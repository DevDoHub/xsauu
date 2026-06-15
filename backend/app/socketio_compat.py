"""SocketIO 兼容层.

让旧 Jetson 边缘端（tripod_pro）能直接连接新后端，无需修改边缘端代码。

边缘端事件 → 新后端逻辑：
  register_device  → 自动注册设备 + 更新在线状态
  alarm_data       → 入库 + SSE 广播（同 MQTT alarm 处理）
  gas_data         → 入库 + SSE 广播（同 MQTT telemetry 处理）
  gas_threshold    → 记录阈值变化
  config_push      → 更新设备配置
  detection_data   → SSE 广播检测框坐标（同 HTTP POST /api/detections/push）

新后端 → 边缘端事件：
  register_response → 注册确认
  command           → 控制指令（PTZ/检测/重置等）
  config_update     → 配置更新
  voice_*           → 语音通话转发
"""

import asyncio
import base64
import datetime
from pathlib import Path

import socketio
from loguru import logger

# ── 创建 SocketIO 服务端实例 ──
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# 设备连接映射 {device_id: sid}
_device_sessions: dict[str, str] = {}


def _run_sync_in_thread(coro):
    """在 SocketIO 异步上下文中安全地运行同步数据库操作.

    将同步的数据库操作放到线程池中执行，避免阻塞事件循环。
    """
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, asyncio.run, coro)


def _save_alarm_image(image_b64: str, device_id: str) -> str | None:
    """保存告警截图到磁盘，返回相对路径."""
    try:
        # 去掉 data:image/jpeg;base64, 前缀
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(image_b64)

        img_dir = Path("data/alarm_images")
        img_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sio_{device_id}_{ts}.jpg"
        filepath = img_dir / filename
        filepath.write_bytes(img_bytes)
        return f"alarm_images/{filename}"
    except Exception as e:
        logger.error(f"保存告警图片失败: {e}")
        return None


# ═══════════════════════════════════════════════════════
#  边缘端 → 服务端 事件处理
# ═══════════════════════════════════════════════════════


@sio.event
async def connect(sid: str, environ: dict):
    """客户端连接."""
    remote = environ.get("REMOTE_ADDR", "unknown")
    logger.info(f"[SocketIO] 客户端连接: sid={sid}, ip={remote}")


@sio.event
async def ping_health(sid: str, data: dict):
    """前端健康检查 ping，回 pong_health.

    与旧后端 (server_code/Sys_main/managers/socketio_manager.py) 保持事件名兼容。
    前端 useSocket composable 通过此机制检测连接是否还活着。
    """
    await sio.emit("pong_health", {"schema_version": 1}, to=sid)


@sio.event
async def disconnect(sid: str):
    """客户端断开."""
    # 清理设备映射
    to_remove = [did for did, s in _device_sessions.items() if s == sid]
    for did in to_remove:
        del _device_sessions[did]
        logger.info(f"[SocketIO] 设备断开: device_id={did}, sid={sid}")

        # 更新数据库：标记离线、清空 online_since
        try:
            from sqlmodel import Session, select
            from app.db import engine
            from app.models.device import Device

            with Session(engine) as session:
                stmt = select(Device).where(Device.device_id == did)
                device = session.exec(stmt).first()
                if device:
                    # 离线前，将本次在线时长累加到 accumulated_runtime
                    if device.online_since:
                        now_utc = datetime.datetime.now(datetime.timezone.utc)
                        since = device.online_since
                        if since.tzinfo is None:
                            since = since.replace(tzinfo=datetime.timezone.utc)
                        session_seconds = max(0, int((now_utc - since).total_seconds()))
                        device.accumulated_runtime += session_seconds
                    device.is_online = False
                    device.online_since = None
                    session.add(device)
                    session.commit()

            # 广播离线状态
            from app.services.detection import detection_service
            import asyncio
            asyncio.create_task(detection_service.update_device_status(did, {
                "is_online": False,
                "online_since": None,
            }))

            # 清理 mediamtx 上对应的拉流路径，避免 mediamtx 持续重试一个不可达 RTSP，
            # 日志刷屏 + 占用资源。下次设备重连会随 register_device 重新建。
            try:
                from app.services.mediamtx import remove_camera_path
                asyncio.create_task(remove_camera_path(did))
            except Exception as e:
                logger.error(f"[SocketIO] 触发 mediamtx 路径清理异常: {e}")
        except Exception as e:
            logger.error(f"[SocketIO] 断开时更新设备状态异常: {e}")

    if not to_remove:
        logger.info(f"[SocketIO] 客户端断开: sid={sid}")


@sio.event
async def register_device(sid: str, data: dict):
    """边缘端注册设备.

    边缘端连接后自动发送: {'device_id': 'cam-bl-01', 'camera_url': 'rtsp://...'}
    
    处理流程：
    1. 记录设备会话映射
    2. 更新数据库设备状态
    3. 如果有 camera_url，自动注册 mediamtx 拉流路径
    4. 广播设备状态更新
    """
    device_id = str(data.get("device_id", ""))
    if not device_id:
        logger.warning(f"[SocketIO] register_device 缺少 device_id: {data}")
        return

    # 边缘端可选传递摄像头地址
    camera_url = data.get("camera_url", "")
    # 设备元信息（边缘端注册时携带）
    device_name = data.get("device_name", "")
    device_manager = data.get("device_manager", "")
    area_manager = data.get("area_manager", "")
    area_manager_phone = data.get("area_manager_phone", "")
    work_location = data.get("work_location", "")
    ip_address = data.get("ip_address", "")
    safety_permit_no = data.get("safety_permit_no", "")
    work_content = data.get("work_content", "")
    work_level = data.get("work_level", "")
    # 作业详情字段（用于前端"工作详情信息"完整显示）
    work_type = data.get("work_type", "")
    confined_space = data.get("confined_space", "")
    work_start_time = data.get("work_start_time", "")
    work_end_time = data.get("work_end_time", "")
    work_status = data.get("work_status", "")
    
    _device_sessions[device_id] = sid
    logger.info(f"[SocketIO] 设备注册: device_id={device_id}, sid={sid}, camera_url={camera_url[:50] if camera_url else 'N/A'}")

    # 确认注册
    await sio.emit(
        "register_response", {"status": "ok", "device_id": device_id}, to=sid
    )

    # 更新数据库中的设备在线状态
    try:
        from sqlmodel import Session, select

        from app.db import engine
        from app.models.device import Device

        with Session(engine) as session:
            stmt = select(Device).where(Device.device_id == device_id)
            device = session.exec(stmt).first()
            now = datetime.datetime.now(datetime.timezone.utc)
            if device:
                device.is_online = True
                device.last_heartbeat = now
                if not device.online_since:
                    device.online_since = now
                # 如果边缘端传递了新的 camera_url，更新数据库
                # （camera_url 仍只在非空时覆盖：空 url 通常代表"未配置/由 ffmpeg 推流"，
                # 不应把 mediamtx 已注册的拉流地址洗掉）
                if camera_url and device.camera_url != camera_url:
                    device.camera_url = camera_url
                    logger.info(f"[SocketIO] 更新设备 camera_url: {device_id}")
                # device_name 仍只在非空时覆盖：避免某次 register 漏传导致设备名变空
                if device_name:
                    device.name = device_name
                # ── 业务字段：边缘端"信息编辑"传什么就用什么，允许清空 ─────────
                # 之前用 `if value:` 守卫导致：边缘端把字段清空后，后端不更新，
                # 前端永远看到旧值；改为无条件覆盖，与 work_end_time 行为一致。
                device.responsible_person = device_manager
                device.area_manager = area_manager
                device.area_manager_phone = area_manager_phone
                device.workshop = work_location
                device.ip_address = ip_address
                device.safety_permit_no = safety_permit_no
                device.work_content = work_content
                device.work_level = work_level
                device.work_type = work_type
                device.confined_space = confined_space
                device.work_start_time = work_start_time
                device.work_end_time = work_end_time
                device.work_status = work_status
                session.add(device)
                session.commit()
            else:
                # 设备不存在，自动注册
                device = Device(
                    device_id=device_id,
                    name=device_name or f"边缘设备-{device_id}",
                    camera_url=camera_url,
                    mediamtx_path=device_id,  # 默认用 device_id 作为路径名
                    is_online=True,
                    last_heartbeat=now,
                    online_since=now,
                    responsible_person=device_manager,
                    area_manager=area_manager,
                    area_manager_phone=area_manager_phone,
                    workshop=work_location,
                    ip_address=ip_address,
                    safety_permit_no=safety_permit_no,
                    work_content=work_content,
                    work_level=work_level,
                    work_type=work_type,
                    confined_space=confined_space,
                    work_start_time=work_start_time,
                    work_end_time=work_end_time,
                    work_status=work_status,
                )
                session.add(device)
                session.commit()
                logger.info(f"[SocketIO] 自动注册新设备: {device_id}")

        # 如果有 camera_url，自动注册 mediamtx 拉流路径
        if camera_url:
            try:
                from app.services.mediamtx import register_camera_path
                success = await register_camera_path(device_id, camera_url)
                if success:
                    logger.info(f"[SocketIO] mediamtx 路径注册成功: {device_id}")
                else:
                    logger.warning(f"[SocketIO] mediamtx 路径注册失败: {device_id}")
            except Exception as e:
                logger.error(f"[SocketIO] mediamtx 注册异常: {e}")

        # 通过 SSE 广播设备状态更新（含 online_since 供前端计算运行时长）
        # 同时把边缘端"信息编辑"上报的元信息一并广播，前端无需刷新即可看到变化
        from app.services.detection import detection_service

        broadcast_payload: dict = {
            "is_online": True,
            "online_since": now.isoformat(),
        }
        # name 仍只在非空时广播（与落库一致：避免某次 register 漏传洗成空名）
        if device_name:
            broadcast_payload["name"] = device_name
        # 业务字段无条件透传：边缘端清空 → 前端立即清空，与落库行为一致
        broadcast_payload["responsible_person"] = device_manager
        broadcast_payload["area_manager"] = area_manager
        broadcast_payload["area_manager_phone"] = area_manager_phone
        broadcast_payload["workshop"] = work_location
        broadcast_payload["ip_address"] = ip_address
        broadcast_payload["safety_permit_no"] = safety_permit_no
        broadcast_payload["work_content"] = work_content
        broadcast_payload["work_level"] = work_level
        broadcast_payload["work_type"] = work_type
        broadcast_payload["confined_space"] = confined_space
        broadcast_payload["work_start_time"] = work_start_time
        broadcast_payload["work_end_time"] = work_end_time
        broadcast_payload["work_status"] = work_status

        await detection_service.update_device_status(device_id, broadcast_payload)
    except Exception as e:
        logger.error(f"[SocketIO] 注册设备处理异常: {e}")


@sio.event
async def alarm_data(sid: str, data: dict):
    """接收边缘端告警数据.

    payload 格式（来自 alarm_manager.py）:
    {
        "image": "data:image/jpeg;base64,...",
        "idx": device_id,
        "note": "work_location",
        "type": "发现火焰",          # 事件类型（中文）
        "type2": "火焰检测",         # 事件类别
        "device_manager": "张三",
        "area_manager": "李四",
        "area_manager_phone": "13800138000",
        "time": "2026-06-10 14:30:00"
    }
    """
    device_id = str(data.get("idx", ""))
    event_type = data.get("type", "未知")
    event_category = data.get("type2", "未知")
    logger.info(f"[SocketIO] 收到告警: device={device_id}, type={event_type}, type2={event_category}")

    # 协议特性：边缘端通过 base64 内嵌图片，需要先落盘
    image_url = None
    image_b64 = data.get("image")
    if image_b64:
        image_url = _save_alarm_image(image_b64, device_id)

    # 委托给协议无关的 ingest 层
    try:
        from app.services.edge_ingest import ingest_alarm

        await ingest_alarm(
            device_id=device_id,
            severity=data.get("severity", "warning"),
            confidence=data.get("confidence", 0.9),
            note=data.get("note", ""),
            type=event_type,
            type2=event_category,
            image_url=image_url,
            device_manager=data.get("device_manager", ""),
            area_manager=data.get("area_manager", ""),
            area_manager_phone=data.get("area_manager_phone", ""),
            snapshot_device_name=data.get("device_name", ""),
            snapshot_ip_address=data.get("ip_address", ""),
            snapshot_safety_permit_no=data.get("safety_permit_no", ""),
            snapshot_workshop=data.get("work_location", ""),
            snapshot_work_content=data.get("work_content", ""),
            snapshot_work_level=data.get("work_level", ""),
            snapshot_work_type=data.get("work_type", ""),
            snapshot_confined_space=data.get("confined_space", ""),
            snapshot_work_start_time=data.get("work_start_time", ""),
            snapshot_work_end_time=data.get("work_end_time", ""),
            snapshot_work_status=data.get("work_status", ""),
            device_time=data.get("time", ""),
            log_prefix="[SocketIO]",
        )
    except Exception as e:
        logger.error(f"[SocketIO] 告警处理异常: {e}")


@sio.event
async def gas_data(sid: str, data: dict):
    """接收边缘端实时气体数据.

    payload 格式:
    {
        "device_id": "1",
        "device_name": "CAM-001",
        "note": "11,12号作业区",
        "C3H8": "450.5", "C2H2": "25.3", "CO2": "650.0",
        "HCN": "2.5", "O2": "20.5", "AR": "0.8", "H2S": "0.0",
        "TEMP": "28.3", "RH": "65.5",
        "update_time": "2026-06-10 14:30:00"
    }
    """
    device_id = str(data.get("device_id", ""))
    if not device_id:
        return

    try:
        from app.services.edge_ingest import ingest_gas_telemetry

        # 委托给协议无关 ingest 层；update_heartbeat=True 保留旧逻辑：
        # 边缘端的 gas_data 同时也算心跳信号。
        await ingest_gas_telemetry(
            device_id=device_id,
            payload=data,
            update_heartbeat=True,
            log_prefix="[SocketIO]",
        )
    except Exception as e:
        logger.error(f"[SocketIO] 气体数据处理异常: {e}")


@sio.event
async def gas_threshold(sid: str, data: dict):
    """接收边缘端气体阈值数据.

    暂存到 Service 层阈值缓存，后续可持久化。
    """
    device_id = str(data.get("device_id", data.get("idx", "")))
    if device_id:
        from app.services.detection import detection_service
        detection_service.update_threshold_cache(device_id, data)
        logger.info(f"[SocketIO] 气体阈值更新: device={device_id}")


@sio.event
async def config_push(sid: str, data: dict):
    """接收边缘端推送的检测配置.

    payload: {'device_id': '1', 'config': {...}}
    """
    device_id = str(data.get("device_id", ""))
    config = data.get("config")
    if not device_id or not config:
        return

    logger.info(f"[SocketIO] 收到设备配置: device={device_id}")

    try:
        from app.db import engine
        from app.models.device import Device
        from sqlmodel import Session, select
        import json

        with Session(engine) as session:
            stmt = select(Device).where(Device.device_id == device_id)
            device = session.exec(stmt).first()
            if device:
                # 合并配置
                existing = {}
                if device.config_json:
                    try:
                        existing = json.loads(device.config_json)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.debug(
                            f"[SocketIO] 现有 config_json 解析失败，按空合并: {e}"
                        )
                existing.update(config)
                device.config_json = json.dumps(existing, ensure_ascii=False)
                session.add(device)
                session.commit()
                logger.info(f"[SocketIO] 设备配置已更新: device={device_id}")
    except Exception as e:
        logger.error(f"[SocketIO] 配置处理异常: {e}")


@sio.event
async def detection_data(sid: str, data: dict):
    """接收边缘端检测框坐标数据.

    边缘端去掉 UDP 视频流后，改为通过 SocketIO 发送检测框坐标。
    复用 POST /api/detections/push 的同一套逻辑（SSE 广播给前端）。

    payload 格式:
    {
        "device_name": "cam1",        # 设备名（对应 mediamtx path）
        "device_id": "1",             # 可选，设备 ID
        "boxes": [
            {"x1": 100, "y1": 200, "x2": 300, "y2": 400, "color": [0,0,255], "label": "fire:0.92"},
            ...
        ],
        "timestamp": 1718000000.0
    }

    边缘端代码示例:
        sio.emit('detection_data', {
            'device_name': settings.device_name,
            'boxes': [{'x1': d.x1, 'y1': d.y1, 'x2': d.x2, 'y2': d.y2,
                        'color': list(color), 'label': f'{d.class_name}:{d.confidence:.2f}'}
                       for d in detections],
            'timestamp': time.time()
        })
    """
    # 允许边缘端用 device_id 代替 device_name
    device_name = data.get("device_name") or data.get("device_id", "unknown")
    if not data.get("device_name"):
        data["device_name"] = device_name

    try:
        from app.services.detection import detection_service
        from app.schemas.detection import DetectionPushDTO

        # 构造 DTO（允许额外字段如 device_id 透传）
        dto = DetectionPushDTO(**data)
        result = await detection_service.receive_push(dto)
        logger.info(f"[SocketIO] 检测框推送: {dto.device_name}, boxes={len(dto.boxes)}")
    except Exception as e:
        logger.error(f"[SocketIO] 检测框处理异常: {e}")


# ═══════════════════════════════════════════════════════
#  前端语音 → 边缘端 转发
# ═══════════════════════════════════════════════════════


@sio.event
async def voice_start(sid: str, data: dict):
    """前端发起语音通知，转发给边缘端.

    payload: {'device_id': '1'}
    """
    device_id = str(data.get("device_id", ""))
    if not device_id:
        logger.warning(f"[SocketIO] voice_start 缺少 device_id: {data}")
        return

    logger.info(f"[SocketIO] 语音开始: device={device_id}, from_sid={sid}")
    await push_voice_start(device_id)


@sio.event
async def voice_data(sid: str, data: dict):
    """前端发送语音数据，转发给边缘端.

    payload: {'device_id': '1', 'audio_chunk': bytes}
    """
    device_id = str(data.get("device_id", ""))
    audio_chunk = data.get("audio_chunk")
    if not device_id or not audio_chunk:
        logger.debug(f"[SocketIO] voice_data 数据无效: device_id={device_id}, has_chunk={audio_chunk is not None}")
        return

    await push_voice_data(device_id, audio_chunk)


@sio.event
async def voice_stop(sid: str, data: dict):
    """前端停止语音，转发给边缘端.

    payload: {'device_id': '1'}
    """
    device_id = str(data.get("device_id", ""))
    if not device_id:
        return

    logger.info(f"[SocketIO] 语音停止: device={device_id}, from_sid={sid}")
    await push_voice_stop(device_id)


# ═══════════════════════════════════════════════════════
#  服务端 → 边缘端 推送接口
# ═══════════════════════════════════════════════════════


async def push_command(device_id: str, cmd_type: str, value=None):
    """向边缘端推送控制命令.

    边缘端通过 on('command') 接收。
    """
    sid = _device_sessions.get(device_id)
    if sid:
        await sio.emit("command", {"type": cmd_type, "value": value}, to=sid)
        logger.info(
            f"[SocketIO] 推送命令: device={device_id}, type={cmd_type}, value={value}"
        )
    else:
        logger.warning(f"[SocketIO] 设备不在线，无法推送命令: device={device_id}")


async def push_config_update(device_id: str, config: dict):
    """向边缘端推送配置更新.

    边缘端通过 on('config_update') 接收。
    """
    sid = _device_sessions.get(device_id)
    if sid:
        await sio.emit("config_update", {"config": config}, to=sid)
        logger.info(f"[SocketIO] 推送配置更新: device={device_id}")
    else:
        logger.warning(f"[SocketIO] 设备不在线，无法推送配置: device={device_id}")


async def push_voice_start(device_id: str):
    """通知边缘端开始语音."""
    sid = _device_sessions.get(device_id)
    if sid:
        await sio.emit("voice_start", {}, to=sid)
        logger.info(f"[SocketIO] 转发 voice_start → 边缘端: device={device_id}")
    else:
        logger.warning(f"[SocketIO] voice_start 设备不在线，无法转发: device={device_id}, 在线设备={list(_device_sessions.keys())}")


async def push_voice_data(device_id: str, audio_chunk):
    """转发语音数据到边缘端."""
    sid = _device_sessions.get(device_id)
    if sid:
        await sio.emit("voice_data", {"audio_chunk": audio_chunk}, to=sid)
    else:
        logger.debug(f"[SocketIO] voice_data 设备不在线，丢弃音频: device={device_id}")


async def push_voice_stop(device_id: str):
    """通知边缘端停止语音."""
    sid = _device_sessions.get(device_id)
    if sid:
        await sio.emit("voice_stop", {}, to=sid)
        logger.info(f"[SocketIO] 转发 voice_stop → 边缘端: device={device_id}")
    else:
        logger.warning(f"[SocketIO] voice_stop 设备不在线，无法转发: device={device_id}")


def is_device_online(device_id: str) -> bool:
    """检查设备是否通过 SocketIO 在线."""
    return device_id in _device_sessions


def get_online_devices() -> list[str]:
    """获取所有通过 SocketIO 在线的设备 ID."""
    return list(_device_sessions.keys())


def get_threshold_cache() -> dict:
    """获取阈值缓存（供气体监控页使用）.

    委托给 DetectionService 的阈值缓存。
    """
    from app.services.detection import detection_service
    return detection_service.get_threshold_cache()
