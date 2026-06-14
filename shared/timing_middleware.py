import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from shared.logging_config import get_logger

logger = get_logger("metric_middleware")

class UnpluggedTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log latency in milliseconds
        logger.info(
            f"API_LATENCY | {request.method} {request.url.path} | "
            f"Status: {response.status_code} | Time: {process_time * 1000:.2f}ms"
        )
        
        # Add Server-Timing header (Standard for RUM)
        response.headers["Server-Timing"] = f"total;dur={process_time * 1000:.2f}"
        
        return response
