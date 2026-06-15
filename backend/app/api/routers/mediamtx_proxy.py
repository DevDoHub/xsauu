"""mediamtx 代理路由.

提供 mediamtx API 的反向代理，避免前端 CORS 问题。
同时提供路径列表的格式化输出。
"""

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.logger import logger

router = APIRouter(prefix="", tags=["mediamtx"])

# mediamtx API 地址
MEDIAMTX_API = "http://127.0.0.1:9997"


@router.get("/mediamtx/paths", summary="获取 mediamtx 在线路径列表")
async def get_paths():
    """代理 mediamtx 控制 API，返回在线路径列表.

    前端可以通过此接口获取当前可用的视频流路径，用于 WebRTC 播放。
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MEDIAMTX_API}/v3/paths/list")
            response.raise_for_status()
            data = response.json()

            # 返回原始数据
            return data
    except httpx.TimeoutException:
        logger.warning("获取 mediamtx 路径超时")
        return JSONResponse(
            status_code=502,
            content={"error": "mediamtx API 超时", "items": []}
        )
    except httpx.HTTPStatusError as e:
        logger.warning(f"mediamtx API 返回错误: {e.response.status_code}")
        return JSONResponse(
            status_code=502,
            content={"error": f"mediamtx API 错误: {e.response.status_code}", "items": []}
        )
    except Exception as e:
        logger.error(f"获取 mediamtx 路径失败: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": str(e), "items": []}
        )


@router.get("/mediamtx/paths/simple", summary="获取简化的路径列表")
async def get_paths_simple():
    """返回简化的路径列表，仅包含路径名和状态.

    适用于前端快速获取可用视频流列表。
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MEDIAMTX_API}/v3/paths/list")
            response.raise_for_status()
            data = response.json()

            # 简化输出
            items = []
            for item in data.get("items", []):
                items.append({
                    "name": item.get("name"),
                    "ready": item.get("ready", False),
                    "source": item.get("source", {}).get("type"),
                })

            return {"items": items}
    except Exception as e:
        logger.error(f"获取 mediamtx 路径失败: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": str(e), "items": []}
        )


@router.get("/mediamtx/config", summary="获取 mediamtx 配置信息")
async def get_config():
    """返回 mediamtx 的 WebRTC 和其他配置信息.

    用于前端构建正确的播放地址。
    """
    return {
        "webrtc": {
            "base_url": f"http://localhost:8889",
            "endpoint_template": "http://localhost:8889/{path}/whep",
        },
        "hls": {
            "base_url": "http://localhost:8888",
            "endpoint_template": "http://localhost:8888/{path}/index.m3u8",
        },
        "api": {
            "base_url": MEDIAMTX_API,
        },
    }


@router.post("/mediamtx/sync", summary="同步数据库设备到 mediamtx")
async def sync_devices_to_mediamtx():
    """将数据库中有 camera_url 的设备同步注册到 mediamtx.
    
    用于：
    - 首次部署时批量注册
    - 手动修复 mediamtx 路径
    - 新增设备后批量同步
    
    返回: {added: int, errors: list}
    """
    try:
        from sqlmodel import Session, select
        from app.db import engine
        from app.models.device import Device

        # 查询所有有 camera_url 的设备
        with Session(engine) as session:
            stmt = select(Device).where(Device.camera_url != "")
            devices = session.exec(stmt).all()
            device_list = [
                {"device_id": d.device_id, "camera_url": d.camera_url}
                for d in devices
            ]

        if not device_list:
            return {"message": "没有配置 camera_url 的设备", "added": 0, "errors": []}

        # 调用同步服务
        from app.services.mediamtx import sync_device_paths
        result = await sync_device_paths(device_list)

        return {
            "message": f"同步完成: {result['added']} 个设备已注册",
            **result
        }
    except Exception as e:
        logger.error(f"同步设备到 mediamtx 失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "added": 0, "errors": [str(e)]}
        )


@router.post("/mediamtx/paths/{device_id}/register", summary="手动注册单个设备到 mediamtx")
async def register_single_device(device_id: str, rtsp_url: str):
    """手动注册单个设备的拉流路径到 mediamtx.
    
    Args:
        device_id: 设备 ID（同时作为 mediamtx 路径名）
        rtsp_url: RTSP 地址
        
    Returns:
        {success: bool, message: str}
    """
    try:
        from app.services.mediamtx import register_camera_path
        success = await register_camera_path(device_id, rtsp_url)
        if success:
            return {"success": True, "message": f"已注册路径: {device_id}"}
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "注册失败，请检查 mediamtx 服务"}
            )
    except Exception as e:
        logger.error(f"手动注册路径失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )
