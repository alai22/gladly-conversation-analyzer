"""
Request logging middleware for debugging
"""

from flask import request, g
from ...utils.logging import get_logger
import time

logger = get_logger('request_logging')


def register_request_logging(app):
    """Register request logging middleware"""
    
    @app.before_request
    def log_request():
        """Log incoming requests"""
        g.request_start_time = time.time()
        g.request_id = f"{time.time()}-{id(request)}"
        
        # Calculate total header size
        header_size = sum(len(k) + len(v) + 4 for k, v in request.headers.items())  # +4 for ': ' and '\r\n'
        
        logger.info(
            f"[REQUEST] {request.method} {request.path} | "
            f"Remote: {request.remote_addr} | "
            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')[:50]} | "
            f"Content-Type: {request.content_type} | "
            f"Content-Length: {request.content_length or 0} | "
            f"Header Size: {header_size} bytes"
        )
        
        # Log if headers are large (potential 431 issue)
        if header_size > 8000:
            logger.warning(
                f"[REQUEST] Large headers detected: {header_size} bytes | "
                f"Path: {request.path} | "
                f"Cookie header length: {len(request.headers.get('Cookie', ''))}"
            )
        
        # Log headers if verbose (but truncate to avoid huge logs)
        if request.headers:
            header_summary = {k: (v[:100] if len(v) > 100 else v) 
                            for k, v in request.headers.items() 
                            if k.lower() not in ['authorization']}  # Still log cookies to debug 431
            # For cookies, just show length
            if 'Cookie' in request.headers:
                cookie_len = len(request.headers['Cookie'])
                header_summary['Cookie'] = f'[Length: {cookie_len} bytes - truncated for logging]'
            logger.debug(f"[REQUEST] Headers: {header_summary}")
        
        # Log request body for POST/PUT (truncated)
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.is_json:
                    data = request.get_json(silent=True) or {}
                    # Truncate large data
                    data_str = str(data)
                    if len(data_str) > 500:
                        data_str = data_str[:500] + "... (truncated)"
                    logger.debug(f"[REQUEST] JSON body: {data_str}")
                else:
                    body = request.get_data(as_text=True)
                    if body and len(body) > 500:
                        body = body[:500] + "... (truncated)"
                    logger.debug(f"[REQUEST] Body: {body[:500] if body else 'empty'}")
            except Exception as e:
                logger.warning(f"[REQUEST] Failed to log request body: {str(e)}")
    
    @app.after_request
    def log_response(response):
        """Log outgoing responses"""
        duration = time.time() - g.get('request_start_time', time.time())
        request_id = g.get('request_id', 'unknown')
        
        logger.info(
            f"[RESPONSE] {request.method} {request.path} | "
            f"Status: {response.status_code} | "
            f"Duration: {duration:.3f}s | "
            f"Size: {response.content_length or len(response.get_data())} bytes | "
            f"Request-ID: {request_id}"
        )
        
        # Log response body for errors (truncated)
        if response.status_code >= 400:
            try:
                response_data = response.get_data(as_text=True)
                if response_data and len(response_data) > 1000:
                    response_data = response_data[:1000] + "... (truncated)"
                logger.error(
                    f"[RESPONSE ERROR] {request.method} {request.path} | "
                    f"Status: {response.status_code} | "
                    f"Body: {response_data}"
                )
            except Exception as e:
                logger.warning(f"[RESPONSE] Failed to log error response: {str(e)}")
        
        return response

