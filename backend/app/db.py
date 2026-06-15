"""数据库配置模块.

使用 SQLModel（SQLAlchemy + Pydantic 一体化）+ SQLite WAL 模式。
"""

from collections.abc import Generator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.logger import logger
from app.settings import settings

# 确保数据目录存在
db_path = settings.DATABASE_URL.replace("sqlite:///", "")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# SQLite 连接参数：多线程安全
connect_args = {"check_same_thread": False}
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """每次新连接时设置 SQLite PRAGMA：WAL 模式 + busy_timeout."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def init_db() -> None:
    """创建所有表（开发用，生产用 alembic）."""
    SQLModel.metadata.create_all(engine)
    _migrate_device_table()
    _migrate_alarm_table()


def _migrate_device_table() -> None:
    """为 device 表添加新增字段（幂等，重复执行无副作用）."""
    from sqlalchemy import text

    with engine.begin() as conn:
        # 检查 mediamtx_path 列是否存在
        result = conn.execute(text("PRAGMA table_info(device)"))
        columns = {row[1] for row in result}
        if "mediamtx_path" not in columns:
            conn.execute(text("ALTER TABLE device ADD COLUMN mediamtx_path VARCHAR(100) DEFAULT ''"))
            # 已有设备默认 mediamtx_path = device_id
            conn.execute(text("UPDATE device SET mediamtx_path = device_id WHERE mediamtx_path = '' OR mediamtx_path IS NULL"))
            logger.info("✅ device 表已添加 mediamtx_path 列")
        if "camera_rotation" not in columns:
            conn.execute(text("ALTER TABLE device ADD COLUMN camera_rotation INTEGER DEFAULT 0"))
            logger.info("✅ device 表已添加 camera_rotation 列")
        if "work_type" not in columns:
            conn.execute(text("ALTER TABLE device ADD COLUMN work_type VARCHAR(50) DEFAULT ''"))
            logger.info("✅ device 表已添加 work_type 列")
        if "confined_space" not in columns:
            conn.execute(text("ALTER TABLE device ADD COLUMN confined_space VARCHAR(10) DEFAULT ''"))
            logger.info("✅ device 表已添加 confined_space 列")
        if "work_start_time" not in columns:
            conn.execute(text("ALTER TABLE device ADD COLUMN work_start_time VARCHAR(30) DEFAULT ''"))
            logger.info("✅ device 表已添加 work_start_time 列")
        if "work_end_time" not in columns:
            conn.execute(text("ALTER TABLE device ADD COLUMN work_end_time VARCHAR(30) DEFAULT ''"))
            logger.info("✅ device 表已添加 work_end_time 列")
        if "work_status" not in columns:
            conn.execute(text("ALTER TABLE device ADD COLUMN work_status VARCHAR(20) DEFAULT ''"))
            logger.info("✅ device 表已添加 work_status 列")


def _migrate_alarm_table() -> None:
    """为 alarm 表补齐 snapshot_* 列（幂等）.

    Alarm 模型新增了 14 个 snapshot_* 字段用于冻结告警瞬间的设备/作业元信息，
    避免历史告警因 Device 表后续修改被污染。早期数据库未含这些列，
    新告警写入会失败（OperationalError: no such column）。
    """
    from sqlalchemy import text

    # 列名 → SQL 类型/默认值
    snapshot_columns: list[tuple[str, str]] = [
        ("snapshot_device_name", "VARCHAR(100) DEFAULT ''"),
        ("snapshot_device_manager", "VARCHAR(50) DEFAULT ''"),
        ("snapshot_area_manager", "VARCHAR(50) DEFAULT ''"),
        ("snapshot_area_manager_phone", "VARCHAR(20) DEFAULT ''"),
        ("snapshot_ip_address", "VARCHAR(50) DEFAULT ''"),
        ("snapshot_workshop", "VARCHAR(100) DEFAULT ''"),
        ("snapshot_safety_permit_no", "VARCHAR(50) DEFAULT ''"),
        ("snapshot_work_content", "VARCHAR(200) DEFAULT ''"),
        ("snapshot_work_level", "VARCHAR(20) DEFAULT ''"),
        ("snapshot_work_type", "VARCHAR(50) DEFAULT ''"),
        ("snapshot_confined_space", "VARCHAR(10) DEFAULT ''"),
        ("snapshot_work_start_time", "VARCHAR(30) DEFAULT ''"),
        ("snapshot_work_end_time", "VARCHAR(30) DEFAULT ''"),
        ("snapshot_work_status", "VARCHAR(20) DEFAULT ''"),
    ]

    with engine.begin() as conn:
        result = conn.execute(text("PRAGMA table_info(alarm)"))
        existing = {row[1] for row in result}
        added = 0
        for col, ddl in snapshot_columns:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE alarm ADD COLUMN {col} {ddl}"))
                added += 1
        if added:
            logger.info(f"✅ alarm 表已补齐 {added} 个 snapshot_* 列")


def seed_data() -> None:
    """初始化种子数据：默认管理员 + 开发环境演示设备."""
    from app.models.user import User
    from app.utils.security import hash_password

    with Session(engine) as session:
        # --- 管理员账户（所有环境） ---
        if not session.exec(select(User).limit(1)).first():
            admin = User(
                username="admin",
                hashed_password=hash_password("123456"),
                nickname="管理员",
                role="admin",
            )
            session.add(admin)
            logger.info("✅ 已创建默认管理员账户")

        session.commit()


def get_session() -> Generator[Session, None, None]:
    """数据库会话依赖注入."""
    with Session(engine) as session:
        yield session


# 简化写法，路由函数直接用: session: SessionDep
SessionDep = Annotated[Session, Depends(get_session)]
