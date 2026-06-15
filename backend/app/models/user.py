"""SQLModel 数据模型 - 用户."""

import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """用户表."""

    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True, description="用户名")
    hashed_password: str = Field(max_length=255, description="密码哈希")
    nickname: str = Field(default="", max_length=100, description="昵称")
    role: str = Field(default="operator", max_length=20, description="角色: admin/operator")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="创建时间",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="更新时间",
    )
