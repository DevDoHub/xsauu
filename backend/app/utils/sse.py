"""SSE (Server-Sent Events) 通用发布订阅工具.

封装 detection / device-status / gas / alarm 等共享的 SSE 模式：
- 维护订阅者 Queue 列表
- 非阻塞广播（满队列剔除慢客户端）
- 异步锁保护订阅者列表
- 流生成器：先发送快照、再消费实时事件、定期心跳
- 连接断开时自动清理订阅

每个发布器有唯一 name（仅用于日志）。

用法：
    from app.utils.sse import SsePublisher

    detection_pub = SsePublisher(name="detection")

    # 业务侧：广播
    await detection_pub.publish({"device": "cam1", "boxes": [...]})

    # 路由侧：建立 SSE 流
    @router.get("/events")
    async def stream(request: Request):
        return StreamingResponse(
            detection_pub.stream(request.is_disconnected, snapshot=lambda: [...]),
            media_type="text/event-stream",
        )
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from app.logger import logger

# SSE 心跳间隔（秒）：客户端没有新数据时也定期发一行注释，防中间代理断连
_HEARTBEAT_INTERVAL = 25
# 每个订阅者 Queue 容量：超过则视为慢客户端剔除
_QUEUE_MAXSIZE = 60


def _format_sse(data: Any) -> str:
    """将任意可 JSON 序列化对象格式化成 SSE 帧."""
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


class SsePublisher:
    """SSE 发布订阅器（异步安全）.

    Attributes:
        name: 发布器名称，仅用于日志区分（如 "detection"、"alarm"）。
    """

    def __init__(self, name: str = "sse") -> None:
        self.name = name
        self._subscribers: list[asyncio.Queue[str]] = []
        self._lock = asyncio.Lock()

    async def publish(self, payload: Any) -> None:
        """向所有订阅者推送一条事件，慢客户端会被剔除.

        Args:
            payload: 任意可 JSON 序列化对象。
        """
        chunk = _format_sse(payload)
        async with self._lock:
            dead: list[asyncio.Queue[str]] = []
            for q in self._subscribers:
                try:
                    q.put_nowait(chunk)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                self._subscribers.remove(q)
            if dead:
                logger.debug(f"[{self.name}] 剔除 {len(dead)} 个慢订阅者")

    async def stream(
        self,
        is_disconnected: Callable[[], Awaitable[bool]],
        snapshot: Callable[[], list[Any]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """生成 SSE 流：先发送快照，再消费实时事件.

        Args:
            is_disconnected: 异步函数，返回客户端是否断开（通常是
                ``request.is_disconnected``）。
            snapshot: 可选，生成"首次快照"的可调用对象（同步），通常
                返回当前所有最新数据。

        Yields:
            SSE 帧字符串。
        """
        # 1. 推送首次快照
        if snapshot is not None:
            try:
                for item in snapshot():
                    yield _format_sse(item)
            except Exception as e:
                logger.warning(f"[{self.name}] 生成快照异常: {e}")

        # 2. 注册订阅者
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        async with self._lock:
            self._subscribers.append(q)

        try:
            while True:
                if await is_disconnected():
                    break
                try:
                    chunk = await asyncio.wait_for(q.get(), timeout=_HEARTBEAT_INTERVAL)
                    yield chunk
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except Exception:
            logger.debug(f"[{self.name}] SSE 客户端断开")
        finally:
            async with self._lock:
                if q in self._subscribers:
                    self._subscribers.remove(q)

    @property
    def subscriber_count(self) -> int:
        """当前订阅者数（不加锁，仅用于监控/调试）."""
        return len(self._subscribers)
