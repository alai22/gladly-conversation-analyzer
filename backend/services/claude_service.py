"""
Claude API service
"""

import json
import requests
from typing import Optional, Dict, Any, Generator
from ..utils.config import Config
from ..utils.logging import get_logger
from ..models.response import ClaudeResponse

logger = get_logger('claude_service')


class ClaudeService:
    """Service for interacting with Claude API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude service"""
        self.api_key = api_key or Config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("API key not provided. Set ANTHROPIC_API_KEY in config or environment variable")
        
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    
    def send_message(self, 
                    message: str, 
                    model: str = None,
                    max_tokens: int = 1000,
                    system_prompt: Optional[str] = None) -> ClaudeResponse:
        """Send a message to Claude API"""
        model = model or Config.CLAUDE_MODEL
        
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            logger.info("Sending message to Claude", model=model, max_tokens=max_tokens)
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            response_data = response.json()
            logger.info("Claude response received", tokens_used=response_data.get('usage', {}).get('output_tokens', 0))
            
            return ClaudeResponse.from_api_response(response_data, model)
        
        except requests.exceptions.RequestException as e:
            logger.error("Claude API request failed", error=str(e))
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Response details", response_text=e.response.text)
            raise
    
    def stream_message(self, 
                      message: str, 
                      model: str = None,
                      max_tokens: int = 1000,
                      system_prompt: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """Stream a message from Claude API"""
        model = model or Config.CLAUDE_MODEL
        
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            logger.info("Streaming message to Claude", model=model, max_tokens=max_tokens)
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data.strip() == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
        
        except requests.exceptions.RequestException as e:
            logger.error("Claude streaming request failed", error=str(e))
            raise
    
    def is_available(self) -> bool:
        """Check if Claude service is available"""
        try:
            # Simple health check - send a minimal request
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json={
                    "model": Config.CLAUDE_MODEL,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "test"}]
                },
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
