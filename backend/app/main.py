from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.database.base import engine, Base
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    # In production, use Alembic migrations instead
    # Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass


# Create FastAPI app
app = FastAPI(
    title="StatArb N50 API",
    description="Statistical arbitrage research platform for Nifty 50 equities",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "StatArb N50 API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
    }


# Include API routers
from app.api import pairs, signals, backtests, research, risk, system, websocket

app.include_router(pairs.router, prefix="/api/pairs", tags=["pairs"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(backtests.router, prefix="/api/backtests", tags=["backtests"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(risk.router, prefix="/api/risk", tags=["risk"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(websocket.router, prefix="/api/ws", tags=["websocket"])


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers if not settings.api_reload else 1,
    )
