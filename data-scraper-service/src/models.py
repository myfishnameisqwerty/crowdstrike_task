from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, timezone

from common import SourceValidator


class DataItem(BaseModel):
    name: str
    source: str  # e.g., 'wikipedia'
    category: str  # e.g., 'animals' (renamed from 'type')
    image_url: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScrapingRequest(BaseModel):
    source: str  # e.g., 'wikipedia'
    category: str  # e.g., 'animals' (renamed from 'type')
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class ScrapingResponse(BaseModel):
    items: List[DataItem]
    total_count: int
    source: str
    category: str  # renamed from 'type'
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DataItemResponseModel(BaseModel):
    name: str
    source: str
    category: str
    image_url: Optional[str] = None
    attributes: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    model_config = {"from_attributes": True}


class ScrapeResponseModel(BaseModel):
    items: List[DataItemResponseModel]
    total_count: int
    source: str
    category: str
    timestamp: str
    metadata: Dict[str, Any] = {}
    model_config = {"from_attributes": True}


class HealthResponseModel(BaseModel):
    status: str
    service: str
    timestamp: str
    version: str
    uptime: Optional[float] = None
    capabilities: Dict[str, Any] = {}
    cache_status: Dict[str, Any] = {}
    error: Optional[str] = None


class SourceTypeInfoModel(BaseModel):
    source: str
    category: str
    description: str


class ErrorResponseModel(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str
    path: str
