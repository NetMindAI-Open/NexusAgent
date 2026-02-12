""" 
@file_name: gemini_api_sdk.py
@author: NetMind.AI
@date: 2025-12-04
@description: This file contains the gemini api sdk.

"""

from pydantic import BaseModel
from google import genai

from xyz_agent_context.settings import settings

class GeminiAPISDK:


    def __init__(self, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model = model
        
    
    async def llm_function(
        self,
        instructions: str,
        user_input: str,
        output_type: BaseModel = None,
        file_path: str = None,
    ) -> str:
        
        if file_path:
            if file_path.endswith(".pdf"):
                return await self._make_response_with_pdf(instructions, user_input, output_type, file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_path}")
        else:
            return await self._make_response(instructions, user_input, output_type)
    
    async def _make_response_with_pdf(
        self,
        instructions: str,
        user_input: str,
        output_type: BaseModel = None,
        file_path: str = None,   
    ) -> str:
        
        file = self.client.files.upload(
        file=file_path,
        )

        prompt=f"""
# System Instructions
{instructions}

# User Input
{user_input}
"""

        if output_type:
            response = self.client.models.generate_content(
            model=self.model,
            contents=[file, prompt],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": output_type.model_json_schema(),
                },
            )
        else:
            response = self.client.models.generate_content(
            model=self.model,
            contents=[file, prompt],
            )
        
        return response
    
    async def _make_response(
        self,
        instructions: str,
        user_input: str,
        output_type: BaseModel = None,
    ) -> str:
        
        prompt=f"""
# System Instructions
{instructions}

# User Input
{user_input}
"""
        
        if output_type:
            response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": output_type.model_json_schema(),
                },
            )
        else:
            response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            )
        
        return response
    


