""" 
@file_name: openai_agents_sdk.py
@author: NetMind.AI
@date: 2025-11-07
@description: This file contains the openai agents sdk.
"""


from typing import AsyncGenerator
from agents import Agent, Runner, OpenAIChatCompletionsModel
from pydantic import BaseModel
from openai import AsyncOpenAI

from xyz_agent_context.settings import settings


class OpenAIAgentsSDK:
    def __init__(self):
        pass
    
    async def agent_loop(
        self) -> AsyncGenerator[str, None]:
        pass
    
    async def llm_function(
        self,
        instructions: str,
        user_input: str,
        output_type: BaseModel = None,
    ) -> str:
        
        agent = Agent(
            name="ChatGPT",
            instructions=instructions,
            output_type=output_type,
            model=OpenAIChatCompletionsModel(
                model="gpt-5.1-2025-11-13",
                openai_client=AsyncOpenAI(api_key=settings.openai_api_key),
            ),
        )
        
        result = await Runner.run(agent, user_input)
        
        return result
