"""自定义异常模块.

统一的异常体系，FastAPI 会自动捕获并返回对应的 JSON 响应。
"""

from typing import Any
from fastapi import HTTPException, status


class AppException(HTTPException):
    """应用基础异常类."""

    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(AppException):
    """资源未找到."""

    def __init__(self, detail: str = "资源不存在"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestException(AppException):
    """请求参数错误."""

    def __init__(self, detail: str = "请求参数错误"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(AppException):
    """未认证."""

    def __init__(self, detail: str = "未认证"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(AppException):
    """无权限."""

    def __init__(self, detail: str = "无权限访问"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
