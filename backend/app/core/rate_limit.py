"""登录与注册接口的频率限制（进程内实现，适用于本地单实例部署）。

说明：多实例或公网部署时应替换为基于共享存储（如 Redis）的限流方案。
"""

import threading
import time
from collections import deque

from app.core.errors import BusinessError

_lock = threading.Lock()
_buckets: dict[str, deque[float]] = {}


def enforce_rate_limit(scope: str, identity: str, limit: int, window_seconds: int) -> None:
    """按作用域与来源限制请求频率，超出限制时抛出 429 中文错误。"""

    key = f"{scope}:{identity}"
    now = time.monotonic()

    with _lock:
        bucket = _buckets.setdefault(key, deque())
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise BusinessError(429, "操作过于频繁，请稍后再试。")
        bucket.append(now)


def reset_rate_limits() -> None:
    """清空频率限制记录（测试与本地调试使用）。"""

    with _lock:
        _buckets.clear()
