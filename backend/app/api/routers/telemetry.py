"""遥测数据路由."""

from fastapi import APIRouter, Query

from app.db import SessionDep
from app.schemas.telemetry import TelemetryListRespVO, TelemetryRespVO
from app.services.telemetry import TelemetryService

router = APIRouter(prefix="", tags=["遥测数据"])


@router.get("/telemetry/", response_model=TelemetryListRespVO, summary="遥测数据列表")
def list_telemetry(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    device_id: str | None = Query(None, description="按设备筛选"),
    sensor_type: str | None = Query(None, description="按传感器类型筛选"),
):
    svc = TelemetryService(session)
    return svc.list_telemetry(
        page=page,
        page_size=page_size,
        device_id=device_id,
        sensor_type=sensor_type,
    )


@router.get("/telemetry/realtime", summary="获取所有设备实时遥测数据")
def get_realtime(session: SessionDep):
    """获取所有设备的最新遥测数据，按设备分组.

    用于气体监控页面展示实时气体浓度、温度等数据.
    """
    svc = TelemetryService(session)
    data = svc.get_realtime()
    return {"data": data}


@router.get("/telemetry/history", summary="获取设备遥测历史")
def get_history(
    session: SessionDep,
    device_id: str = Query(..., description="设备 ID"),
    sensor_type: str | None = Query(None, description="传感器类型"),
    hours: int = Query(24, ge=1, le=720, description="查询小时数"),
):
    """获取指定设备的遥测历史数据."""
    svc = TelemetryService(session)
    items = svc.get_history(device_id, sensor_type, hours)
    return {"data": items, "device_id": device_id, "hours": hours}
