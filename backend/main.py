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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# Configure CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
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


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Agent Context API",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
