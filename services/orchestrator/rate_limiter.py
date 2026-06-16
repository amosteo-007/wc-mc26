"""Simple Redis token-bucket rate limiter."""
import os
import time
from database import get_redis


RATE_LIMITS = {
    'simulations': {'burst': 10, 'rate': 0.1},     # 10 burst, 1 per 10 sec refill
    'matches': {'burst': 60, 'rate': 1.0},           # 60 burst, 1 per sec refill
    'default': {'burst': 30, 'rate': 0.5},            # 30 burst, 1 per 2 sec
}

CONCURRENT_SIM_CAP = int(os.getenv('MAX_CONCURRENT_SIMS', '5'))


def check_rate_limit(client_ip: str, endpoint: str = 'default') -> bool:
    """Return True if request is allowed, False if rate limited.

    Uses a simple token-bucket: tokens refill at `rate` per second,
    up to `burst` max. Each request consumes 1 token.
    """
    r = get_redis()
    limits = RATE_LIMITS.get(endpoint, RATE_LIMITS['default'])
    key = f"rate:{client_ip}:{endpoint}"

    now = time.time()

    # Use Lua-style atomic check-and-decrement via pipelining
    # Simple approach: get current tokens, compute refill, check
    pipe = r.pipeline()
    pipe.get(key)
    pipe.get(f"{key}:ts")
    tokens_str, ts_str = pipe.execute()

    tokens = float(tokens_str) if tokens_str else float(limits['burst'])
    last_ts = float(ts_str) if ts_str else now

    # Refill
    elapsed = now - last_ts
    tokens = min(limits['burst'], tokens + elapsed * limits['rate'])

    if tokens < 1.0:
        return False

    tokens -= 1.0
    pipe = r.pipeline()
    pipe.set(key, tokens, ex=300)  # 5 min TTL
    pipe.set(f"{key}:ts", now, ex=300)
    pipe.execute()

    return True


def check_concurrent_sims() -> bool:
    """Return True if a new simulation can be started."""
    r = get_redis()
    keys = r.keys("job:*")
    running = 0
    for k in keys:
        status = r.hget(k, 'status')
        if status and status not in ('done', 'failed', 'unknown'):
            running += 1
    return running < CONCURRENT_SIM_CAP
