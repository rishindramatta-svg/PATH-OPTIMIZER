from collections import defaultdict, deque
from time import monotonic

_hits: dict[str, deque[float]] = defaultdict(deque)


def consume_rate_limit(key: str, limit: int, window_seconds: float = 60, now: float | None = None) -> bool:
    """Return True when a request is within the fixed sliding window."""
    from .shared_state import shared_rate_limit

    shared = shared_rate_limit(key, limit, int(window_seconds))
    if shared is not None:
        return shared
    stamp = monotonic() if now is None else now
    hits = _hits[key]
    while hits and hits[0] <= stamp - window_seconds:
        hits.popleft()
    if len(hits) >= limit:
        return False
    hits.append(stamp)
    return True


def reset_rate_limits() -> None:
    _hits.clear()
