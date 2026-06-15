"""Pydantic Schema - 遥测数据响应."""

from pydantic import BaseModel, Field
from app.schemas.common import PaginatedResponse


class TelemetryRespVO(BaseModel):
    """遥测数据响应."""
    id: int
    device_id: str
    sensor_type: str
    value: float
    unit: str
    is_overlimit: bool
    threshold: float | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class TelemetryListRespVO(PaginatedResponse[TelemetryRespVO]):
    """遥测数据列表分页响应."""
    pass
