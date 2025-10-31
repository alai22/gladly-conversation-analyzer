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
        """Send a message to Claude API with automatic model fallback"""
        # Resolve model through aliases and fallbacks
        requested_model = model or Config.CLAUDE_MODEL
        model = Config.resolve_model(requested_model)
        
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
            timeout = Config.CLAUDE_API_TIMEOUT
            logger.info(f"Sending message to Claude: model={model}, max_tokens={max_tokens}, timeout={timeout}s")
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            
            response_data = response.json()
            logger.info(f"Claude response received: tokens_used={response_data.get('usage', {}).get('output_tokens', 0)}")
            
            return ClaudeResponse.from_api_response(response_data, model)
        
        except requests.exceptions.Timeout as e:
            logger.error(f"Claude API request timed out after {Config.CLAUDE_API_TIMEOUT} seconds. The request may be too complex or the API is slow.")
            raise TimeoutError(f"Request to Claude API timed out after {Config.CLAUDE_API_TIMEOUT} seconds. The query may be too complex or there may be network issues. Please try again or simplify your query.") from e
        
        except requests.exceptions.RequestException as e:
            # If model not found error and we haven't tried fallback yet
            if hasattr(e, 'response') and e.response is not None:
                error_data = e.response.json() if e.response.headers.get('content-type', '').startswith('application/json') else {}
                error_type = error_data.get('error', {}).get('type', '')
                
                if error_type == 'not_found_error' and model != Config.FALLBACK_MODEL and requested_model != Config.FALLBACK_MODEL:
                    logger.warning(f"Model '{model}' not found, falling back to '{Config.FALLBACK_MODEL}'")
                    # Retry with fallback model
                    payload['model'] = Config.FALLBACK_MODEL
                    response = requests.post(
                        f"{self.base_url}/messages",
                        headers=self.headers,
                        json=payload,
                        timeout=Config.CLAUDE_API_TIMEOUT
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    logger.info(f"Claude response received with fallback model: tokens_used={response_data.get('usage', {}).get('output_tokens', 0)}")
                    return ClaudeResponse.from_api_response(response_data, Config.FALLBACK_MODEL)
            
            logger.error(f"Claude API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response details: {e.response.text}")
            raise
    
    def stream_message(self, 
                      message: str, 
                      model: str = None,
                      max_tokens: int = 1000,
                      system_prompt: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """Stream a message from Claude API with automatic model fallback"""
        # Resolve model through aliases and fallbacks
        requested_model = model or Config.CLAUDE_MODEL
        model = Config.resolve_model(requested_model)
        
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
            timeout = Config.CLAUDE_API_TIMEOUT
            logger.info(f"Streaming message to Claude: model={model}, max_tokens={max_tokens}, timeout={timeout}s")
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=timeout
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
        
        except requests.exceptions.Timeout as e:
            logger.error(f"Claude API streaming request timed out after {Config.CLAUDE_API_TIMEOUT} seconds.")
            raise TimeoutError(f"Streaming request to Claude API timed out after {Config.CLAUDE_API_TIMEOUT} seconds. The query may be too complex or there may be network issues.") from e
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Claude streaming request failed: {str(e)}")
            raise
    
    def is_available(self) -> bool:
        """Check if Claude service is available, trying fallback models if needed"""
        # Resolve the configured model first
        model = Config.resolve_model()
        
        # Try configured/aliased model first
        models_to_try = [model]
        
        # Add fallback if it's different
        if Config.FALLBACK_MODEL not in models_to_try:
            models_to_try.append(Config.FALLBACK_MODEL)
        
        # Try verified models as last resort
        for verified_model in Config.VERIFIED_MODELS:
            if verified_model not in models_to_try:
                models_to_try.append(verified_model)
                break  # Only need one fallback
        
        # Use shorter timeout for health check
        health_check_timeout = min(30, Config.CLAUDE_API_TIMEOUT // 4)
        
        for test_model in models_to_try:
            try:
                response = requests.post(
                    f"{self.base_url}/messages",
                    headers=self.headers,
                    json={
                        "model": test_model,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "test"}]
                    },
                    timeout=health_check_timeout
                )
                if response.status_code == 200:
                    if test_model != model:
                        logger.info(f"Health check: '{model}' unavailable, using working model '{test_model}'")
                    return True
                else:
                    logger.warning(f"Model '{test_model}' health check returned status {response.status_code}")
            except requests.exceptions.Timeout:
                logger.warning(f"Model '{test_model}' health check timed out")
                continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"Model '{test_model}' health check failed: {str(e)}")
                continue
            except Exception as e:
                logger.warning(f"Model '{test_model}' health check error: {str(e)}")
                continue
        
        return False
