"""
FastAPI Middleware for Request/Response Logging
================================================

Logs all HTTP requests and responses with timing information
"""

import time
import uuid
import sys
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.utils.logger import logger, request_id_var


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Start timing
        start_time = time.time()
        
        # Log request
        logger.bind(request_id=request_id).info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        # Optionally log request body (be careful with sensitive data!)
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                logger.bind(request_id=request_id).debug(
                    f"Request body: {body.decode('utf-8')[:500]}"  # Limit to 500 chars
                )
            except Exception as e:
                logger.bind(request_id=request_id).warning(f"Could not read request body: {e}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.bind(request_id=request_id).info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration,
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.bind(request_id=request_id).error(
                f"Request failed: {request.method} {request.url.path} - {str(e)} ({duration:.3f}s)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration,
                    "error": str(e),
                }
            )
            raise


class LoguruInterceptHandler:
    """
    Intercept standard logging and redirect to Loguru
    Useful for third-party libraries that use standard logging
    """
    
    def __init__(self, level: str = "INFO"):
        self.level = level
    
    def __call__(self, record):
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = self.level
        
        # Find caller from where the logged message originated
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == __file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )