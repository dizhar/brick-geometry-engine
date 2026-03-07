"""
FastAPI application entry point for the brick-geometry-engine API.

Run with:
    uvicorn api.main:app --reload

Environment variables (via .env):
    DATABASE_URL   — PostgreSQL connection string
                     e.g. postgresql://user:pass@localhost:5432/brickdb
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routes import assemblies, parts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic migrations in production).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Brick Geometry Engine API",
    description="REST API for storing and querying LEGO assemblies.",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(assemblies.router, prefix="/api/v1")
app.include_router(parts.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
