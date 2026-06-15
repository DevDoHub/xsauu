"""FastAPI 应用入口.

使用 lifespan 管理启动/关闭事件：初始化数据库、启动 SocketIO 兼容层、注册异常处理。
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import socketio as _socketio_lib
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.db import init_db, seed_data
from app.exceptions import AppException
from app.logger import logger, setup_logging
from app.settings import settings


def custom_generate_unique_id(route: APIRoute) -> str:
    """生成 OpenAPI 路由唯一标识，供前端代码生成工具使用."""
    return f"{route.tags[0]}-{route.name}" if route.tags else route.name


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理."""
    # ── 基础设施初始化 ──
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info(f"🚀 {settings.PROJECT_NAME} v{settings.VERSION} 启动中...")

    init_db()
    seed_data()

    # 初始化系统默认配置
    from sqlmodel import Session as _Session

    from app.db import engine as _engine
    from app.services.system_config import SystemConfigService
    with _Session(_engine) as _session:
        inserted = SystemConfigService(_session).init_defaults()
        if inserted:
            logger.info(f"✅ 初始化 {inserted} 个默认配置项")
    logger.info("✅ 数据库初始化完成")

    # ── 通信层启动 ──
    # 当前阶段：边缘端（tripod_pro / utree_pro）仍使用 SocketIO 协议接入（见
    # docs/features/SOCKETIO_COMPAT.md）。MQTT 默认关闭，待边缘端迁移到 MQTT
    # 后将 settings.MQTT_ENABLED 设为 True 即可启用订阅器。
    if settings.MQTT_ENABLED:
        from app.mqtt.handler import register_mqtt_handlers
        from app.mqtt.subscriber import mqtt_subscriber

        register_mqtt_handlers()
        mqtt_subscriber.start()
        logger.info("✅ MQTT 订阅器已启动")
    else:
        logger.info("⏭️  MQTT 已禁用（边缘端走 SocketIO 兼容层）")

    # ── 后台任务 ──
    bg_tasks: list[asyncio.Task] = []
    bg_tasks.append(asyncio.create_task(_check_device_offline(_engine, _Session)))

    # ── 开发环境专用：气体数据模拟 ──
    # 边缘端真实气体数据接入后可删除本块。该模拟仅在 ENVIRONMENT == "local"
    # 时启用，不暴露 HTTP 端点（前端无需启停）。
    if settings.ENVIRONMENT == "local":
        from app.api.routers.detections import start_gas_simulation
        await start_gas_simulation()

    # ── 启动摘要 ──
    sio_status = "已启用（兼容层）" if settings.SOCKETIO_ENABLED else "已禁用"
    mqtt_status = "已启用" if settings.MQTT_ENABLED else "已禁用"
    logger.info(
        f"\n"
        f"  ┌─────────────────────────────────────────┐\n"
        f"  │  ✅ 服务就绪                              │\n"
        f"  │  环境: {settings.ENVIRONMENT:<33s}│\n"
        f"  │  MQTT: {mqtt_status:<33s}│\n"
        f"  │  SocketIO: {sio_status:<29s}│\n"
        f"  └─────────────────────────────────────────┘"
    )

    yield

    # ── 关闭 ──
    if settings.ENVIRONMENT == "local":
        from app.api.routers.detections import stop_gas_simulation
        await stop_gas_simulation()
    for task in bg_tasks:
        task.cancel()
    if settings.MQTT_ENABLED:
        from app.mqtt.subscriber import mqtt_subscriber
        mqtt_subscriber.stop()
    logger.info("👋 服务已停止")


async def _check_device_offline(engine, session_cls):
    """后台协程：定期扫描心跳超时的设备，标记为离线.

    业务逻辑下沉到 ``DeviceService.mark_timeout_devices_offline``。
    本协程仅负责调度 + 读配置。
    """
    from app.services.device import DeviceService
    from app.services.system_config import SystemConfigService

    while True:
        try:
            with session_cls(engine) as session:
                timeout = SystemConfigService(session).get_typed_value(
                    "device_offline_timeout", default=30,
                )
                DeviceService(session).mark_timeout_devices_offline(timeout)
        except Exception as e:
            logger.error(f"设备离线检测异常: {e}")
        await asyncio.sleep(10)


def create_app() -> FastAPI:
    """应用工厂."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
        generate_unique_id_function=custom_generate_unique_id,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局异常处理
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": "请求参数验证失败", "errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # 注册路由
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # 兼容旧端点: /api/push → /api/detections/push
    # poc-sau/edge/main.py 使用的是旧端点 /api/push
    from app.schemas.detection import DetectionPushDTO
    
    @app.post("/api/push", tags=["兼容"], summary="兼容旧端点 - 边缘端推送检测框数据")
    async def legacy_push(payload: DetectionPushDTO):
        """兼容 poc-sau/edge/main.py 的旧端点 /api/push."""
        from app.services.detection import detection_service
        return await detection_service.receive_push(payload)

    # 健康检查
    @app.get("/health", tags=["系统"])
    async def health():
        return {"status": "ok", "version": settings.VERSION}

    # --- 报警截图静态文件服务 ---
    alarm_images_dir = Path(__file__).parent.parent / "data" / "alarm_images"
    alarm_images_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/alarm_images", StaticFiles(directory=alarm_images_dir), name="alarm-images")

    # --- 前端静态文件服务 ---
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        # 静态资源（js/css/图片）
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="static-assets")

        # SPA catch-all：非 /api 和非 /health 的 GET 请求都返回 index.html
        @app.get("/{path:path}", tags=["前端"])
        async def serve_spa(path: str):
            # 尝试返回具体文件（如 favicon.ico）
            file_path = frontend_dist / path
            if path and file_path.is_file():
                return FileResponse(file_path)
            # 否则返回 index.html（SPA 路由）
            return FileResponse(frontend_dist / "index.html")
    else:
        logger.debug(f"前端构建目录不存在: {frontend_dist}，跳过静态文件服务（开发环境用 npm run dev）")

    return app


# ── 组装最终 ASGI 应用 ──
# 注意：不能将内部 FastAPI 实例暴露为模块级变量，
# 否则 `fastapi dev` 会错误地选择它（而非 SocketIO 包装后的版本）。
# 请使用 `uvicorn app.main:app --reload` 或 `make dev` 启动开发服务器。

def _build_final_app():
    """构建最终 ASGI 应用（FastAPI + 可选 SocketIO 兼容层）."""
    _fastapi = create_app()
    if settings.SOCKETIO_ENABLED:
        from app.socketio_compat import sio
        return _socketio_lib.ASGIApp(sio, other_asgi_app=_fastapi)
    return _fastapi


app = _build_final_app()
