from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from typing import Union

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging"""
    logger.warning(f"HTTP {exc.status_code} error on {request.url}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "error_code": exc.status_code
        }
    )

async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions"""
    logger.warning(f"Starlette HTTP {exc.status_code} error on {request.url}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "error_code": exc.status_code
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation error",
            "error_code": 422,
            "details": exc.errors()
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error on {request.url}: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "error_code": 500
        }
    )

class APIError(Exception):
    """Custom API error class"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or str(status_code)
        super().__init__(self.message)

class DocumentProcessingError(APIError):
    """Error during document processing"""
    def __init__(self, message: str):
        super().__init__(message, 422, "DOCUMENT_PROCESSING_ERROR")

class RAGFlowError(APIError):
    """Error communicating with RAGFlow"""
    def __init__(self, message: str):
        super().__init__(message, 503, "RAGFLOW_ERROR")

class DatabaseError(APIError):
    """Database operation error"""
    def __init__(self, message: str):
        super().__init__(message, 500, "DATABASE_ERROR")

async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors"""
    logger.error(f"API error on {request.url}: {exc.message}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "error_code": exc.error_code
        }
    )