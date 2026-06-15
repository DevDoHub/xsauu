"""MediaMTX 动态路径管理服务.

通过 MediaMTX REST API 动态添加/删除摄像头拉流路径，
实现边缘端注册时自动配置视频流。

API 参考 (mediamtx v1.x)：
    POST   /v3/config/paths/add/{name}     新增 path（已存在 → 400）
    PATCH  /v3/config/paths/patch/{name}   更新已有 path
    DELETE /v3/config/paths/delete/{name}  删除 path
    GET    /v3/paths/list                  列出当前活跃 path

设计要点：
    - 注册时使用 "upsert" 语义：先 PATCH，失败再 ADD，避免重连导致 400。
    - device_id 同时是 mediamtx 路径名（与边缘端 device_name 单一身份源对齐）。
"""

import httpx
from loguru import logger

from app.settings import settings

MEDIAMTX_API = settings.MEDIAMTX_API_URL


def _path_payload(rtsp_url: str) -> dict:
    """统一构建 mediamtx path 配置 payload。

    A 端 mediamtx 拉的是 B 端 mediamtx 代理的 RTSP，
    所以 source 用 rtsp:// 即可，不需要 ffmpeg runOnDemand。
    """
    return {
        "source": rtsp_url,
        # 海康/RTSP 链路：TCP 比 UDP 稳得多
        "rtspTransport": "tcp",
        # 按需拉流：前端没人看 → A 不拉 B → B 不拉 C
        "sourceOnDemand": True,
        "sourceOnDemandStartTimeout": "10s",
        "sourceOnDemandCloseAfter": "10s",
    }


async def register_camera_path(device_id: str, rtsp_url: str) -> bool:
    """边缘端注册时，在 MediaMTX 创建 / 更新拉流路径 (upsert).

    Args:
        device_id: 设备唯一标识，同时作为 mediamtx 路径名
        rtsp_url:  上游 RTSP 地址（生产环境是 B 端 mediamtx 的代理 URL）

    Returns:
        bool: 是否成功

    示例:
        await register_camera_path(
            "0CCCHS6AZ3173341",
            "rtsp://192.168.3.8:8554/0CCCHS6AZ3173341",
        )
    """
    payload = _path_payload(rtsp_url)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 先尝试 PATCH（已存在时更新，避免 400 冲突）
            patch_resp = await client.patch(
                f"{MEDIAMTX_API}/v3/config/paths/patch/{device_id}",
                json=payload,
            )
            if patch_resp.status_code in (200, 204):
                logger.info(
                    f"[MediaMTX] 已更新拉流路径 (patch): {device_id} → {rtsp_url}"
                )
                return True

            # PATCH 在 path 不存在时会返回 400 / 404，回退到 ADD
            if patch_resp.status_code in (400, 404):
                add_resp = await client.post(
                    f"{MEDIAMTX_API}/v3/config/paths/add/{device_id}",
                    json=payload,
                )
                if add_resp.status_code in (200, 201, 204):
                    logger.info(
                        f"[MediaMTX] 已注册拉流路径 (add): {device_id} → {rtsp_url}"
                    )
                    return True
                logger.error(
                    f"[MediaMTX] add 失败: {device_id}, "
                    f"HTTP {add_resp.status_code}, body={add_resp.text[:200]}"
                )
                return False

            # 其他错误码：直接报错
            logger.error(
                f"[MediaMTX] patch 失败: {device_id}, "
                f"HTTP {patch_resp.status_code}, body={patch_resp.text[:200]}"
            )
            return False
    except httpx.TimeoutException:
        logger.error(f"[MediaMTX] 注册路径超时: {device_id}")
        return False
    except Exception as e:
        logger.error(f"[MediaMTX] 注册路径异常: {device_id}, {e}")
        return False


async def remove_camera_path(device_id: str) -> bool:
    """设备下线或删除时，移除 MediaMTX 路径.
    
    Args:
        device_id: 设备唯一标识
        
    Returns:
        bool: 是否成功
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.delete(
                f"{MEDIAMTX_API}/v3/config/paths/delete/{device_id}"
            )
            response.raise_for_status()
            logger.info(f"[MediaMTX] 已删除路径: {device_id}")
            return True
    except Exception as e:
        logger.error(f"[MediaMTX] 删除路径异常: {device_id}, {e}")
        return False


async def check_path_exists(device_id: str) -> bool:
    """检查 MediaMTX 路径是否存在.
    
    Args:
        device_id: 设备唯一标识
        
    Returns:
        bool: 路径是否存在
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{MEDIAMTX_API}/v3/paths/list")
            response.raise_for_status()
            data = response.json()
            existing_paths = {item["name"] for item in data.get("items", [])}
            return device_id in existing_paths
    except Exception as e:
        logger.warning(f"[MediaMTX] 检查路径失败: {e}")
        return False


async def sync_device_paths(devices: list[dict]) -> dict:
    """同步数据库中的设备列表到 MediaMTX.
    
    用于启动时或手动同步，确保 MediaMTX 路径与数据库一致。
    
    Args:
        devices: 设备列表，每项包含 device_id 和 camera_url
        
    Returns:
        dict: {added: int, removed: int, errors: list}
    """
    result = {"added": 0, "removed": 0, "errors": []}
    
    try:
        # 获取现有路径
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{MEDIAMTX_API}/v3/paths/list")
            response.raise_for_status()
            data = response.json()
            existing_paths = {item["name"] for item in data.get("items", [])}
        
        # 数据库中的设备 ID 集合
        device_ids = {d["device_id"] for d in devices if d.get("camera_url")}
        
        # 添加缺失的路径
        for device in devices:
            if device.get("camera_url") and device["device_id"] not in existing_paths:
                success = await register_camera_path(
                    device["device_id"], 
                    device["camera_url"]
                )
                if success:
                    result["added"] += 1
                else:
                    result["errors"].append(f"添加失败: {device['device_id']}")
        
        # 可选：删除数据库中不存在的路径（谨慎使用）
        # for path in existing_paths:
        #     if path not in device_ids and path not in ("cam1", "all_others"):
        #         await remove_camera_path(path)
        #         result["removed"] += 1
        
    except Exception as e:
        logger.error(f"[MediaMTX] 同步路径异常: {e}")
        result["errors"].append(str(e))
    
    return result
