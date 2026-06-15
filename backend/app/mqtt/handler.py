"""MQTT 消息处理器.

注册到 subscriber，处理边缘端上报的告警、遥测、心跳消息。

业务逻辑（入库 + SSE 广播）已下沉到 ``app.services.edge_ingest``，
本模块只做 MQTT 协议适配（topic 解析、payload 字段映射、线程桥接）。
"""

import asyncio

from loguru import logger

from app.mqtt.subscriber import mqtt_subscriber


def _run_async(coro):
    """在 MQTT 线程中安全地运行异步函数.

    MQTT 回调运行在单独的线程中，需要通过 call_soon_threadsafe
    将协程调度到主线程的事件循环中执行。
    """
    try:
        loop = asyncio.get_running_loop()
        # 事件循环正在运行（主线程），使用 call_soon_threadsafe 调度
        asyncio.run_coroutine_threadsafe(coro, loop)
    except RuntimeError:
        # 没有正在运行的事件循环，直接运行
        try:
            asyncio.run(coro)
        except Exception as e:
            logger.error(f"异步任务执行失败: {e}")


def handle_alarm(topic: str, payload: dict) -> None:
    """处理告警消息.

    topic 格式: xsau/edge/{device_id}/alarm
    payload 示例（兼容边缘端 SocketIO 格式）:
    {
        "severity": "warning",
        "confidence": 0.92,
        "description": "检测到未佩戴安全帽",
        "bbox": "[100, 200, 300, 400]",
        "image_url": "alarm_images/xxx.jpg",
        "note": "白龙外场车间",
        "type": "没有安全帽",
        "type2": "安全文明着装",
        "device_manager": "张三",
        "area_manager": "李四",
        "area_manager_phone": "13800138000",
        "time": "2026-06-10 14:30:00"
    }
    """
    from app.services.edge_ingest import ingest_alarm

    device_id = topic.split("/")[2]
    event_type = payload.get("type", "未知")
    event_category = payload.get("type2", "未知")
    logger.info(f"收到告警 [{device_id}]: type={event_type}, type2={event_category}")

    # 协议适配：把 MQTT payload 字段映射到 edge_ingest.ingest_alarm 的关键字参数
    _run_async(ingest_alarm(
        device_id=device_id,
        severity=payload.get("severity", "warning"),
        confidence=payload.get("confidence", 0.0),
        description=payload.get("description", ""),
        note=payload.get("note", ""),
        type=event_type,
        type2=event_category,
        image_url=payload.get("image_url"),
        bbox=payload.get("bbox"),
        device_manager=payload.get("device_manager", ""),
        area_manager=payload.get("area_manager", ""),
        area_manager_phone=payload.get("area_manager_phone", ""),
        snapshot_device_name=payload.get("device_name", ""),
        snapshot_ip_address=payload.get("ip_address", ""),
        snapshot_safety_permit_no=payload.get("safety_permit_no", ""),
        snapshot_workshop=payload.get("work_location", ""),
        snapshot_work_content=payload.get("work_content", ""),
        snapshot_work_level=payload.get("work_level", ""),
        snapshot_work_type=payload.get("work_type", ""),
        snapshot_confined_space=payload.get("confined_space", ""),
        snapshot_work_start_time=payload.get("work_start_time", ""),
        snapshot_work_end_time=payload.get("work_end_time", ""),
        snapshot_work_status=payload.get("work_status", ""),
        device_time=payload.get("time", ""),
        log_prefix="",  # MQTT 不加前缀，与历史日志风格一致
    ))


def handle_telemetry(topic: str, payload: dict) -> None:
    """处理遥测数据.

    支持两种格式：
    1. 新格式（单传感器）：
       topic: xsau/edge/{device_id}/telemetry
       payload: {"sensor_type": "gas_co", "value": 23.5, "unit": "ppm"}

    2. 旧格式（多传感器合并）：
       topic: xsau/edge/{device_id}/telemetry
       payload: {
           "device_id": "1",
           "C3H8": "100", "C2H2": "50", "CO2": "200",
           "TEMP": "25", "RH": "60"
       }
    """
    from app.services.edge_ingest import ingest_gas_telemetry

    device_id = topic.split("/")[2]

    # 新格式（单传感器）：转成与旧格式一致的"传感器名 → 数值"字典再入库
    if "sensor_type" in payload:
        sensor_type = payload.get("sensor_type", "unknown")
        value = payload.get("value", 0.0)
        gas_payload = {sensor_type: value}
        # 注意：单传感器格式没有 is_overlimit/threshold/unit 的载体；
        # 现有 ingest_gas_telemetry 不存这三个字段（默认空/False）。
        # 如未来需要保留，可在 ingest 层做扩展。
    else:
        # 旧格式（多传感器合并）直接透传
        gas_payload = payload

    _run_async(ingest_gas_telemetry(
        device_id=device_id,
        payload=gas_payload,
        update_heartbeat=False,  # MQTT 心跳走独立 topic
        log_prefix="",
    ))


def handle_heartbeat(topic: str, payload: dict) -> None:
    """处理心跳消息.

    topic 格式: xsau/edge/{device_id}/heartbeat
    payload 示例: {"status": "ok"}
    """
    from app.services.edge_ingest import ingest_heartbeat

    device_id = topic.split("/")[2]
    logger.debug(f"心跳 [{device_id}]")
    _run_async(ingest_heartbeat(device_id))


def register_mqtt_handlers() -> None:
    """注册所有 MQTT 消息处理器，在应用启动时调用."""
    from app.settings import settings

    mqtt_subscriber.register_handler(settings.MQTT_TOPIC_ALARM, handle_alarm)
    mqtt_subscriber.register_handler(settings.MQTT_TOPIC_TELEMETRY, handle_telemetry)
    mqtt_subscriber.register_handler(settings.MQTT_TOPIC_HEARTBEAT, handle_heartbeat)

    logger.info("MQTT 消息处理器注册完成")
