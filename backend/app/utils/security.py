"""安全工具模块.

JWT token 生成/验证、密码哈希、用户认证依赖。
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
import bcrypt

from app.settings import settings


def hash_password(password: str) -> str:
    """对密码进行哈希."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """生成 JWT access token.

    Args:
        data: 要编码的数据，通常包含 {"sub": user_id}
        expires_delta: 过期时间增量，默认使用配置值
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """解码 JWT token.

    Returns:
        解码后的 payload 字典，失败返回 None
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


async def _get_current_user_id(
    authorization: str = Header(..., description="Bearer token"),
) -> int:
    """从 JWT token 中解析当前用户 ID."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证格式")
    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token 已过期或无效")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token 中缺少用户信息")
    return int(user_id)


# 简化写法，路由函数直接用: user_id: UserIdDep
UserIdDep = Annotated[int, Depends(_get_current_user_id)]
