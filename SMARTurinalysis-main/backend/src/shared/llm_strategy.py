"""
LLM Strategy Pattern for interacting with different providers.
Enforces the use of the STRATEGY architectural pattern as per the global rules.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json
import logging
import httpx
from pydantic import BaseModel
from google import genai
from google.genai import types

from src.config.config import settings

logger = logging.getLogger("nutri-sentinel")

class LLMStrategy(ABC):
    """
    Abstract Base Class representing an LLM Provider strategy.
    """
    
    @abstractmethod
    async def generate_async(
        self,
        prompt: str,
        system_prompt: str,
        json_mode: bool = False,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None
    ) -> str:
        """Execute an asynchronous call to the LLM."""
        pass

    @abstractmethod
    def generate_sync(
        self,
        prompt: str,
        system_prompt: str,
        json_mode: bool = False,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None
    ) -> str:
        """Execute a synchronous call to the LLM."""
        pass


class GroqStrategy(LLMStrategy):
    """
    Concrete Strategy for Groq API.
    """

    def _prepare_payload(
        self,
        prompt: str,
        system_prompt: str,
        json_mode: bool,
        model: Optional[str],
        image_url: Optional[str],
        max_tokens: Optional[int]
    ) -> dict:
        selected_model = model or settings.LLM_MODEL or "llama-3.1-8b-instant"
        
        if image_url:
            user_content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        else:
            user_content = prompt

        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        return payload

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str,
        json_mode: bool = False,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None
    ) -> str:
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set. Returning mock response.")
            return "{}" if json_mode else "Mock response"
            
        payload = self._prepare_payload(prompt, system_prompt, json_mode, model, image_url, max_tokens)
        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling Groq API (async): {str(e)}")
            raise

    def generate_sync(
        self,
        prompt: str,
        system_prompt: str,
        json_mode: bool = False,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None
    ) -> str:
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set. Returning mock response.")
            return "{}" if json_mode else "Mock response"
            
        payload = self._prepare_payload(prompt, system_prompt, json_mode, model, image_url, max_tokens)
        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling Groq API (sync): {str(e)}")
            raise


class GeminiStrategy(LLMStrategy):
    """
    Concrete Strategy for Google Gemini API.
    """

    def _prepare_config(
        self,
        system_prompt: str,
        json_mode: bool,
        max_tokens: Optional[int],
        tools: Optional[list]
    ) -> types.GenerateContentConfig:
        config_kwargs = {
            "system_instruction": system_prompt,
            "temperature": 0.2,
        }
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        if max_tokens:
            config_kwargs["max_output_tokens"] = max_tokens
        if tools:
            config_kwargs["tools"] = tools
            
        return types.GenerateContentConfig(**config_kwargs)

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str,
        json_mode: bool = False,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None
    ) -> str:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        selected_model = model or settings.GEMINI_MODEL or "gemini-2.5-flash"
        config = self._prepare_config(system_prompt, json_mode, max_tokens, tools)
        
        # Note: We are doing sync generation here as genai.Client.models doesn't expose async directly in this SDK version
        # Or we can wrap it in asyncio.to_thread if we want true non-blocking
        import asyncio
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=selected_model,
            contents=prompt,
            config=config
        )
        return response.text

    def generate_sync(
        self,
        prompt: str,
        system_prompt: str,
        json_mode: bool = False,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None
    ) -> str:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        selected_model = model or settings.GEMINI_MODEL or "gemini-2.5-flash"
        config = self._prepare_config(system_prompt, json_mode, max_tokens, tools)
        
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=config
        )
        return response.text
