import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

KEY = "senem:current_slide"

def set_current_slide(slide_index: int):
    try:
        v = max(0, int(slide_index))
    except Exception:
        v = 0
    _r.set(KEY, v)

def get_current_slide(default: int = 0) -> int:
    v = _r.get(KEY)
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default