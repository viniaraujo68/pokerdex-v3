from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .routers import auth, catalog, groups, nights, public, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Pokerdex API", lifespan=lifespan)

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

app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(catalog.router)
app.include_router(nights.router)
app.include_router(stats.router)
app.include_router(public.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
