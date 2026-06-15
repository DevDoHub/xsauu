"""Pydantic Schema - 系统配置相关请求/响应."""

import datetime

from pydantic import BaseModel, Field


class SystemConfigRespVO(BaseModel):
    """单个配置项响应."""
    id: int
    key: str
    value: str
    value_type: str
    group: str
    label: str
    description: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class SystemConfigUpdateDTO(BaseModel):
    """更新单个配置项."""
    value: str = Field(..., description="新的配置值")


class SystemConfigBatchUpdateDTO(BaseModel):
    """批量更新配置项."""
    configs: dict[str, str] = Field(
        ...,
        description="配置键值对，如 {\"decoder_hardware_accel\": \"cuda\"}",
    )


class SystemConfigGroupVO(BaseModel):
    """按分组返回的配置."""
    group: str
    items: list[SystemConfigRespVO]
