"""边缘端事件入库服务（协议无关）.

将 SocketIO 兼容层（``socketio_compat.py``）和 MQTT 处理器
（``mqtt/handler.py``）中重复的"告警入库 / 气体数据入库 / 心跳更新"
逻辑统一抽到这里。两边只负责：

1. 解析自己协议的 payload 格式（字段名差异）
2. 调用本服务的 ``ingest_*`` 方法

设计原则：
- **方法签名都是 async**：在异步上下文（SocketIO handler）直接 await，
  在同步上下文（MQTT 回调线程）通过 ``asyncio.run_coroutine_threadsafe``
  调度（参见 ``mqtt/handler.py::_run_async``）。
- **不做协议层的事**：base64 图片解码、topic 解析、字段重命名等，
  由调用方处理后再传入。
"""

from __future__ import annotations

import datetime

from sqlmodel import Session

from app.db import engine
from app.logger import logger
from app.models.alarm import Alarm
from app.models.telemetry import Telemetry

# 气体 payload 中的非传感器字段（写 Telemetry 时跳过）
_GAS_SKIP_FIELDS = frozenset({"device_id", "device_name", "note", "update_time", "idx"})


async def ingest_alarm(
    *,
    device_id: str,
    severity: str = "warning",
    confidence: float = 0.0,
    description: str = "",
    note: str = "",
    type: str = "",
    type2: str = "",
    image_url: str | None = None,
    bbox: str | None = None,
    device_manager: str = "",
    area_manager: str = "",
    area_manager_phone: str = "",
    snapshot_device_name: str = "",
    snapshot_ip_address: str = "",
    snapshot_safety_permit_no: str = "",
    snapshot_workshop: str = "",
    snapshot_work_content: str = "",
    snapshot_work_level: str = "",
    snapshot_work_type: str = "",
    snapshot_confined_space: str = "",
    snapshot_work_start_time: str = "",
    snapshot_work_end_time: str = "",
    snapshot_work_status: str = "",
    device_time: str = "",
    log_prefix: str = "",
) -> int | None:
    """统一处理边缘端告警入库 + SSE 广播.

    流程：
    1. 读 SystemConfig 取 ``alarm_confidence_threshold``、``alarm_auto_review``
    2. 置信度过滤（低于阈值丢弃，返回 None）
    3. 解析 ``device_time``（北京时间字符串）为 datetime
    4. 写 Alarm 表（带完整设备/作业快照，写入即冻结）
    5. 通过 ``detection_service.push_alarm`` 广播到前端 SSE

    Args:
        device_id: 设备 ID。
        severity: 严重级别，默认 ``warning``。
        confidence: 置信度，0~1，低于配置阈值会被过滤。
        description: 告警描述（MQTT 协议有此字段，SocketIO 通常为空）。
        note: 备注（如作业区域）。
        type: 事件类型（中文，如 "没有安全帽"）。
        type2: 事件类别（中文，如 "安全文明着装"）。
        image_url: 告警截图相对路径（调用方处理图片落盘后传入）。
        bbox: 检测框坐标 JSON 字符串。
        device_manager: 设备负责人（写入快照）。
        area_manager: 区域负责人（写入快照）。
        area_manager_phone: 区域负责人电话（写入快照）。
        snapshot_*: 完整设备/作业快照字段，写入时一次性冻结。
        device_time: 边缘端北京时间字符串 ``YYYY-MM-DD HH:MM:SS``，
            为空时 Alarm 模型用默认值（写入时刻）。
        log_prefix: 日志前缀（如 ``"[SocketIO]"`` / ``""``），便于
            排障时区分来源。

    Returns:
        新建告警的主键 ``id``；置信度被过滤时返回 ``None``。
    """
    # 注意：不再用告警事件反向更新 Device 表的负责人字段。
    # Device 元信息的唯一更新通道是 register_device 事件；告警里
    # 的 device_manager / area_manager 仅用于做"快照"，冻结当时的负责人，
    # 确保历史告警不会因后续配置变更被污染。
    prefix = f"{log_prefix} " if log_prefix else ""

    with Session(engine) as session:
        # 1. 读取系统配置
        from app.services.system_config import SystemConfigService

        config_svc = SystemConfigService(session)
        threshold = config_svc.get_typed_value("alarm_confidence_threshold", default=0.0)
        auto_review = config_svc.get_typed_value("alarm_auto_review", default=False)

        # 2. 置信度过滤
        if confidence < threshold:
            logger.info(
                f"{prefix}告警被过滤: confidence={confidence} < threshold={threshold}"
            )
            return None

        # 3. 解析边缘端时间
        alarm_time: datetime.datetime | None = None
        if device_time:
            try:
                alarm_time = datetime.datetime.strptime(device_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.warning(f"{prefix}边缘端时间格式异常: {device_time}")

        # 4. 入库（带完整快照）
        alarm = Alarm(
            device_id=device_id,
            severity=severity,
            confidence=confidence,
            description=description,
            note=note,
            type=type,
            type2=type2,
            image_url=image_url,
            bbox=bbox,
            snapshot_device_name=snapshot_device_name,
            snapshot_device_manager=device_manager,
            snapshot_area_manager=area_manager,
            snapshot_area_manager_phone=area_manager_phone,
            snapshot_ip_address=snapshot_ip_address,
            snapshot_workshop=snapshot_workshop,
            snapshot_safety_permit_no=snapshot_safety_permit_no,
            snapshot_work_content=snapshot_work_content,
            snapshot_work_level=snapshot_work_level,
            snapshot_work_type=snapshot_work_type,
            snapshot_confined_space=snapshot_confined_space,
            snapshot_work_start_time=snapshot_work_start_time,
            snapshot_work_end_time=snapshot_work_end_time,
            snapshot_work_status=snapshot_work_status,
            alarm_time=alarm_time,
        )
        if auto_review:
            alarm.is_reviewed = True
            alarm.review_status = 2  # 确定报警

        session.add(alarm)
        session.commit()
        session.refresh(alarm)

        alarm_id = alarm.id
        alarm_time_iso = (
            device_time
            if device_time
            else (alarm.alarm_time.strftime("%Y-%m-%d %H:%M:%S") if alarm.alarm_time else None)
        )

        logger.info(
            f"{prefix}告警已入库: id={alarm_id}, type={type}, alarm_time={alarm.alarm_time}"
        )

        # 5. SSE 广播（在 session 关闭前取必要字段，避免 detached 实例）
        broadcast_payload = {
            "device_id": device_id,
            "alarm_id": alarm_id,
            "severity": alarm.severity,
            "confidence": alarm.confidence,
            "note": alarm.note,
            "type": alarm.type,
            "type2": alarm.type2,
            "image_url": alarm.image_url,
            "bbox": alarm.bbox,
            "device_manager": device_manager,
            "area_manager": area_manager,
            "area_manager_phone": area_manager_phone,
            "alarm_time": alarm_time_iso,
        }

    # session 关闭后再走异步广播，避免 SSE 客户端慢导致 DB 连接被占
    from app.services.detection import detection_service

    await detection_service.push_alarm(broadcast_payload)
    return alarm_id


async def ingest_gas_telemetry(
    *,
    device_id: str,
    payload: dict,
    update_heartbeat: bool = False,
    log_prefix: str = "",
) -> dict[str, float]:
    """统一处理边缘端气体/遥测数据入库 + SSE 广播.

    遍历 ``payload`` 中所有可转 float 的传感器字段，每个字段写一条
    ``Telemetry`` 记录。``device_id``、``device_name``、``note``、
    ``update_time``、``idx`` 等元数据字段会被跳过。

    SSE 广播时**透传调用方提供的 payload**（含 device_name/note/update_time
    等），并补上数值字段。

    Args:
        device_id: 设备 ID。
        payload: 边缘端原始数据，含若干传感器字段（值可为 str/float）。
        update_heartbeat: 是否同时更新设备心跳（SocketIO ``gas_data``
            事件需要，MQTT 不需要——MQTT 走独立的 heartbeat topic）。
        log_prefix: 日志前缀，便于排障。

    Returns:
        实际入库的传感器数值字典 ``{field: float}``，调用方可基于此
        判断"有无新数据"或扩充 SSE payload。
    """
    prefix = f"{log_prefix} " if log_prefix else ""
    sensor_values: dict[str, float] = {}

    with Session(engine) as session:
        # 1. 写 Telemetry
        for field, raw in payload.items():
            if field in _GAS_SKIP_FIELDS or raw is None or raw == "":
                continue
            try:
                value = float(raw)
            except (ValueError, TypeError):
                continue
            session.add(Telemetry(
                device_id=device_id,
                sensor_type=field,
                value=value,
                unit="",
                is_overlimit=False,
                threshold=None,
            ))
            sensor_values[field] = value

        # 2. 可选：更新设备心跳（SocketIO 走这条路，MQTT 不走）
        if update_heartbeat:
            from sqlmodel import select

            from app.models.device import Device

            stmt = select(Device).where(Device.device_id == device_id)
            device = session.exec(stmt).first()
            if device:
                device.is_online = True
                device.last_heartbeat = datetime.datetime.now(datetime.timezone.utc)
                session.add(device)

        session.commit()

    if not sensor_values:
        logger.debug(f"{prefix}气体数据无可入库字段: device={device_id}")
        return sensor_values

    # 3. SSE 广播：把传感器数值合并到调用方 payload 后广播
    from app.services.detection import detection_service

    sse_payload = {**payload, **sensor_values, "device_id": device_id}
    await detection_service.update_gas_data(device_id, sse_payload)
    return sensor_values


async def ingest_heartbeat(device_id: str, *, log_prefix: str = "") -> bool:
    """统一处理设备心跳：更新 ``last_heartbeat`` + ``is_online`` + 广播 SSE.

    Args:
        device_id: 设备 ID。
        log_prefix: 日志前缀。

    Returns:
        ``True`` 表示设备存在并已更新；``False`` 表示设备不在 DB 中
        （调用方可决定是否自动注册）。
    """
    from sqlmodel import select

    from app.models.device import Device

    prefix = f"{log_prefix} " if log_prefix else ""
    with Session(engine) as session:
        device = session.exec(
            select(Device).where(Device.device_id == device_id)
        ).first()
        if not device:
            logger.warning(f"{prefix}心跳来自未注册设备: {device_id}")
            return False

        now = datetime.datetime.now(datetime.timezone.utc)
        device.is_online = True
        device.last_heartbeat = now
        if not device.online_since:
            device.online_since = now
        session.add(device)
        session.commit()

        device_name = device.name
        last_heartbeat_iso = now.isoformat()

    # session 关闭后再走异步广播
    from app.services.detection import detection_service

    await detection_service.update_device_status(device_id, {
        "is_online": True,
        "device_name": device_name,
        "last_heartbeat": last_heartbeat_iso,
    })
    return True
