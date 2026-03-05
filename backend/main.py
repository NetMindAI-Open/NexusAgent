"""
@file_name: main.py
@author: NetMind.AI
@date: 2025-11-28
@description: FastAPI application entry point

Provides WebSocket streaming for agent runtime and REST APIs for
jobs, inbox, agents, and awareness management.

Usage:
    uvicorn backend.main:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from loguru import logger

from xyz_agent_context.utils.db_factory import get_db_client, close_db_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Handles startup and shutdown events:
    - Startup: Initialize database connection pool
    - Shutdown: Close database connections
    """
    # Startup
    logger.info("Starting FastAPI application...")
    logger.info("Initializing database connection pool...")
    await get_db_client()
    logger.info("Database connection pool initialized")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")
    await close_db_client()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Agent Context API",
    description="WebSocket streaming and REST APIs for Agent Context runtime",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://localhost:8000",  # Backend serves frontend
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import and include routers
from backend.routes.websocket import router as websocket_router
from backend.routes.agents import router as agents_router
from backend.routes.jobs import router as jobs_router
from backend.routes.inbox import router as inbox_router
from backend.routes.agent_inbox import router as agent_inbox_router
from backend.routes.auth import router as auth_router
from backend.routes.skills import router as skills_router

app.include_router(websocket_router, tags=["WebSocket"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(inbox_router, prefix="/api/inbox", tags=["Inbox"])
app.include_router(agent_inbox_router, prefix="/api/agent-inbox", tags=["Agent Inbox"])
app.include_router(skills_router, prefix="/api/skills", tags=["Skills"])


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
    }


# ─── 前端静态文件 & SPA fallback ──────────────────────────
# 在所有 API 路由之后挂载，确保 /api/* 和 /ws/* 优先匹配

# 前端构建产物目录（支持本地开发和打包后两种路径）
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").exists():
    logger.info(f"Serving frontend from {_FRONTEND_DIST}")

    # 挂载静态资源（JS/CSS/图片等）
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(request: Request, full_path: str):
        """
        SPA fallback：非 API/WS 请求一律返回 index.html，
        由前端路由处理页面导航。
        """
        # 尝试返回静态文件（favicon.ico 等根目录文件）
        file_path = _FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        # 其余全部返回 index.html
        return FileResponse(_FRONTEND_DIST / "index.html")
else:
    logger.info("Frontend dist not found, API-only mode")

    @app.get("/")
    async def root():
        """Health check endpoint (no frontend)"""
        return {
            "status": "ok",
            "service": "Agent Context API",
            "version": "1.0.0",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
