"""
@file_name: settings.py
@author: NetMind.AI
@date: 2026-02-09
@description: Unified configuration management

Uses pydantic-settings to centrally manage all environment variables, replacing
scattered load_dotenv() + os.getenv() calls throughout the codebase.

Usage:
    from xyz_agent_context.settings import settings

    api_key = settings.google_api_key
    db_host = settings.db_host
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root directory (3 levels up from src/xyz_agent_context/settings.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application global configuration, automatically loaded from .env file and environment variables"""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ===== LLM API Keys =====
    openai_api_key: str = ""
    google_api_key: str = ""

    # ===== Database =====
    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = ""
    db_user: str = ""
    db_password: str = ""

    # SSL (optional)
    db_ssl_ca: Optional[str] = None
    db_ssl_cert: Optional[str] = None
    db_ssl_key: Optional[str] = None
    db_ssl_verify_cert: Optional[str] = None

    # ===== Workspace =====
    base_working_path: str = "./agent_workspace"

    # ===== Embedding =====
    openai_embedding_model: str = "text-embedding-3-small"

    # ===== Export Paths =====
    narrative_markdown_path: str = "./data/narratives"
    trajectory_path: str = "./data/trajectories"

    # ===== Auth =====
    admin_secret_key: str = ""


settings = Settings()

# Sync key variables to os.environ for direct use by third-party SDKs (e.g., OpenAI Agents SDK).
# pydantic-settings only loads values into the Settings object and does not automatically write to os.environ.
_ENV_SYNC = {
    "OPENAI_API_KEY": settings.openai_api_key,
    "GOOGLE_API_KEY": settings.google_api_key,
}
for _key, _val in _ENV_SYNC.items():
    if _val and not os.environ.get(_key):
        os.environ[_key] = _val
