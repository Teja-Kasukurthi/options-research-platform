import structlog
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.redis import close_redis, get_redis
from app.api.routers import auth, market, analytics, signals, paper, backtest, positions, research
from app.api.websocket.handlers import ws_pnl, ws_position_alerts, ws_signals, ws_ticks

logger = structlog.get_logger()

app = FastAPI(
    title="Options Research Platform",
    version="0.1.0",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-vercel-app.vercel.app"] if settings.is_production else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# REST Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["signals"])
app.include_router(paper.router, prefix="/api/v1/paper", tags=["paper-trading"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])
app.include_router(positions.router, prefix="/api/v1/positions", tags=["positions"])
app.include_router(research.router, prefix="/api/v1/research", tags=["research"])

# WebSocket endpoints
@app.websocket("/ws/market/ticks/{symbol}")
async def websocket_ticks(ws: WebSocket, symbol: str) -> None:
    await ws_ticks(ws, symbol)


@app.websocket("/ws/paper/pnl")
async def websocket_pnl(ws: WebSocket) -> None:
    await ws_pnl(ws)


@app.websocket("/ws/positions/alerts")
async def websocket_alerts(ws: WebSocket) -> None:
    await ws_position_alerts(ws)


@app.websocket("/ws/signals/new")
async def websocket_signals(ws: WebSocket) -> None:
    await ws_signals(ws)


@app.on_event("startup")
async def startup() -> None:
    await get_redis()
    logger.info("startup_complete", env=settings.app_env)


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_redis()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
