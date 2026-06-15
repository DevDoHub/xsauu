"""通用响应 Schema.

提供分页、统一响应格式等可复用的基类。
"""

from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应.

    用法::

        class AlarmListRespVO(PaginatedResponse[AlarmRespVO]):
            pass
    """

    total: int
    items: list[T]
    page: int
    page_size: int
