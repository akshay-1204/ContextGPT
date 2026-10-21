"""ContextGPT FastAPI Main Application Entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.db.base import Base
from backend.app.db.session import engine
# Import all models to ensure metadata registration
import backend.app.db.models  # noqa: F401

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.users import router as users_router
from backend.app.api.routes.sources import router as sources_router
from backend.app.api.routes.summaries import router as summaries_router
from backend.app.api.routes.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' environment...")

    # Automatically initialize tables if not already created
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schemas initialized.")
    except Exception as e:
        logger.warning(f"Database schema auto-creation notice: {e}")

    yield

    # Shutdown tasks
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title="ContextGPT API",
    description="Multi-source AI summarization and question-answering platform backend API.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Health Probes
app.include_router(health_router)

# Register Versioned API Routes (/api/v1)
API_V1_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_V1_PREFIX)
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(users_router, prefix=API_V1_PREFIX)
app.include_router(sources_router, prefix=API_V1_PREFIX)
app.include_router(summaries_router, prefix=API_V1_PREFIX)
app.include_router(chat_router, prefix=API_V1_PREFIX)


@app.get("/", tags=["Root"])
def root_endpoint():
    return {
        "name": settings.APP_NAME,
        "tagline": "Understand more. Ask anything.",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
