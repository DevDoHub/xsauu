"""设备路由.

⚠️ 路由声明顺序约定：FastAPI/Starlette 按注册顺序匹配路由。
所有**字面量路径**必须排在带路径参数的路径**之前**，否则会被
`/devices/{device_pk:int}` 这类带类型校验的路径抢先匹配并返回 422。

本文件分组：
  1. 集合操作        : POST /devices/, GET /devices/
  2. 字面量子路径    : /devices/count, /devices/persons, /devices/ip-map,
                       /devices/grouped/*, /devices/by-id/*, /devices/socketio/*
  3. 参数化主键路径  : /devices/{device_pk}, /devices/{device_pk}/...
  4. 参数化业务子路径: /devices/{device_id}/config, /devices/{device_id}/control/*
"""

from fastapi import APIRouter, Query

from app.db import SessionDep
from app.schemas.device import (
    CameraControlDTO,
    ControlCommandRespVO,
    DetectionControlDTO,
    DeviceConfigDTO,
    DeviceConfigRespVO,
    DeviceCountRespVO,
    DeviceCreateDTO,
    DeviceGroupedByAreaVO,
    DeviceGroupedByPersonVO,
    DeviceIpMapRespVO,
    DeviceListRespVO,
    DeviceRespVO,
    DeviceUpdateDTO,
    SocketIOStatusRespVO,
)
from app.services.device import DeviceService

router = APIRouter(prefix="", tags=["设备管理"])


# ── 1. 集合操作 ──────────────────────────────────────────────────────────────


@router.post("/devices/", response_model=DeviceRespVO, summary="注册设备")
def register_device(payload: DeviceCreateDTO, session: SessionDep):
    """注册新设备，mediamtx_path 为空时自动使用 device_id."""
    svc = DeviceService(session)
    return svc.register_device(payload)


@router.get("/devices/", response_model=DeviceListRespVO, summary="设备列表")
def list_devices(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """分页查询设备列表."""
    svc = DeviceService(session)
    return svc.list_devices(page=page, page_size=page_size)


# ── 2. 字面量子路径（必须在 /{device_pk} 之前） ──────────────────────────────


@router.get("/devices/count", response_model=DeviceCountRespVO, summary="获取设备在线/总数")
def get_device_count(session: SessionDep):
    """返回设备总数和在线数统计（在线状态从 MediaMTX 实时获取）."""
    svc = DeviceService(session)
    return svc.get_device_counts()


@router.get("/devices/persons", summary="获取所有负责人列表")
def list_all_persons(session: SessionDep):
    """返回所有设备负责人列表（直接返回数组，兼容旧系统 /all_persons）."""
    svc = DeviceService(session)
    return svc.list_all_persons()


@router.get("/devices/ip-map", response_model=DeviceIpMapRespVO, summary="获取所有设备IP映射")
def get_device_ip_map(session: SessionDep):
    """返回 {device_id: {ip, name}} 映射."""
    svc = DeviceService(session)
    return svc.get_device_ip_map()


@router.get("/devices/grouped/by-person", response_model=DeviceGroupedByPersonVO, summary="按负责人分组查询设备")
def list_devices_grouped_by_person(session: SessionDep):
    """返回按负责人分组的设备列表，兼容旧系统 /search_device 接口."""
    svc = DeviceService(session)
    return svc.list_devices_grouped_by_person()


@router.get("/devices/grouped/by-area", response_model=DeviceGroupedByAreaVO, summary="按区域负责人分组查询设备")
def list_devices_grouped_by_area(session: SessionDep):
    """返回按区域负责人二级分组的设备列表，兼容旧系统 /search_device_by_device_manager 接口."""
    svc = DeviceService(session)
    return svc.list_devices_grouped_by_area()


@router.get("/devices/by-id/{device_id}", response_model=DeviceRespVO, summary="按设备ID获取详情")
def get_device_by_id(device_id: str, session: SessionDep):
    """按 device_id 获取设备详情."""
    svc = DeviceService(session)
    return svc.get_device_by_device_id(device_id)


@router.get("/devices/socketio/status", response_model=SocketIOStatusRespVO, summary="SocketIO 兼容层状态")
def get_socketio_status(session: SessionDep):
    """返回 SocketIO 兼容层的连接状态（调试用）."""
    svc = DeviceService(session)
    return svc.get_socketio_status()


# ── 3. 参数化主键路径 ────────────────────────────────────────────────────────


@router.get("/devices/{device_pk}", response_model=DeviceRespVO, summary="获取设备详情")
def get_device(device_pk: int, session: SessionDep):
    """按数据库主键获取设备详情."""
    svc = DeviceService(session)
    return svc.get_device(device_pk)


@router.put("/devices/{device_pk}", response_model=DeviceRespVO, summary="更新设备信息")
def update_device(device_pk: int, payload: DeviceUpdateDTO, session: SessionDep):
    """更新设备信息."""
    svc = DeviceService(session)
    return svc.update_device(device_pk, payload)


# ── 4. 参数化业务子路径（device_id 是字符串，与 device_pk:int 不冲突） ───────


@router.get("/devices/{device_id}/config", response_model=DeviceConfigRespVO, summary="获取设备配置")
def get_device_config(device_id: str, session: SessionDep):
    """获取设备的检测配置."""
    svc = DeviceService(session)
    return svc.get_device_config(device_id)


@router.put("/devices/{device_id}/config", response_model=DeviceConfigRespVO, summary="更新设备配置")
def update_device_config(device_id: str, payload: DeviceConfigDTO, session: SessionDep):
    """更新设备检测配置（增量合并），同时通过 SocketIO 推送配置更新到边缘端."""
    svc = DeviceService(session)
    result = svc.update_device_config(device_id, payload)

    # SocketIO 兼容：推送配置更新到边缘端
    svc.push_config_update(device_id, result.config)

    return result


@router.post("/devices/{device_id}/control/camera", response_model=ControlCommandRespVO, summary="摄像头方向控制")
def control_camera(device_id: str, payload: CameraControlDTO, session: SessionDep):
    """通过 MQTT 发送摄像头控制命令，同时兼容 SocketIO 设备.

    direction: up/down/left/right/stop/zoom_in/zoom_out/auto/reconnect/disconnect
    """
    svc = DeviceService(session)
    return svc.control_camera(device_id, payload.direction)


@router.post("/devices/{device_id}/control/detection", response_model=ControlCommandRespVO, summary="开始/停止检测")
def control_detection(device_id: str, payload: DetectionControlDTO, session: SessionDep):
    """通过 MQTT 发送检测控制命令，同时兼容 SocketIO 设备.

    action: start/stop
    """
    svc = DeviceService(session)
    return svc.control_detection(device_id, payload.action)
