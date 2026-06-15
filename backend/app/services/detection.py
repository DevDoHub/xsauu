"""检测框数据业务逻辑层.

管理检测框的实时状态、SSE 推送、MQTT 控制命令、
气体数据、设备状态、告警推送等。
"""

import asyncio
import datetime
from collections.abc import AsyncGenerator

from app.logger import logger
from app.schemas.detection import (
    GAS_REGISTRY,
    BatchDetectionControlRespVO,
    DetectionAction,
    DetectionPushDTO,
    DetectionPushRespVO,
    GasMonitorDataRespVO,
    GasThresholdRespVO,
    GlobalDetectionControlRespVO,
    PersonDetectionControlRespVO,
)
from app.utils.sse import SsePublisher


class DetectionService:
    """检测框 Service.

    管理检测框共享状态（异步安全）。
    同时管理设备状态、气体数据、告警的 SSE 广播。
    """

    MAX_ALARM_HISTORY = 100
    # 气体数据过期时间（秒），超过此时间无数据更新视为离线
    GAS_DATA_EXPIRE_SECONDS = 30

    def __init__(self) -> None:
        # 设备名 → mediamtx 视频路径映射
        self._device_path_map: dict[str, str] = {}

        # 4 个独立 SSE 频道：检测框 / 设备状态 / 气体数据 / 告警
        self._detection_pub = SsePublisher(name="detection")
        self._status_pub = SsePublisher(name="device-status")
        self._gas_pub = SsePublisher(name="gas")
        self._alarm_pub = SsePublisher(name="alarm")

        # 各频道的"最新快照"存储（新订阅者首次连接时回放）
        self._latest_detections: dict[str, dict] = {}
        self._latest_device_status: dict[str, dict] = {}
        self._latest_gas_data: dict[str, dict] = {}
        self._latest_alarms: list[dict] = []

        # 气体数据相关锁（仅保护 _latest_gas_data 的清理逻辑）
        self._gas_lock = asyncio.Lock()

        # 气体阈值缓存 {device_id: threshold_dict}
        self._threshold_cache: dict[str, dict] = {}

    # ── 属性 ──────────────────────────────────────────────────────────────────

    @property
    def device_path_map(self) -> dict[str, str]:
        """获取设备名→视频路径映射."""
        return self._device_path_map

    @device_path_map.setter
    def device_path_map(self, mapping: dict[str, str]) -> None:
        """设置设备名→视频路径映射."""
        self._device_path_map = mapping

    # ── 阈值缓存管理 ─────────────────────────────────────────────────────────

    def update_threshold_cache(self, device_id: str, data: dict) -> None:
        """更新气体阈值缓存（由 SocketIO gas_threshold 事件调用）.

        Args:
            device_id: 设备 ID。
            data: 阈值数据。
        """
        self._threshold_cache[device_id] = data
        logger.info(f"气体阈值缓存更新: device={device_id}")

    def get_threshold_cache(self) -> dict[str, dict]:
        """获取阈值缓存快照.

        Returns:
            {device_id: threshold_dict} 映射。
        """
        return dict(self._threshold_cache)

    # ── 检测框广播 ────────────────────────────────────────────────────────────

    async def broadcast(self, payload: dict) -> None:
        """向所有 SSE 客户端广播一条检测事件.

        Args:
            payload: 检测事件数据。
        """
        await self._detection_pub.publish(payload)

    async def receive_push(self, dto: DetectionPushDTO) -> DetectionPushRespVO:
        """接收边缘端推送的检测框数据.

        Args:
            dto: 检测框推送数据。

        Returns:
            处理结果。
        """
        device = dto.device_name
        mapped_name = self._device_path_map.get(device, device)

        payload = dto.model_dump()
        payload["device_name"] = mapped_name
        payload["real_device_id"] = device

        self._latest_detections[mapped_name] = payload

        await self._detection_pub.publish(payload)
        logger.debug(f"收到检测框推送: {device} -> {mapped_name}")
        return DetectionPushRespVO(status="ok", device=mapped_name)

    async def get_sse_stream(self, request_is_disconnected) -> AsyncGenerator[str, None]:
        """获取 SSE 流生成器.

        Args:
            request_is_disconnected: 请求断开检查回调。

        Yields:
            SSE 格式的数据。
        """
        async for chunk in self._detection_pub.stream(
            request_is_disconnected,
            snapshot=lambda: list(self._latest_detections.values()),
        ):
            yield chunk

    async def get_latest_detections(self) -> list[dict]:
        """获取所有设备最新检测框快照.

        Returns:
            检测框数据列表。
        """
        return list(self._latest_detections.values())

    async def get_device_detection(self, device_name: str) -> dict | None:
        """获取指定设备最新检测框.

        Args:
            device_name: 设备名称。

        Returns:
            检测框数据，不存在返回 None。
        """
        return self._latest_detections.get(device_name)

    # ── 检测控制 ──────────────────────────────────────────────────────────────

    def control_global_detection(self, action: DetectionAction) -> GlobalDetectionControlRespVO:
        """发送全局检测控制命令.

        Args:
            action: 动作，start/stop。

        Returns:
            命令发送结果。
        """
        from app.mqtt.subscriber import mqtt_subscriber

        topic = "xsau/control/all/detection"
        message = {"action": action, "scope": "global"}
        mqtt_subscriber.publish(topic, message)
        logger.info(f"全局检测控制: {action}")
        return GlobalDetectionControlRespVO(
            status="ok", action=action, scope="global", command=message,
        )

    def control_batch_detection(self, device_ids: list[str], action: DetectionAction) -> BatchDetectionControlRespVO:
        """发送批量检测控制命令.

        Args:
            device_ids: 设备 ID 列表。
            action: 动作，start/stop。

        Returns:
            命令发送结果。
        """
        from app.mqtt.subscriber import mqtt_subscriber

        results = []
        for device_id in device_ids:
            topic = f"xsau/control/{device_id}/detection"
            message = {"action": action}
            mqtt_subscriber.publish(topic, message)
            results.append({"device_id": device_id, "status": "sent"})

        logger.info(f"批量检测控制: {action}, 设备数: {len(device_ids)}")
        return BatchDetectionControlRespVO(
            status="ok", action=action, results=results,
        )

    def control_detection_by_person(self, person: str, action: DetectionAction, session) -> PersonDetectionControlRespVO:
        """按负责人控制检测.

        Args:
            person: 负责人名称。
            action: 动作，start/stop。
            session: 数据库会话。

        Returns:
            命令发送结果。
        """
        # 延迟导入：避免 DeviceService ↔ DetectionService 循环依赖
        from app.services.device import DeviceService
        from app.mqtt.subscriber import mqtt_subscriber

        svc = DeviceService(session)
        devices = svc.get_devices_by_person(person)

        if not devices:
            return PersonDetectionControlRespVO(
                status="ok", action=action, person=person, results=[],
            )

        results = []
        for device in devices:
            topic = f"xsau/control/{device.device_id}/detection"
            message = {"action": action}
            mqtt_subscriber.publish(topic, message)
            results.append({"device_id": device.device_id, "device_name": device.name, "status": "sent"})

        logger.info(f"按负责人检测控制: {action}, 负责人: {person}, 设备数: {len(results)}")
        return PersonDetectionControlRespVO(
            status="ok", action=action, person=person, results=results,
        )

    # ── 设备状态 ──────────────────────────────────────────────────────────────

    async def broadcast_device_status(self, payload: dict) -> None:
        """向所有 SSE 客户端广播设备状态更新.

        Args:
            payload: 设备状态数据。
        """
        await self._status_pub.publish(payload)

    async def update_device_status(self, device_id: str, status: dict) -> None:
        """更新设备状态并广播.

        Args:
            device_id: 设备 ID。
            status: 设备状态信息。
        """
        self._latest_device_status[device_id] = {
            "device_id": device_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            **status,
        }
        await self._status_pub.publish({
            "type": "device_status",
            "device_id": device_id,
            **status,
        })

    async def get_device_status_sse_stream(self, request_is_disconnected) -> AsyncGenerator[str, None]:
        """获取设备状态 SSE 流生成器.

        Args:
            request_is_disconnected: 请求断开检查回调。

        Yields:
            SSE 格式的数据。
        """
        async for chunk in self._status_pub.stream(
            request_is_disconnected,
            snapshot=lambda: list(self._latest_device_status.values()),
        ):
            yield chunk

    async def get_latest_device_status(self) -> dict[str, dict]:
        """获取所有设备最新状态.

        Returns:
            {device_id: status} 映射。
        """
        return dict(self._latest_device_status)

    # ── 气体数据 ──────────────────────────────────────────────────────────────

    async def broadcast_gas_data(self, payload: dict) -> None:
        """向所有 SSE 客户端广播气体数据更新.

        Args:
            payload: 气体数据。
        """
        await self._gas_pub.publish(payload)

    async def update_gas_data(self, device_id: str, gas_data: dict) -> None:
        """更新气体数据并广播.

        Args:
            device_id: 设备 ID。
            gas_data: 气体监测数据。
        """
        self._latest_gas_data[device_id] = gas_data
        await self._gas_pub.publish({"type": "gas_data", **gas_data})

    async def get_gas_sse_stream(self, request_is_disconnected) -> AsyncGenerator[str, None]:
        """获取气体数据 SSE 流生成器.

        Args:
            request_is_disconnected: 请求断开检查回调。

        Yields:
            SSE 格式的数据。
        """
        # 客户端连接时先清一次过期数据，再给快照
        async with self._gas_lock:
            self._cleanup_expired_gas_data()
            snapshot_list = list(self._latest_gas_data.values())

        async for chunk in self._gas_pub.stream(
            request_is_disconnected,
            snapshot=lambda: snapshot_list,
        ):
            yield chunk

    def _cleanup_expired_gas_data(self) -> None:
        """清理过期的气体数据（同步，由调用方保证串行）."""
        now = datetime.datetime.now()
        expired_devices: list[str] = []

        for device_id, gas_data in self._latest_gas_data.items():
            update_time_str = gas_data.get("update_time")
            if not update_time_str:
                continue

            try:
                # 解析 update_time（格式：YYYY-MM-DD HH:MM:SS）
                update_time = datetime.datetime.strptime(update_time_str, "%Y-%m-%d %H:%M:%S")
                diff_seconds = (now - update_time).total_seconds()

                if diff_seconds > self.GAS_DATA_EXPIRE_SECONDS:
                    expired_devices.append(device_id)
            except (ValueError, TypeError):
                # 解析失败，视为过期
                expired_devices.append(device_id)

        for device_id in expired_devices:
            del self._latest_gas_data[device_id]

        if expired_devices:
            logger.info(f"清理过期气体数据，移除离线设备: {expired_devices}")

    async def get_latest_gas_data(self) -> dict[str, dict]:
        """获取所有设备最新气体数据（自动清理过期数据）.

        Returns:
            {device_id: gas_data} 映射（仅含在线设备）。
        """
        async with self._gas_lock:
            self._cleanup_expired_gas_data()
            return dict(self._latest_gas_data)

    async def get_gas_monitor_data(self) -> GasMonitorDataRespVO:
        """获取气体监控聚合数据（驾驶舱专用）.

        返回格式与旧后端完全一致: {realtime, threshold, registry}。

        Returns:
            气体监控聚合数据。
        """
        realtime = await self.get_latest_gas_data()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        threshold: dict[str, dict] = {}
        for device_id in realtime:
            cached = self._threshold_cache.get(device_id, {})
            threshold[device_id] = {
                "C3H8": cached.get("C3H8", 400),
                "C2H2": cached.get("C2H2", 250),
                "CO2": cached.get("CO2", 1000),
                "HCN": cached.get("HCN", 5),
                "O2_max": cached.get("O2_max", 23.5),
                "O2_min": cached.get("O2_min", 19.5),
                "device_id": device_id,
                "device_name": realtime[device_id].get("device_name", device_id),
                "update_time": now_str,
            }

        return GasMonitorDataRespVO(
            realtime=realtime,
            threshold=threshold,
            registry=GAS_REGISTRY,
        )

    async def get_gas_threshold(self) -> GasThresholdRespVO:
        """获取气体阈值配置.

        Returns:
            阈值数据，格式: {data: {device_id: {...}}}。
        """
        monitor_data = await self.get_gas_monitor_data()
        return GasThresholdRespVO(data=monitor_data.threshold)

    # ── 告警 ──────────────────────────────────────────────────────────────────

    async def broadcast_alarm(self, payload: dict) -> None:
        """向所有 SSE 客户端广播告警事件.

        Args:
            payload: 告警数据。
        """
        await self._alarm_pub.publish(payload)

    async def push_alarm(self, alarm_data: dict) -> None:
        """推送告警并广播.

        Args:
            alarm_data: 告警数据。
        """
        self._latest_alarms.append(alarm_data)
        if len(self._latest_alarms) > self.MAX_ALARM_HISTORY:
            self._latest_alarms.pop(0)

        await self._alarm_pub.publish({"type": "alarm", **alarm_data})

    async def get_alarm_sse_stream(self, request_is_disconnected) -> AsyncGenerator[str, None]:
        """获取告警 SSE 流生成器.

        Args:
            request_is_disconnected: 请求断开检查回调。

        Yields:
            SSE 格式的数据。
        """
        async for chunk in self._alarm_pub.stream(
            request_is_disconnected,
            snapshot=lambda: list(self._latest_alarms),
        ):
            yield chunk

    async def get_latest_alarms(self) -> list[dict]:
        """获取最近告警列表.

        Returns:
            告警列表（最多100条）。
        """
        return list(self._latest_alarms)


# 全局单例
detection_service = DetectionService()
