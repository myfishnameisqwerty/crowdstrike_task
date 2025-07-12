#!/usr/bin/env python3
"""
FastAPI-based Image Downloader API

Provides REST endpoints for downloading images with threading support.
"""

import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from pydantic import ValidationError
from datetime import datetime, timezone

from .models import DownloadRequest, BatchDownloadRequest, BatchDownloadResult
from .downloader import ImageDownloader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Base Endpoint Class
# ============================================================================

class BaseEndpoint:
    def __init__(self, app: FastAPI):
        self.app = app
        self._setup_exception_handlers()

    def _setup_exception_handlers(self):
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(
            request: Request, exc: RequestValidationError
        ):
            logger.warning(f"Validation error: {exc.errors()}")
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Validation Error",
                    "detail": str(exc.errors()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "path": request.url.path,
                },
            )

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": "HTTP Error",
                    "detail": exc.detail,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "path": request.url.path,
                },
            )

        @self.app.exception_handler(ValueError)
        async def value_error_handler(request: Request, exc: ValueError):
            logger.warning(f"ValueError: {exc}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Bad Request",
                    "detail": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "path": request.url.path,
                },
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unexpected error: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "path": request.url.path,
                },
            )

# ============================================================================
# FastAPI App Setup
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Image Downloader Service...")
    logger.info("Image Downloader Service started successfully")
    yield
    # Shutdown
    logger.info("Shutting down Image Downloader Service...")

app = FastAPI(
    title="Image Downloader API",
    description="Threading-based image downloader with retry logic",
    version="1.0.0",
    lifespan=lifespan,
)

base_endpoint = BaseEndpoint(app)

# Global downloader instance
downloader = ImageDownloader(max_workers=15)

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Image Downloader Service",
        "version": "1.0.0",
        "description": "Threading-based image downloader with retry logic",
        "endpoints": {
            "download": "/download",
            "download-single": "/download-single",
            "health": "/health",
        },
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "image-downloader",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "capabilities": {
            "threading": {
                "max_workers": 15,
                "retry_logic": True,
                "timeout_handling": True
            },
            "downloads": {
                "batch_downloads": True,
                "single_downloads": True,
                "file_extension_detection": True
            }
        }
    }

@app.post("/download", response_model=BatchDownloadResult)
def download_images(batch_request: BatchDownloadRequest) -> BatchDownloadResult:
    """
    Download multiple images using threading.
    
    Args:
        batch_request: BatchDownloadRequest containing list of downloads and settings
        
    Returns:
        BatchDownloadResult with results for all downloads
    """
    logger.info(f"Received download request for {len(batch_request.downloads)} images")
    
    # Validate the request
    if not batch_request.downloads:
        raise HTTPException(status_code=400, detail="No downloads specified")
    
    try:
        # Execute the batch download
        result = downloader.download_batch(batch_request)
        
        logger.info(f"Download completed: {result.success_count} successful, {result.failure_count} failed")
        
        return result
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.post("/download-single")
def download_single_image(download_request: DownloadRequest) -> Dict[str, Any]:
    """
    Download a single image.
    
    Args:
        download_request: DownloadRequest containing image URL and target info
        
    Returns:
        DownloadResult for the single download
    """
    logger.info(f"Received single download request for {download_request.name}")
        
    # Create a batch request with single item
    batch_request = BatchDownloadRequest(
    downloads=[download_request],
    max_concurrent=1,
    timeout_seconds=30  # Default timeout for single downloads
    )
        
    try:
        # Execute the download
        result = downloader.download_batch(batch_request)
        
        if result.results:
            return result.results[0].model_dump()
        else:
            raise HTTPException(status_code=500, detail="No result returned from download")
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Single download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}") 