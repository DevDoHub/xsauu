"""设备业务逻辑层.

设备元数据存储在数据库中，但在线状态始终从 MediaMTX 中间件实时查询。
"""

import datetime
import json
from collections import defaultdict
from typing import Optional

import httpx
from sqlmodel import Session, select, func

from app.models.device import Device
from app.schemas.device import (
    DeviceCreateDTO, DeviceUpdateDTO, DeviceRespVO,
    DeviceListRespVO, DeviceConfigDTO, DeviceConfigRespVO,
    DeviceCountRespVO, DeviceGroupedByPersonVO, DeviceGroupedByAreaVO,
    DeviceIpMapRespVO, SocketIOStatusRespVO, ControlCommandRespVO,
    CameraDirection, DeviceStatus,
)
from app.exceptions import NotFoundException, BadRequestException
from app.logger import logger


def _to_iso(dt: datetime.datetime | None) -> str | None:
    """将 datetime 转为 ISO 字符串，确保含时区信息（UTC +00:00）。
    
    SQLite 读出的 datetime 是 naive 的，直接 isoformat() 不带时区，
    前端 JS new Date() 会按本地时区解析，导致偏差。
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.isoformat()

# MediaMTX 控制 API 地址
MEDIAMTX_API = "http://127.0.0.1:9997"

# 边缘端 PTZ 方向映射（前端 up↔down 已在旧后端反转，这里保持一致）
_PTZ_DIRECTION_MAP: dict[str, str] = {
    "up": "down", "down": "up", "left": "left", "right": "right",
}


def _fetch_mediamtx_online_map() -> dict[str, bool]:
    """从 MediaMTX API 获取所有路径的在线状态.
    
    返回 {path_name: is_ready} 映射。
    is_ready 表示该路径有活跃的视频流（ready=True）。
    """
    try:
        resp = httpx.get(f"{MEDIAMTX_API}/v3/paths/list", timeout=3.0)
        resp.raise_for_status()
        data = resp.json()
        return {
            item["name"]: item.get("ready", False)
            for item in data.get("items", [])
        }
    except Exception as e:
        logger.warning(f"查询 MediaMTX 在线状态失败: {e}")
        return {}


class DeviceService:
    """设备 Service."""

    def __init__(self, session: Session):
        self.session = session
    
    def _device_to_resp(self, device: Device, is_online: Optional[bool] = None) -> DeviceRespVO:
        """将Device模型转换为DeviceRespVO，处理datetime到str的转换.
        
        如果提供了 is_online 参数，则使用该值覆盖设备的 is_online 字段。
        """
        online = is_online if is_online is not None else device.is_online

        # 计算总运行时长 = 历史累计 + 本次在线时长
        current_session_seconds = 0
        if online and device.online_since:
            now = datetime.datetime.now(datetime.timezone.utc)
            since = device.online_since
            if since.tzinfo is None:
                since = since.replace(tzinfo=datetime.timezone.utc)
            current_session_seconds = max(0, int((now - since).total_seconds()))
        
        total = device.accumulated_runtime + current_session_seconds

        return DeviceRespVO(
            id=device.id,
            device_id=device.device_id,
            deviceNumber=device.device_id,
            name=device.name,
            location=device.location,
            ip_address=device.ip_address,
            camera_url=device.camera_url,
            mediamtx_path=device.mediamtx_path or device.device_id,
            camera_rotation=device.camera_rotation or 0,
            is_online=online,
            online_since=_to_iso(device.online_since),
            total_runtime_seconds=max(0, total),
            last_heartbeat=_to_iso(device.last_heartbeat),
            status=device.status,
            responsible_person=device.responsible_person,
            area_manager=device.area_manager,
            area_manager_phone=device.area_manager_phone,
            workshop=device.workshop,
            safety_permit_no=device.safety_permit_no,
            work_content=device.work_content,
            work_level=device.work_level,
            work_type=device.work_type or '',
            confined_space=device.confined_space or '',
            work_start_time=device.work_start_time or '',
            work_end_time=device.work_end_time or '',
            work_status=device.work_status or '',
            created_at=_to_iso(device.created_at) or "",
            updated_at=_to_iso(device.updated_at) or "",
        )

    def register_device(self, dto: DeviceCreateDTO) -> DeviceRespVO:
        """注册新设备."""
        if self._get_by_device_id(dto.device_id):
            raise BadRequestException(f"设备 '{dto.device_id}' 已注册")

        device = Device(
            device_id=dto.device_id,
            name=dto.name,
            location=dto.location,
            ip_address=dto.ip_address,
            camera_url=dto.camera_url,
            mediamtx_path=dto.mediamtx_path or dto.device_id,  # 为空时默认用 device_id
            camera_rotation=dto.camera_rotation,
            responsible_person=dto.responsible_person,
            area_manager=dto.area_manager,
            area_manager_phone=dto.area_manager_phone,
            workshop=dto.workshop,
        )
        self.session.add(device)
        self.session.commit()
        self.session.refresh(device)
        return self._device_to_resp(device)

    def get_device(self, device_pk: int) -> DeviceRespVO:
        """获取设备详情（按主键）."""
        device = self.session.get(Device, device_pk)
        if not device:
            raise NotFoundException(f"设备 {device_pk} 不存在")
        return self._device_to_resp(device)

    def get_device_by_device_id(self, device_id: str) -> DeviceRespVO:
        """获取设备详情（按 device_id）."""
        device = self._get_by_device_id(device_id)
        if not device:
            raise NotFoundException(f"设备 '{device_id}' 不存在")
        return self._device_to_resp(device)

    def update_device(self, device_pk: int, dto: DeviceUpdateDTO) -> DeviceRespVO:
        """更新设备信息."""
        device = self.session.get(Device, device_pk)
        if not device:
            raise NotFoundException(f"设备 {device_pk} 不存在")

        update_data = dto.model_dump(exclude_none=True)
        for key, value in update_data.items():
            setattr(device, key, value)

        self.session.add(device)
        self.session.commit()
        self.session.refresh(device)
        return self._device_to_resp(device)

    def list_devices(self, *, page: int = 1, page_size: int = 20) -> DeviceListRespVO:
        """分页查询设备."""
        skip = (page - 1) * page_size
        stmt = select(Device).offset(skip).limit(page_size)
        devices = list(self.session.exec(stmt).all())
        total = self.session.exec(select(func.count()).select_from(Device)).one()
        return DeviceListRespVO(
            total=total,
            items=[self._device_to_resp(d) for d in devices],
            page=page,
            page_size=page_size,
        )

    def _refresh_devices_with_realtime_status(
        self, *, auto_discover: bool = False,
    ) -> list[tuple[Device, bool]]:
        """读取所有未禁用设备 + MediaMTX/SocketIO 实时在线状态，
        把状态变化（上线/下线）落库（含 ``accumulated_runtime`` 累加），
        并返回 ``[(device, is_online_now), ...]`` 供分组方法使用。

        Args:
            auto_discover: ``True`` 时先用 ``_auto_discover_from_mediamtx``
                注册 MediaMTX 里发现的新设备，再查列表。

        Returns:
            ``[(device, is_online_now), ...]``。
        """
        # 1. 实时在线源
        mtx_online = _fetch_mediamtx_online_map()
        sio_online: set[str] = set()
        try:
            from app.socketio_compat import get_online_devices

            sio_online = set(get_online_devices())
        except Exception as e:
            logger.warning(f"获取 SocketIO 在线设备失败: {e}")

        # 2. 可选：发现 MediaMTX 里出现的新设备并入库
        if auto_discover:
            self._auto_discover_from_mediamtx(mtx_online)

        # 3. 查询所有未禁用设备
        stmt = select(Device).where(Device.status != DeviceStatus.DISABLED)
        devices = list(self.session.exec(stmt).all())

        # 4. 计算实时在线状态 + 落库状态变化
        now = datetime.datetime.now(datetime.timezone.utc)
        results: list[tuple[Device, bool]] = []
        dirty = False
        for device in devices:
            was_online = device.is_online
            online_now = (
                mtx_online.get(device.device_id, False)
                or device.device_id in sio_online
            )

            if online_now and not was_online:
                # 刚上线：记录起始时间
                device.online_since = now
                device.is_online = True
                self.session.add(device)
                dirty = True
            elif not online_now and was_online:
                # 刚下线：累加本次会话时长到 accumulated_runtime
                if device.online_since:
                    since = device.online_since
                    if since.tzinfo is None:
                        since = since.replace(tzinfo=datetime.timezone.utc)
                    session_seconds = max(0, int((now - since).total_seconds()))
                    device.accumulated_runtime += session_seconds
                device.online_since = None
                device.is_online = False
                self.session.add(device)
                dirty = True
            elif online_now and was_online and not device.online_since:
                # 在线但 online_since 缺失（比如服务重启后）：补一个起点
                device.online_since = now
                self.session.add(device)
                dirty = True

            results.append((device, online_now))

        if dirty:
            self.session.commit()
        return results

    def list_devices_grouped_by_person(self) -> DeviceGroupedByPersonVO:
        """按负责人分组查询设备列表（在线状态从 MediaMTX + SocketIO 实时获取）."""
        items = self._refresh_devices_with_realtime_status()
        grouped: dict[str, list[DeviceRespVO]] = defaultdict(list)
        for device, online in items:
            person = device.responsible_person or "未分配"
            grouped[person].append(self._device_to_resp(device, is_online=online))
        return DeviceGroupedByPersonVO(data=dict(grouped))

    def list_devices_grouped_by_area(self) -> DeviceGroupedByAreaVO:
        """按区域负责人分组查询设备列表（兼容旧前端二级结构）.

        返回格式与旧后端 /search_device_by_device_manager 一致：
        ``{ "区域负责人": { "设备名": DeviceRespVO } }``
        """
        items = self._refresh_devices_with_realtime_status(auto_discover=True)
        grouped: dict[str, dict[str, DeviceRespVO]] = defaultdict(dict)
        for device, online in items:
            area = device.area_manager or "未分配区域"
            device_name = device.name or device.device_id
            grouped[area][device_name] = self._device_to_resp(device, is_online=online)
        return DeviceGroupedByAreaVO(
            data={area: dict(devices_map) for area, devices_map in grouped.items()},
        )

    def get_device_counts(self) -> DeviceCountRespVO:
        """轻量级设备计数（仅查总数 + MediaMTX 在线数）.

        不创建 ORM 对象、不分组、不更新数据库状态。
        在线状态直接从 MediaMTX 实时获取，避免依赖 DB 中可能过时的 is_online 字段。
        同时考虑 SocketIO 兼容层的在线设备。
        """
        mtx_online = _fetch_mediamtx_online_map()

        # SocketIO 在线设备
        sio_online = set()
        try:
            from app.socketio_compat import get_online_devices
            sio_online = set(get_online_devices())
        except Exception as e:
            logger.warning(f"获取 SocketIO 在线设备失败: {e}")

        stmt = select(Device.device_id, Device.status).where(Device.status != "disabled")
        rows = self.session.exec(stmt).all()

        total = 0
        online = 0
        for device_id, _status in rows:
            total += 1
            if mtx_online.get(device_id, False) or device_id in sio_online:
                online += 1

        return DeviceCountRespVO(total=total, online=online)

    def list_all_persons(self) -> list[str]:
        """获取所有负责人列表."""
        stmt = select(Device.responsible_person).distinct()
        persons = list(self.session.exec(stmt).all())
        return sorted([p for p in persons if p])

    def update_heartbeat(self, device_id: str) -> Device | None:
        """更新设备心跳."""
        device = self._get_by_device_id(device_id)
        if device:
            device.is_online = True
            device.last_heartbeat = datetime.datetime.now(datetime.timezone.utc)
            self.session.add(device)
            self.session.commit()
            self.session.refresh(device)
        return device

    def mark_offline(self, device_id: str) -> Device | None:
        """标记设备离线."""
        device = self._get_by_device_id(device_id)
        if device:
            device.is_online = False
            self.session.add(device)
            self.session.commit()
            self.session.refresh(device)
        return device

    def mark_timeout_devices_offline(self, timeout_seconds: int) -> list[str]:
        """扫描所有 ``is_online=True`` 但 ``last_heartbeat`` 超时的设备，
        排除 SocketIO 在线设备后批量标记为离线。

        离线时会把"本次在线时长"累加到 ``accumulated_runtime``，并清空
        ``online_since``，保证总运行时长统计正确。

        Args:
            timeout_seconds: 心跳超时阈值（秒）。

        Returns:
            被标记离线的设备 ID 列表（用于日志/广播）。
        """
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now_utc - datetime.timedelta(seconds=timeout_seconds)

        # 候选：DB 里"在线但心跳超时"的设备
        stmt = select(Device).where(
            Device.is_online == True,  # noqa: E712 (SQLModel 不支持 `is True`)
            Device.last_heartbeat < cutoff,
        )
        candidates = list(self.session.exec(stmt).all())
        if not candidates:
            return []

        # 排除：SocketIO 兼容层中仍在线的设备
        sio_online: set[str] = set()
        try:
            from app.socketio_compat import get_online_devices

            sio_online = set(get_online_devices())
        except Exception as e:
            logger.warning(f"查询 SocketIO 在线设备失败: {e}")

        offline_ids: list[str] = []
        for device in candidates:
            if device.device_id in sio_online:
                continue  # SocketIO 还在线，不算离线

            # 累加本次会话时长
            if device.online_since:
                since = device.online_since
                if since.tzinfo is None:
                    since = since.replace(tzinfo=datetime.timezone.utc)
                session_seconds = max(0, int((now_utc - since).total_seconds()))
                device.accumulated_runtime += session_seconds
                device.online_since = None

            device.is_online = False
            self.session.add(device)
            offline_ids.append(device.device_id)
            logger.info(
                f"⏰ 设备离线: {device.device_id} ({device.name}) "
                f"超时 {timeout_seconds}s 无心跳"
            )

        if offline_ids:
            self.session.commit()
        return offline_ids

    def get_device_config(self, device_id: str) -> DeviceConfigRespVO:
        """获取设备配置.
        
        Args:
            device_id: 设备唯一标识。
            
        Raises:
            NotFoundException: 设备不存在时抛出。
        """
        device = self._get_by_device_id(device_id)
        if not device:
            raise NotFoundException(f"设备 '{device_id}' 不存在")
        config = {}
        if device.config_json:
            try:
                config = json.loads(device.config_json)
            except json.JSONDecodeError:
                logger.warning(f"设备 {device_id} 配置 JSON 解析失败，返回空配置")
                config = {}
        return DeviceConfigRespVO(device_id=device_id, config=config)

    def update_device_config(self, device_id: str, config_dto: DeviceConfigDTO) -> DeviceConfigRespVO:
        """更新设备配置（增量合并）.
        
        Args:
            device_id: 设备唯一标识。
            config_dto: 增量配置。
            
        Raises:
            NotFoundException: 设备不存在时抛出。
        """
        device = self._get_by_device_id(device_id)
        if not device:
            raise NotFoundException(f"设备 '{device_id}' 不存在")
        
        # 获取当前配置
        current_config = {}
        if device.config_json:
            try:
                current_config = json.loads(device.config_json)
            except json.JSONDecodeError:
                current_config = {}
        
        # 增量合并
        update_data = config_dto.model_dump(exclude_none=True)
        for key, value in update_data.items():
            if key in ('confidence_values', 'gas_values', 'special_detection_rules', 'passage_values') and isinstance(value, dict):
                # dict 深合并
                if key not in current_config:
                    current_config[key] = {}
                current_config[key].update(value)
            else:
                # list 整体替换 / 标量直接覆盖
                current_config[key] = value
        
        # 写回数据库
        device.config_json = json.dumps(current_config, ensure_ascii=False)
        self.session.add(device)
        self.session.commit()
        
        return DeviceConfigRespVO(device_id=device_id, config=current_config)

    def get_device_ip_map(self) -> DeviceIpMapRespVO:
        """获取所有设备 IP 映射.

        返回 {device_id: {"ip": ..., "name": ...}} 映射。
        """
        stmt = select(Device)
        devices = list(self.session.exec(stmt).all())
        return DeviceIpMapRespVO(devices={
            d.device_id: {"ip": d.ip_address, "name": d.name}
            for d in devices
        })

    def get_device_path_map(self) -> dict[str, str]:
        """获取设备名→MediaMTX视频路径映射.

        返回 {device_id: mediamtx_path} 映射。
        由于统一用 SN 命名，device_id == mediamtx_path，映射为恒等函数。
        此方法保留用于兼容旧逻辑和未来扩展。
        """
        stmt = select(Device.device_id, Device.mediamtx_path)
        rows = self.session.exec(stmt).all()
        return {row[0]: row[1] or row[0] for row in rows}

    def control_camera(self, device_id: str, direction: CameraDirection) -> ControlCommandRespVO:
        """通过 MQTT 发送摄像头控制命令，同时兼容 SocketIO 设备.

        Args:
            device_id: 设备 ID。
            direction: 方向控制命令。

        Returns:
            命令发送结果。
        """
        from app.mqtt.subscriber import mqtt_subscriber

        message = {"direction": direction.value}

        # MQTT 发送（所有方向都通过 MQTT 通知）
        topic = f"xsau/control/{device_id}/camera"
        mqtt_subscriber.publish(topic, message)

        # SocketIO 兼容：如果设备通过 SocketIO 在线，也推送命令
        from app.socketio_compat import is_device_online, push_command
        import asyncio
        if is_device_online(device_id):
            # PTZ 方向需要反转映射，其他命令直接转发
            if direction in (CameraDirection.UP, CameraDirection.DOWN,
                             CameraDirection.LEFT, CameraDirection.RIGHT,
                             CameraDirection.STOP):
                mapped = _PTZ_DIRECTION_MAP.get(direction.value, direction.value)
                sio_command = "direction"
                sio_payload = mapped
            elif direction == CameraDirection.ZOOM_IN:
                sio_command = "zoom_in"
                sio_payload = None
            elif direction == CameraDirection.ZOOM_OUT:
                sio_command = "zoom_out"
                sio_payload = None
            elif direction == CameraDirection.AUTO:
                sio_command = "auto_detect"
                sio_payload = None
            elif direction == CameraDirection.RECONNECT:
                sio_command = "reconnect"
                sio_payload = None
            elif direction == CameraDirection.DISCONNECT:
                sio_command = "disconnect"
                sio_payload = None
            else:
                sio_command = "direction"
                sio_payload = direction.value

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(push_command(device_id, sio_command, sio_payload))
            except RuntimeError:
                asyncio.run(push_command(device_id, sio_command, sio_payload))

        return ControlCommandRespVO(status="ok", device_id=device_id, command=message)

    def control_detection(self, device_id: str, action: str) -> ControlCommandRespVO:
        """通过 MQTT 发送检测控制命令，同时兼容 SocketIO 设备.

        Args:
            device_id: 设备 ID。
            action: 动作，start/stop。

        Returns:
            命令发送结果。
        """
        from app.mqtt.subscriber import mqtt_subscriber

        topic = f"xsau/control/{device_id}/detection"
        message = {"action": action}
        mqtt_subscriber.publish(topic, message)

        # SocketIO 兼容
        from app.socketio_compat import is_device_online, push_command
        import asyncio
        if is_device_online(device_id):
            cmd_type = "start_detection" if action == "start" else "stop_detection"
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(push_command(device_id, cmd_type))
            except RuntimeError:
                asyncio.run(push_command(device_id, cmd_type))

        return ControlCommandRespVO(status="ok", device_id=device_id, command=message)

    def push_config_update(self, device_id: str, config: dict) -> None:
        """通过 SocketIO 推送配置更新到边缘端.

        Args:
            device_id: 设备 ID。
            config: 设备配置。
        """
        from app.socketio_compat import is_device_online, push_config_update
        import asyncio
        if is_device_online(device_id) and config:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(push_config_update(device_id, config))
            except RuntimeError:
                asyncio.run(push_config_update(device_id, config))

    def get_socketio_status(self) -> SocketIOStatusRespVO:
        """获取 SocketIO 兼容层状态（调试用）.

        Returns:
            SocketIO 状态信息。
        """
        from app.socketio_compat import get_online_devices, get_threshold_cache
        from app.settings import settings
        online = get_online_devices()
        return SocketIOStatusRespVO(
            enabled=settings.SOCKETIO_ENABLED,
            online_devices=online,
            online_count=len(online),
            threshold_cache=get_threshold_cache(),
        )

    def _get_by_device_id(self, device_id: str) -> Device | None:
        stmt = select(Device).where(Device.device_id == device_id)
        return self.session.exec(stmt).first()

    def _auto_discover_from_mediamtx(self, mtx_online: dict[str, bool]) -> int:
        """自动发现 MediaMTX 中的新路径并注册为设备.

        只注册 device 表中不存在的路径，返回新注册数量。
        忽略以下路径：
        - 以 _ 开头的内部路径
        - 包含 / 的路径
        """
        if not mtx_online:
            return 0

        # 查询已注册的 device_id
        existing = set()
        for row in self.session.exec(select(Device.device_id)).all():
            existing.add(row if isinstance(row, str) else row[0])

        logger.info(f"自动发现: MediaMTX路径={list(mtx_online.keys())}, 已注册={existing}")

        new_count = 0
        for path_name in mtx_online:
            # 跳过内部路径和无效路径
            if not path_name or path_name.startswith("_") or "/" in path_name:
                continue
            if path_name in existing:
                continue

            # 自动注册新设备
            try:
                device = Device(
                    device_id=path_name,
                    name=f"自动发现-{path_name}",
                    location="待分配",
                    ip_address="",
                    camera_url=f"rtsp://127.0.0.1:8554/{path_name}",
                    mediamtx_path=path_name,
                    is_online=False,
                    status=DeviceStatus.ACTIVE,
                    responsible_person="待分配",
                    area_manager="待分配区域",
                    area_manager_phone="",
                    workshop="",
                    safety_permit_no="",
                    work_content="",
                    work_level="",
                    config_json="{}",
                )
                self.session.add(device)
                self.session.commit()
                new_count += 1
                logger.info(f"自动发现并注册新设备: {path_name}")
            except Exception as e:
                self.session.rollback()
                logger.warning(f"自动注册设备 {path_name} 失败(可能已存在): {e}")

        return new_count

    def get_devices_by_person(self, person: str) -> list[Device]:
        """获取指定负责人下的所有设备."""
        stmt = select(Device).where(
            Device.responsible_person == person,
            Device.status != "disabled"
        )
        return list(self.session.exec(stmt).all())
