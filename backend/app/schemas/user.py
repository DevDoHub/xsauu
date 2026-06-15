"""Pydantic Schema - 用户相关请求/响应."""

from datetime import datetime

from pydantic import BaseModel, Field


# ===== 请求 DTO =====

class UserCreateDTO(BaseModel):
    """创建用户."""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    nickname: str = Field(default="", max_length=100, description="昵称")
    role: str = Field(default="operator", description="角色: admin/operator")


class UserUpdateDTO(BaseModel):
    """更新用户."""
    nickname: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class LoginDTO(BaseModel):
    """登录请求."""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


# ===== 响应 VO =====

class UserRespVO(BaseModel):
    """用户信息响应."""
    id: int
    username: str
    nickname: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenRespVO(BaseModel):
    """登录 token 响应."""
    access_token: str
    token_type: str = "bearer"
    user: UserRespVO
