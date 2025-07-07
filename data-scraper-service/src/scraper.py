from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
import aiohttp

from .models import DataItem, ScrapingRequest, ScrapingResponse
from .wiki_scraper import WikipediaAnimalsScraper
from common import SourceValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataScraper:
    """Generic data scraper that manages scrapers."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataScraper, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Initialize scrapers
            self._scrapers = {}
            self._discover_scrapers()
            DataScraper._initialized = True

    def _discover_scrapers(self):
        """Discover and register all scraper classes."""
        # Register the Wikipedia animals scraper
        scraper_instance = WikipediaAnimalsScraper()
        self.register_scraper("wikipedia", "animals", scraper_instance)
        logger.info(f"Registered scraper: wikipedia - animals")

    async def scrape_data(self, request: ScrapingRequest) -> ScrapingResponse:
        """Scrape data using the appropriate scraper."""
        # Validate source/category using SourceValidator
        SourceValidator.validate(request.source, request.category)
        
        scraper_key = (request.source, request.category)

        if scraper_key not in self._scrapers:
            raise ValueError(
                f"No scraper registered for source '{request.source}' and category '{request.category}'"
            )

        scraper = self._scrapers[scraper_key]
        
        # Create aiohttp session with proper headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # Scrape all data (no limit applied during scraping)
            items = await scraper.scrape(session, request)

        # Apply filters first
        filtered_items = self._apply_filters_only(items, request.filters)
        
        # Apply offset if specified
        if request.offset and request.offset > 0:
            if request.offset >= len(filtered_items):
                # Offset is beyond available items, return empty list
                filtered_items = []
            else:
                filtered_items = filtered_items[request.offset:]
        
        # Apply limit after offset for proper pagination
        if request.limit and request.limit > 0:
            filtered_items = filtered_items[:request.limit]

        return ScrapingResponse(
            items=filtered_items,
            total_count=len(filtered_items),
            source=request.source,
            category=request.category,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "original_count": len(items),
                "filtered_count": len(self._apply_filters_only(items, request.filters)),
                "filters_applied": bool(request.filters),
                "limit_applied": bool(request.limit),
                "offset_applied": bool(request.offset),
                "offset_value": request.offset or 0,
                "limit_value": request.limit or None,
            },
        )

    def _apply_filters_only(
        self,
        items: List[DataItem],
        filters: Optional[Dict[str, Any]],
    ) -> List[DataItem]:
        """Apply filters to items (limit is handled by individual scrapers)."""
        if not filters:
            return items

        filtered_items = [
            item
            for item in items
            if self._item_passes_filters(item, filters)
        ]

        return filtered_items

    def _item_passes_filters(self, item: DataItem, filters: Dict[str, Any]) -> bool:
        """Check if an item passes all filters."""
        for filter_key, filter_value in filters.items():
            if filter_key == "name_in" and filter_value:
                # filter_value should be a list of names (case-insensitive)
                if not any(item.name.lower() == name.lower() for name in filter_value):
                    return False
        return True

    def register_scraper(self, source: str, category: str, scraper):
        """Register a scraper for a specific source and data category."""
        self._scrapers[(source, category)] = scraper

    def get_available_scrapers(self) -> List[tuple]:
        """Get list of available scrapers."""
        return list(self._scrapers.keys())

    @staticmethod
    def is_supported(source: str, category: str) -> bool:
        try:
            SourceValidator.validate(source, category)
            return True
        except ValueError:
            return False


def init_scrapers() -> DataScraper:
    """Initialize and return the DataScraper singleton."""
    return DataScraper()


async def scrape_data(request: ScrapingRequest) -> ScrapingResponse:
    """Convenience function to scrape data."""
    scraper = DataScraper()
    return await scraper.scrape_data(request)
