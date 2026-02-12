"""
@file_name: config.py
@author: NetMind.AI
@date: 2025-11-07
@description: This file contains the config for the agent context module.

Global configuration, shared by all modules
"""


# ==================== Narrative LLM Dynamic Update ====================

# LLM update interval (number of Events)
# Description: Use LLM to update Narrative metadata every N Events
# Default: 1 (update every time)
# Can be set to 3-5 to reduce LLM call costs
# Updated fields: name, current_summary, actors, topic_keywords, dynamic_summary
NARRATIVE_LLM_UPDATE_INTERVAL = 1




