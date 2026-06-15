"""应用配置模块.

使用 pydantic-settings 从环境变量或 .env 文件加载配置。
"""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # --- 基本信息 ---
    PROJECT_NAME: str = "核工业安全监控平台"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = False

    # --- API ---
    API_V1_PREFIX: str = "/api"

    # --- 数据库 (SQLite) ---
    DATABASE_URL: str = "sqlite:///./data/xsau.db"

    # --- JWT 认证 ---
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时
    ALGORITHM: str = "HS256"

    # --- MQTT ---
    # MQTT_ENABLED: 当前阶段边缘端仍使用 SocketIO 协议接入（见 docs/features/SOCKETIO_COMPAT.md），
    # 故默认关闭。未来逐台迁移到 MQTT 后再设为 True。
    MQTT_ENABLED: bool = False
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_CLIENT_ID: str = "xsau-server"
    MQTT_TOPIC_ALARM: str = "xsau/edge/+/alarm"
    MQTT_TOPIC_TELEMETRY: str = "xsau/edge/+/telemetry"
    MQTT_TOPIC_HEARTBEAT: str = "xsau/edge/+/heartbeat"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- SocketIO 兼容层（旧 Jetson 边缘端） ---
    SOCKETIO_ENABLED: bool = True

    # --- 日志 ---
    LOG_LEVEL: str = "INFO"

    # --- 媒体服务器 ---
    MEDIAMTX_API_URL: str = "http://localhost:9997"
    DECODER_HARDWARE_ACCEL: Literal["cpu", "cuda", "vaapi"] = "cpu"


settings = Settings()
