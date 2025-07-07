from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, computed_field
from datetime import datetime, timezone
import os

from common import SourceValidator


class DownloadRequest(BaseModel):
    """Request model for downloading a single image."""
    image_url: str = Field(..., description="URL of the image to download")
    name: str = Field(..., description="Name of the item for filename generation")
    source: str = Field(..., description="Data source (e.g., wikipedia)")
    category: str = Field(..., description="Data category (e.g., animals)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('image_url')
    @classmethod
    def validate_image_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('image_url must be a valid HTTP/HTTPS URL')
        return v

    @field_validator('source', 'category')
    @classmethod
    def validate_source_category(cls, v, info):
        if info.field_name == 'source':
            # Store source for category validation
            return v
        elif info.field_name == 'category':
            # Get source from the same request
            source = info.data.get('source')
            if source:
                SourceValidator.validate(source, v)
        return v

    @computed_field
    @property
    def source_type(self) -> str:
        """Computed field for backward compatibility and directory naming."""
        return f"{self.source}_{self.category}"

    @computed_field
    @property
    def target_path(self) -> str:
        """Generate the full target path for the image."""
        # Create organized directory structure: /tmp/{source_type}/
        download_dir = f"/tmp/{self.source_type}"
        
        # Simple filename generation: lowercase name with underscores
        safe_name = self.name.lower().replace(" ", "_")
        filename = f"{safe_name}.jpg"
        
        return os.path.join(download_dir, filename)


class DownloadResult(BaseModel):
    """Result model for a single image download."""
    image_url: str
    target_path: str
    is_successful: bool = Field(..., description="Whether the download was successful")
    error_message: Optional[str] = None
    file_size: Optional[int] = None
    download_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchDownloadRequest(BaseModel):
    """Request model for downloading multiple images."""
    downloads: List[DownloadRequest] = Field(..., description="List of images to download")
    max_concurrent: int = Field(5, ge=1, le=20, description="Maximum concurrent downloads")
    timeout_seconds: int = Field(30, ge=5, le=300, description="Timeout for each download in seconds")


class BatchDownloadResult(BaseModel):
    """Result model for batch image downloads."""
    results: List[DownloadResult]
    total_count: int
    success_count: int
    failure_count: int
    total_time: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    version: str
    uptime: Optional[float] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str 