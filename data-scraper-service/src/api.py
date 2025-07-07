from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

from .scraper import scrape_data, init_scrapers
from .image_cache import image_cache
from .models import (
    ScrapingRequest, ScrapingResponse,
    ScrapeResponseModel, DataItemResponseModel,
    HealthResponseModel, ErrorResponseModel
)

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
                content=ErrorResponseModel(
                    error="Validation Error",
                    detail=str(exc.errors()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    path=request.url.path,
                ).model_dump(),
            )

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponseModel(
                    error="HTTP Error",
                    detail=exc.detail,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    path=request.url.path,
                ).model_dump(),
            )

        @self.app.exception_handler(ValueError)
        async def value_error_handler(request: Request, exc: ValueError):
            logger.warning(f"ValueError: {exc}")
            return JSONResponse(
                status_code=400,
                content=ErrorResponseModel(
                    error="Bad Request",
                    detail=str(exc),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    path=request.url.path,
                ).model_dump(),
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unexpected error: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=ErrorResponseModel(
                    error="Internal Server Error",
                    detail="An unexpected error occurred",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    path=request.url.path,
                ).model_dump(),
            )

    async def _handle_health_check_error(self, error: Exception) -> JSONResponse:
        logger.error(f"Health check failed: {error}")
        return JSONResponse(
            status_code=503,
            content=HealthResponseModel(
                status="unhealthy",
                service="data-scraper-service",
                timestamp=datetime.now(timezone.utc).isoformat(),
                version="1.0.0",
                error=str(error),
            ).model_dump(),
        )


# ============================================================================
# Serializers
# ============================================================================


class ResponseSerializer:
    @staticmethod
    def serialize_scrape_response(response: ScrapingResponse) -> ScrapeResponseModel:
        return ScrapeResponseModel(
            items=[DataItemResponseModel.model_validate(item.model_dump()) for item in response.items],
            total_count=response.total_count,
            source=response.source,
            category=response.category,
            timestamp=response.timestamp,
            metadata=response.metadata
        )
        
        
    @staticmethod
    def serialize_health_response(
        healthy: bool = True, 
        capabilities: Optional[Dict[str, Any]] = None,
        cache_status: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> HealthResponseModel:
        return HealthResponseModel(
            status="healthy" if healthy else "unhealthy",
            service="data-scraper-service",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="1.0.0",
            capabilities=capabilities or {},
            cache_status=cache_status or {},
            error=error,
        )


# ============================================================================
# FastAPI App Setup
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Data Scraper Service...")
    init_scrapers()
    logger.info("Data Scraper Service started successfully")
    yield
    # Shutdown
    logger.info("Shutting down Data Scraper Service...")


app = FastAPI(
    title="Data Scraper Service",
    description="Service for scraping data from various sources",
    version="1.0.0",
    lifespan=lifespan,
)

base_endpoint = BaseEndpoint(app)


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Data Scraper Service",
        "version": "1.0.0",
        "description": "Service for scraping data from various sources",
        "endpoints": {
            "scrape": "/scrape",
            "health": "/health",
            "cache_stats": "/cache/stats",
        },
    }


@app.get("/scrape", response_model=ScrapeResponseModel)
async def scrape_endpoint_get(
    source: str = Query(..., description="Data source (e.g., wikipedia)"),
    category: str = Query(..., description="Category of data to scrape (e.g., animals)"),
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Maximum number of items to return"
    ),
    offset: Optional[int] = Query(
        None, ge=0, description="Number of items to skip (for pagination)"
    ),
    name_in: Optional[List[str]] = Query(
        None, description="Filter items by exact names (case-insensitive)"
    ),
):
    """Scrape data from specified source and category."""
    # Build filters dict
    filters = {}
    if name_in:
        filters["name_in"] = name_in

    # Create request object
    request = ScrapingRequest(
        source=source,
        category=category,
        filters=filters if filters else None,
        limit=limit,
        offset=offset,
    )

    # Scrape data
    response = await scrape_data(request)
    
    # Serialize and return response
    return ResponseSerializer.serialize_scrape_response(response)


@app.get("/health", response_model=HealthResponseModel)
async def health_check():
    """Health check endpoint with cache status."""
    try:
        # Get cache statistics
        cache_stats = image_cache.get_stats()
        
        # Define service capabilities
        capabilities = {
            "scraping": {
                "sources": ["wikipedia"],
                "categories": ["animals"],
                "filters": ["name_in", "limit", "offset"],
                "async": True
            },
            "caching": {
                "enabled": True,
                "ttl": 3600,  # 1 hour
                "max_size": 1000
            }
        }
        
        return ResponseSerializer.serialize_health_response(
            healthy=True,
            capabilities=capabilities,
            cache_status=cache_stats
        )
    except Exception as e:
        return await base_endpoint._handle_health_check_error(e)


@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    return image_cache.get_stats()


@app.delete("/cache")
async def clear_cache(
    source: str = Query(
        ..., description="Clear cache for specific source (e.g., wikipedia)"
    ),
    category: str = Query(..., description="Clear cache for specific category (e.g., animals)"),
):
    """Clear cache for specific source and category."""
    cleared_count = image_cache.clear_by_source_category(source, category)
    return {
        "message": f"Cleared {cleared_count} cached items for {source}:{category}",
        "cleared_count": cleared_count,
        "source": source,
        "category": category,
    }


@app.delete("/cache/all")
async def clear_all_cache():
    """Clear all cached data."""
    cleared_count = image_cache.clear_all()
    return {
        "message": f"Cleared all {cleared_count} cached items",
        "cleared_count": cleared_count,
    }
