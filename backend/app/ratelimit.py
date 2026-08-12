"""Per-IP rate limiting for the endpoints worth protecting: credential endpoints
(brute force / account enumeration) and the unauthenticated public directory (scraping).

Lives in its own module so routers can decorate their handlers without importing main.py.
The limiter keys on the client IP, which is only correct because uvicorn runs with
--proxy-headers --forwarded-allow-ips=* behind the edge proxy (see Dockerfile); otherwise
every request would look like it came from the proxy and share one bucket.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .errors import error_body

# key_style="endpoint": buckets are per (client IP, handler), not per concrete URL. With
# the default "url" style every distinct /api/public/{slug} would get its own 30/min
# allowance, so walking slugs would sidestep the limit entirely.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
    key_style="endpoint",
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_body("rate_limited", "Muitas tentativas. Aguarde um momento e tente novamente."),
        headers={"Retry-After": "60"},
    )


def reset() -> None:
    """Drop all counters. Used by tests; harmless in production."""
    limiter.reset()
