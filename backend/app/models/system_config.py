"""SQLModel 数据模型 - 系统配置."""

import datetime

from sqlmodel import Field, SQLModel


class SystemConfig(SQLModel, table=True):
    """系统配置表，存储运行时可修改的系统级参数.

    采用 key-value 结构，支持类型标注和分组。
    """

    __tablename__ = "system_config"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(
        max_length=100,
        unique=True,
        index=True,
        description="配置键名，如 decoder_hardware_accel",
    )
    value: str = Field(default="", description="配置值（字符串形式）")
    value_type: str = Field(
        default="str",
        max_length=20,
        description="值类型: str/int/float/bool/json",
    )
    group: str = Field(
        default="general",
        max_length=50,
        description="配置分组: general/decoder/timeout/alarm/display",
    )
    label: str = Field(default="", max_length=200, description="配置项中文名称")
    description: str = Field(default="", max_length=500, description="配置项说明")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="创建时间",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="最后更新时间",
    )
