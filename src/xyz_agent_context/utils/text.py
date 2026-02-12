#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General text processing utilities

@file_name: text.py
@author: NetMind.AI
@date: 2025-12-22
@description: Provides general text processing functions such as keyword extraction and text truncation

Features:
1. extract_keywords - Extract keywords from text (supports Chinese and English)
2. truncate_text - Smart text truncation
"""

from __future__ import annotations

import re
from typing import List, Set, Optional


# =============================================================================
# Stop Words
# =============================================================================

# Chinese stop words
CHINESE_STOPWORDS: Set[str] = {
    "的", "了", "是", "在", "我", "你", "他", "她", "它", "们",
    "这", "那", "有", "和", "就", "不", "人", "都", "一", "上",
    "也", "很", "到", "说", "要", "去", "吗", "会", "着", "没", "看",
    "好", "自己", "这个", "那个", "怎么", "什么", "如何", "为什么",
    "可以", "能", "想", "知道", "觉得", "应该", "可能", "需要",
    "请", "帮", "帮我", "告诉", "一下", "一些", "还是", "或者",
}

# English stop words
ENGLISH_STOPWORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "of", "and", "or", "but", "not",
    "with", "from", "by", "as", "this", "that", "it", "its", "i", "you",
    "he", "she", "we", "they", "my", "your", "his", "her", "our", "their",
    "what", "how", "why", "when", "where", "which", "who", "whom",
    "can", "could", "would", "should", "will", "do", "does", "did",
    "have", "has", "had", "am", "if", "then", "so", "than", "just",
    "about", "into", "over", "after", "before", "between", "under",
    "again", "further", "once", "here", "there", "all", "each", "few",
    "more", "most", "other", "some", "such", "no", "nor", "only", "own",
    "same", "too", "very", "just", "also", "now", "please", "help", "me",
}

# Combined stop words
ALL_STOPWORDS: Set[str] = CHINESE_STOPWORDS | ENGLISH_STOPWORDS


# =============================================================================
# Keyword Extraction
# =============================================================================

def extract_keywords(
    text: str,
    max_keywords: int = 5,
    min_length: int = 2,
    stopwords: Optional[Set[str]] = None
) -> List[str]:
    """
    Extract keywords from text

    Supports mixed Chinese and English text, automatically filters stop words and short words.

    Args:
        text: Input text
        max_keywords: Maximum number of keywords (default 5)
        min_length: Minimum word length (default 2)
        stopwords: Custom stop word set (defaults to built-in stop words)

    Returns:
        List of keywords (deduplicated, order preserved)

    Example:
        >>> extract_keywords("How to use Python for machine learning?")
        ['Python', 'machine', 'learning']
        >>> extract_keywords("How to build a recommendation system?")
        ['build', 'recommendation', 'system']
    """
    if not text:
        return []

    # Use default stop words
    if stopwords is None:
        stopwords = ALL_STOPWORDS

    # Extract words (mixed Chinese and English)
    # Match: Chinese character sequences or English alphanumeric sequences
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', text)

    # Filter stop words and short words
    keywords = []
    seen = set()

    for word in words:
        word_lower = word.lower()

        # Skip stop words
        if word_lower in stopwords or word in stopwords:
            continue

        # Skip short words
        if len(word) < min_length:
            continue

        # Deduplicate (preserve original case)
        if word_lower not in seen:
            keywords.append(word)
            seen.add(word_lower)

            # Reached maximum count
            if len(keywords) >= max_keywords:
                break

    return keywords


# =============================================================================
# Text Truncation
# =============================================================================

def truncate_text(
    text: str,
    max_length: int = 100,
    suffix: str = "..."
) -> str:
    """
    Smart text truncation

    If the text exceeds the maximum length, truncate at an appropriate position and add a suffix.

    Args:
        text: Input text
        max_length: Maximum length (default 100)
        suffix: Truncation suffix (default "...")

    Returns:
        Truncated text

    Example:
        >>> truncate_text("This is a very long text", max_length=10)
        'This is...'
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    # Calculate actual available length
    available_length = max_length - len(suffix)
    if available_length <= 0:
        return suffix

    return text[:available_length] + suffix


