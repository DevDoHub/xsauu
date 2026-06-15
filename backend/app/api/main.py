"""API 路由聚合模块.

将所有子路由注册到统一的 api_router。
"""

from fastapi import APIRouter

from app.api.routers import (
    alarms,
    detections,
    devices,
    mediamtx_proxy,
    system_config,
    telemetry,
    users,
)

api_router = APIRouter()

api_router.include_router(users.router)
api_router.include_router(devices.router)
api_router.include_router(alarms.router)
api_router.include_router(telemetry.router)
api_router.include_router(detections.router)
api_router.include_router(mediamtx_proxy.router)
api_router.include_router(system_config.router)
