from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError

from .config import settings
from .db import init_db
from .errors import error_body
from .ratelimit import limiter, rate_limit_handler
from .routers import auth, catalog, groups, nights, public, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Pokerdex API", lifespan=lifespan)

# slowapi reads the limiter off app.state; the @limiter.limit decorators do the rest.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# In production everything is same-origin behind Caddy, so no CORS is needed.
# In dev the SvelteKit server (5173) talks to the API (8000), so allow it.
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """FK/unique violations are conflicts, not server faults — never leak a raw 500."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_body("integrity_conflict", "Operação conflita com dados existentes."),
    )


app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(catalog.router)
app.include_router(nights.router)
app.include_router(stats.router)
app.include_router(public.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
