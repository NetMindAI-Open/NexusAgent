"""
@file_name: timezone.py
@author: NetMind.AI
@date: 2026-01-20
@description: Timezone utility module

Provides unified timezone handling functions to ensure:
- Internal storage: all times use UTC
- Display/LLM: convert to user timezone

Core functions:
- utc_now(): Get UTC time (replaces all datetime.now() calls)
- to_user_timezone(dt, tz): UTC -> user timezone
- format_for_api(dt): Format as API ISO 8601 UTC format
- format_for_llm(dt, tz): Format for LLM prompts
- is_valid_timezone(tz): Validate timezone string
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from loguru import logger


# ===== Default Timezone =====

DEFAULT_TIMEZONE = "UTC"


# ===== Core Time Functions =====

def utc_now() -> datetime:
    """
    Get the current UTC time (with timezone info)

    Used to replace all datetime.now() calls, ensuring stored times are unified as UTC

    Returns:
        A datetime object with UTC timezone info
    """
    return datetime.now(timezone.utc)


def to_user_timezone(dt: Optional[datetime], user_tz: str = DEFAULT_TIMEZONE) -> Optional[datetime]:
    """
    Convert UTC time to user timezone

    Args:
        dt: UTC datetime object (can be naive or aware)
        user_tz: User timezone string (IANA format, e.g., 'Asia/Shanghai')

    Returns:
        Converted datetime object (in user timezone), or None if input is None
    """
    if dt is None:
        return None

    try:
        # If naive datetime, assume it is UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Convert to user timezone
        target_tz = ZoneInfo(user_tz)
        return dt.astimezone(target_tz)
    except Exception as e:
        logger.warning(f"Timezone conversion failed (to_user_timezone): {e}, returning original time")
        return dt


# ===== Formatting Functions =====

def format_for_api(dt: Optional[datetime]) -> Optional[str]:
    """
    Format as ISO 8601 UTC format for API responses

    Ensures that frontend JavaScript's new Date() correctly recognizes it as UTC time

    Format: YYYY-MM-DDTHH:MM:SSZ

    Args:
        dt: datetime object (UTC or naive; naive will be assumed to be UTC)

    Returns:
        ISO 8601 format string (with Z suffix), e.g., "2025-01-15T14:30:00Z"
        Returns None if input is None
    """
    if dt is None:
        return None

    try:
        # If naive datetime, assume it is UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Convert to UTC (if not already UTC)
        utc_dt = dt.astimezone(timezone.utc)

        # Return ISO 8601 format with Z suffix indicating UTC
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as e:
        logger.warning(f"Time formatting failed (format_for_api): {e}")
        return str(dt) if dt else None


def format_for_llm(dt: Optional[datetime], user_tz: str = DEFAULT_TIMEZONE) -> str:
    """
    Format as LLM-friendly prompt format

    Format: YYYY/M/D AM/PM H:MM (timezone)

    Args:
        dt: datetime object (UTC or with timezone info)
        user_tz: User timezone string

    Returns:
        Formatted time string, e.g., "2025/1/15 PM 2:30 (Asia/Shanghai)"
    """
    if dt is None:
        return "Time unknown"

    try:
        # Convert to user timezone
        local_dt = to_user_timezone(dt, user_tz)
        if local_dt is None:
            return "Time unknown"

        # Format
        year = local_dt.year
        month = local_dt.month
        day = local_dt.day
        hour = local_dt.hour
        minute = local_dt.minute

        # AM/PM
        if hour < 12:
            period = "AM"
            display_hour = hour if hour > 0 else 12
        else:
            period = "PM"
            display_hour = hour - 12 if hour > 12 else 12

        return f"{year}/{month}/{day} {period} {display_hour}:{minute:02d} ({user_tz})"
    except Exception as e:
        logger.warning(f"Time formatting failed (format_for_llm): {e}")
        return str(dt)


# ===== Timezone Validation =====

def is_valid_timezone(tz_str: str) -> bool:
    """
    Validate whether a timezone string is valid

    Args:
        tz_str: Timezone string (IANA format)

    Returns:
        Whether it is a valid timezone string
    """
    try:
        ZoneInfo(tz_str)
        return True
    except Exception:
        return False


