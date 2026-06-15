"""SQLModel 数据模型 - 气体/传感器遥测."""

import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Telemetry(SQLModel, table=True):
    """遥测数据表，记录气体、温度等传感器数据."""

    __tablename__ = "telemetry"

    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: str = Field(max_length=64, index=True, description="来源设备 ID")
    sensor_type: str = Field(
        max_length=50,
        description="传感器类型，直接使用边缘端原始字段名，如 C3H8/CO2/O2/TEMP/RH/...",
    )
    value: float = Field(description="测量值")
    unit: str = Field(default="", max_length=20, description="单位，如 ppm、℃")
    is_overlimit: bool = Field(default=False, description="是否超限")
    threshold: Optional[float] = Field(default=None, description="超限阈值")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="采集时间",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="最后更新时间",
    )
