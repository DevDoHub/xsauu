"""日志配置模块.

使用 loguru 统一管理日志，支持控制台彩色输出和文件轮转。
"""

import sys
import logging
from pathlib import Path
from loguru import logger

# --- 日志路径 ---
LOG_PATH = Path("logs")
LOG_PATH.mkdir(parents=True, exist_ok=True)

# --- 轮转配置 ---
ROTATION_TIME = "00:00"
ROTATION_SIZE = "50 MB"
RETENTION_TIME = "14 days"

# --- 格式定义 ---
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} | {message}"
)


class InterceptHandler(logging.Handler):
    """拦截标准 logging，重定向到 loguru."""

    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level: str = "INFO") -> None:
    """初始化日志系统.

    Args:
        log_level: 日志级别，如 "INFO", "DEBUG"
    """
    # 移除 loguru 默认 handler
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stderr,
        format=CONSOLE_FORMAT,
        level=log_level,
        colorize=True,
    )

    # 文件输出 - 一般日志
    logger.add(
        LOG_PATH / "xsau_{time:YYYY-MM-DD}.log",
        format=FILE_FORMAT,
        level="DEBUG",
        rotation=ROTATION_TIME,
        retention=RETENTION_TIME,
        encoding="utf-8",
    )

    # 文件输出 - 错误日志
    logger.add(
        LOG_PATH / "error_{time:YYYY-MM-DD}.log",
        format=FILE_FORMAT,
        level="ERROR",
        rotation=ROTATION_SIZE,
        retention=RETENTION_TIME,
        encoding="utf-8",
    )

    # 拦截 uvicorn 等标准库日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    logger.info(f"日志系统初始化完成，级别: {log_level}")
