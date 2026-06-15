"""检测框数据路由.

迁移自 poc-sau/deploy/serve.py 的检测框相关功能。
提供：
- POST /push: 边缘端推送检测框数据
- GET /events: SSE 流，前端订阅实时检测框
- GET /latest: 返回所有设备最新检测框快照
- 检测控制: global / batch / by-person
- 设备状态 SSE: device-status/events, device-status/latest
- 气体数据 SSE: gas/events, gas/latest, gas/threshold, gas/registry, gas_monitor_data
- 告警 SSE: alarm/events, alarm/latest

气体数据模拟（开发环境用，非 HTTP 端点，由 main.py lifespan 启动）：
- start_gas_simulation() / stop_gas_simulation()
"""

import asyncio
import datetime
import math
import random

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.db import SessionDep
from app.logger import logger
from app.schemas.detection import (
    BatchDetectionControlDTO,
    BatchDetectionControlRespVO,
    DetectionControlDTO,
    DetectionPushDTO,
    DetectionPushRespVO,
    GAS_REGISTRY,
    GasMonitorDataRespVO,
    GasThresholdRespVO,
    GlobalDetectionControlRespVO,
    PersonDetectionControlDTO,
    PersonDetectionControlRespVO,
)
from app.services.detection import detection_service

router = APIRouter(prefix="", tags=["检测框"])


# 设备名 → mediamtx 视频路径映射（部署时人工保证 MediaMTX path = 设备 SN）
DEVICE_PATH_MAP: dict[str, str] = {}

# 初始化映射
detection_service.device_path_map = DEVICE_PATH_MAP


# ── 检测框推送 ───────────────────────────────────────────────────────────────


@router.post("/detections/push", summary="边缘端推送检测框数据", response_model=DetectionPushRespVO)
async def receive_push(payload: DetectionPushDTO) -> DetectionPushRespVO:
    """接收边缘端推送的检测框数据."""
    return await detection_service.receive_push(payload)


@router.get("/detections/events", summary="SSE 流 - 实时检测框推送")
async def sse_stream(request: Request) -> StreamingResponse:
    """SSE 流，前端订阅实时检测框."""
    return StreamingResponse(
        detection_service.get_sse_stream(request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/detections/latest", summary="获取所有设备最新检测框快照")
async def get_latest_detections() -> list[dict]:
    """返回所有设备最新检测框快照."""
    return await detection_service.get_latest_detections()


@router.get("/detections/device/{device_name}", summary="获取指定设备最新检测框")
async def get_device_detection(device_name: str) -> dict | None:
    """返回指定设备的最新检测框数据."""
    return await detection_service.get_device_detection(device_name)


# ── 检测控制 ─────────────────────────────────────────────────────────────────


@router.post("/detections/control/global", summary="全局检测控制", response_model=GlobalDetectionControlRespVO)
async def control_global_detection(payload: DetectionControlDTO) -> GlobalDetectionControlRespVO:
    """通过 MQTT 发送全局检测控制命令."""
    return detection_service.control_global_detection(payload.action)


@router.post("/detections/control/batch", summary="批量检测控制", response_model=BatchDetectionControlRespVO)
async def control_batch_detection(payload: BatchDetectionControlDTO) -> BatchDetectionControlRespVO:
    """通过 MQTT 发送批量检测控制命令."""
    return detection_service.control_batch_detection(payload.device_ids, payload.action)


@router.post("/detections/control/by-person", summary="按负责人控制检测", response_model=PersonDetectionControlRespVO)
async def control_detection_by_person(payload: PersonDetectionControlDTO, session: SessionDep) -> PersonDetectionControlRespVO:
    """通过 MQTT 发送按负责人检测控制命令."""
    return detection_service.control_detection_by_person(payload.person, payload.action, session)


# ── 设备状态 SSE ─────────────────────────────────────────────────────────────


@router.get("/detections/device-status/events", summary="SSE 流 - 设备状态推送")
async def device_status_sse_stream(request: Request) -> StreamingResponse:
    """SSE 流，前端订阅设备状态变化."""
    return StreamingResponse(
        detection_service.get_device_status_sse_stream(request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/detections/device-status/latest", summary="获取所有设备最新状态")
async def get_latest_device_status() -> dict[str, dict]:
    """返回所有设备最新状态快照."""
    return await detection_service.get_latest_device_status()


# ── 气体数据 SSE ─────────────────────────────────────────────────────────────


@router.get("/detections/gas/events", summary="SSE 流 - 气体数据推送")
async def gas_data_sse_stream(request: Request) -> StreamingResponse:
    """SSE 流，前端订阅气体数据变化."""
    return StreamingResponse(
        detection_service.get_gas_sse_stream(request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/detections/gas/latest", summary="获取所有设备最新气体数据")
async def get_latest_gas_data() -> dict[str, dict]:
    """返回所有设备最新气体数据快照."""
    return await detection_service.get_latest_gas_data()


# ── 告警 SSE ─────────────────────────────────────────────────────────────────


@router.get("/detections/alarm/events", summary="SSE 流 - 告警推送")
async def alarm_sse_stream(request: Request) -> StreamingResponse:
    """SSE 流，前端订阅告警事件."""
    return StreamingResponse(
        detection_service.get_alarm_sse_stream(request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/detections/alarm/latest", summary="获取最近告警列表")
async def get_latest_alarms() -> list[dict]:
    """返回最近的告警列表（最多100条）."""
    return await detection_service.get_latest_alarms()


# ── 气体监控数据接口（驾驶舱专用） ───────────────────────────────────────────


@router.get("/detections/gas_monitor_data", summary="获取气体监控数据", response_model=GasMonitorDataRespVO)
async def get_gas_monitor_data() -> GasMonitorDataRespVO:
    """获取气体监控数据，返回格式与旧后端完全一致: {realtime, threshold, registry}."""
    return await detection_service.get_gas_monitor_data()


@router.get("/detections/gas/threshold", summary="获取气体阈值配置", response_model=GasThresholdRespVO)
async def get_gas_threshold() -> GasThresholdRespVO:
    """返回气体阈值配置: {data: {device_id: {...}}}."""
    return await detection_service.get_gas_threshold()


@router.get("/detections/gas/registry", summary="获取气体类型注册表")
async def get_gas_registry() -> list[dict]:
    """返回支持的气体类型注册表."""
    return GAS_REGISTRY


# ── 气体数据模拟（开发环境用） ────────────────────────────────────────────────
# 仅供 main.py lifespan 在 ENVIRONMENT == "local" 时调用，
# 不暴露为 HTTP 端点（前端无需启停模拟）。
# 边缘端真实数据接入后，把 main.py 中的 start_gas_simulation() 调用去掉即可。

SIMULATED_DEVICES = ["0CCCHS6AZ3173341", "0CCCHS6AZ3173342"]
DEVICE_NOTES = {"0CCCHS6AZ3173341": "3,4号作业区", "0CCCHS6AZ3173342": "11,12号作业区"}
_simulation_task: asyncio.Task | None = None
_simulation_running = False


async def _generate_gas_simulation() -> None:
    """后台任务：每 2 秒生成模拟气体数据，更新到 detection_service."""
    t = 0
    while _simulation_running:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for device_id in SIMULATED_DEVICES:
            temp = 25.0 + 10 * math.sin(t / 30) + random.uniform(-2, 2)
            rh = 60.0 + 10 * math.sin(t / 20 + 1) + random.uniform(-3, 3)
            c3h8 = 200.0 + 200 * math.sin(t / 25) + random.uniform(-30, 30)
            c2h2 = 100.0 + 80 * math.sin(t / 18) + random.uniform(-20, 20)
            co2 = 500.0 + 300 * math.sin(t / 22) + random.uniform(-50, 50)
            hcn = 2.0 + 2 * math.sin(t / 15) + random.uniform(-0.5, 0.5)
            o2 = 20.0 + 2 * math.sin(t / 35) + random.uniform(-0.5, 0.5)

            # 偶发尖峰，便于测试告警阈值
            if random.random() < 0.08:
                c2h2 = random.uniform(260, 350)
            if random.random() < 0.05:
                c3h8 = random.uniform(420, 600)
            if random.random() < 0.03:
                hcn = random.uniform(6, 10)

            gas_data = {
                "C3H8": str(round(max(0, c3h8), 1)),
                "C2H2": str(round(max(0, c2h2), 1)),
                "CO2": str(round(max(0, co2), 1)),
                "HCN": str(round(max(0, hcn), 2)),
                "O2": str(round(max(0, o2), 1)),
                "AR": "0.0",
                "H2S": "0.0",
                "TEMP": str(round(temp, 1)),
                "RH": str(round(rh, 1)),
                "device_id": device_id,
                "device_name": device_id,
                "note": DEVICE_NOTES.get(device_id, ""),
                "update_time": now_str,
            }
            await detection_service.update_gas_data(device_id, gas_data)
        t += 2
        await asyncio.sleep(2)


async def start_gas_simulation() -> None:
    """启动后台气体数据模拟任务（幂等）."""
    global _simulation_task, _simulation_running
    if _simulation_running:
        return
    _simulation_running = True
    _simulation_task = asyncio.create_task(_generate_gas_simulation())
    logger.info("[dev] 气体数据模拟已启动")


async def stop_gas_simulation() -> None:
    """停止后台气体数据模拟任务（幂等，供 lifespan 关闭时调用）."""
    global _simulation_task, _simulation_running
    if not _simulation_running:
        return
    _simulation_running = False
    if _simulation_task:
        _simulation_task.cancel()
        _simulation_task = None
    logger.info("[dev] 气体数据模拟已停止")
