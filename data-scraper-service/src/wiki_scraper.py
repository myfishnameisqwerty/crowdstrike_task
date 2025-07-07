import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
from abc import ABC, abstractmethod
import time
import re
import asyncio

from .models import DataItem, ScrapingRequest
from .image_cache import image_cache

# Configure logging
logger = logging.getLogger(__name__)


class WikiScraper(ABC):
    """Abstract base class for Wikipedia scrapers."""

    def __init__(
        self,
        *,
        url: str,
        source: str,
        category: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.url = url
        self.source = source  # e.g., 'wikipedia'
        self.category = category  # e.g., 'animals'
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.soup: Optional[BeautifulSoup] = None

    async def _make_request(self, session: aiohttp.ClientSession, url: str, timeout: int = 30) -> str:
        """Make HTTP request with retry mechanism."""
        for attempt in range(self.max_retries):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    response.raise_for_status()
                    return await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Failed to fetch {url} after {self.max_retries} attempts: {e}"
                    )
                    raise
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff

    async def _load_soup(self, session: aiohttp.ClientSession):
        """Load BeautifulSoup object from URL with retry mechanism."""
        if self.soup is None:
            content = await self._make_request(session, self.url)
            self.soup = BeautifulSoup(content, "html.parser")

    async def _extract_wiki_image_url(self, session: aiohttp.ClientSession, element, item_name: Optional[str] = None) -> Optional[str]:
        """Extract image URL from Wikipedia article pages."""
        try:
            # First check cache if item name is provided
            if item_name:
                cached_url = image_cache.get_image_url(self.category, item_name)
                if cached_url:
                    logger.debug(
                        f"Using cached image URL for {item_name}: {cached_url}"
                    )
                    return cached_url

            # Look for Wikipedia article links
            link = element.find("a")
            if link and link.get("href") and link.get("href").startswith("/wiki/"):
                article_url = f"https://en.wikipedia.org{link.get('href')}"
                logger.debug(f"Checking article for {item_name}: {article_url}")

                try:
                    # Fetch the individual article page
                    content = await self._make_request(session, article_url, timeout=10)
                    article_soup = BeautifulSoup(content, "html.parser")

                    # Look for images in the infobox (main image)
                    infobox = article_soup.find("table", {"class": "infobox"})
                    if infobox:
                        images = infobox.find_all("img")
                        for img in images:
                            src = img.get("src")
                            if src and not src.endswith(".svg"):  # Skip SVG icons
                                # Convert relative URLs to absolute
                                if src.startswith("//"):
                                    image_url = f"https:{src}"
                                elif src.startswith("/"):
                                    image_url = f"https://en.wikipedia.org{src}"
                                elif src.startswith("http"):
                                    image_url = src
                                else:
                                    image_url = f"https://en.wikipedia.org/{src}"

                                # Cache the extracted URL if item name is provided
                                if item_name and image_url:
                                    image_cache.set_image_url(
                                        self.category,
                                        item_name,
                                        image_url,
                                        metadata={
                                            "source": "wikipedia_article",
                                            "extracted_at": datetime.now(
                                                timezone.utc
                                            ).isoformat(),
                                        },
                                    )

                                logger.debug(
                                    f"Found image for {item_name}: {image_url}"
                                )
                                return image_url

                    # If no infobox image, look for any image in the article
                    images = article_soup.find_all("img")
                    for img in images:
                        src = img.get("src")
                        if (
                            src
                            and src.startswith("//upload.wikimedia.org/")
                            and not src.endswith(".svg")
                        ):
                            image_url = f"https:{src}"

                            # Cache the extracted URL if item name is provided
                            if item_name and image_url:
                                image_cache.set_image_url(
                                    self.category,
                                    item_name,
                                    image_url,
                                    metadata={
                                        "source": "wikipedia_article",
                                        "extracted_at": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                    },
                                )

                            logger.debug(
                                f"Found article image for {item_name}: {image_url}"
                            )
                            return image_url

                except Exception as e:
                    logger.warning(f"Error fetching article for {item_name}: {e}")

            return None
        except Exception as e:
            logger.warning(f"Error extracting image URL: {e}")
            return None

    def _extract_animal_name(self, cell) -> Optional[str]:
        """Extract and clean animal name from table cell."""
        try:
            # Look for link with title attribute - this is the cleanest way
            link = cell.find("a")
            if link and link.get("title"):
                return link.get("title")

            # Fallback to text content if no link found
            animal_name = cell.get_text(strip=True)
            return animal_name if animal_name else None

        except Exception as e:
            logger.warning(f"Error extracting animal name: {e}")
            return None

    def _extract_column_values(self, cell, column_name: str) -> List[str]:
        """Extract values from any column, handling <br> tags and citations."""
        try:
            if not cell:
                return []

            # Get all text content, preserving <br> tags
            content = str(cell)

            # Split by <br> tags to get multiple values
            parts = re.split(r"<br\s*/?>", content, flags=re.IGNORECASE)

            values = []
            for part in parts:
                # Parse each part as HTML to get clean text
                part_soup = BeautifulSoup(part, "html.parser")
                text = part_soup.get_text(strip=True)

                # Remove citations like [107], [5], [c], etc.
                text = re.sub(r"\[\w+\]", "", text)

                # Remove superscript references
                text = re.sub(r"<sup[^>]*>.*?</sup>", "", text, flags=re.DOTALL)

                # Clean up any remaining HTML
                text = re.sub(r"<[^>]+>", "", text)

                # Remove parentheses and their content (e.g., "taurine (male)" -> "taurine")
                text = re.sub(r"\s*\([^)]*\)\s*", "", text)

                # Clean up whitespace
                text = text.strip()

                if text:
                    values.append(text)

            return values
        except Exception as e:
            logger.warning(f"Error extracting {column_name} values: {e}")
            return []

    @abstractmethod
    async def scrape(self, session: aiohttp.ClientSession, request: ScrapingRequest) -> List[DataItem]:
        """Abstract method that each scraper must implement."""
        pass


class WikipediaAnimalsScraper(WikiScraper):
    """Scraper for Wikipedia animals collateral adjectives."""

    def __init__(self):
        super().__init__(
            url="https://en.wikipedia.org/wiki/List_of_animal_names",
            source="wikipedia",
            category="animals",
        )

    async def scrape(self, session: aiohttp.ClientSession, request: ScrapingRequest) -> List[DataItem]:
        """Scrape animal data from Wikipedia."""
        await self._load_soup(session)

        # Find the second table "Terms by species or taxon"
        tables = self.soup.find_all("table", {"class": "wikitable"})
        if len(tables) < 2:
            logger.error("Could not find the 'Terms by species or taxon' table")
            return []

        target_table = tables[1]  # Second table
        rows = target_table.find_all("tr")[1:]  # Skip header row

        items = []

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # Extract animal name from the first column
            animal_name = self._extract_animal_name(cells[0])
            if not animal_name or animal_name == "(list)":
                continue

            # Extract collateral adjectives from the second column
            collateral_adjectives = self._extract_column_values(cells[1], "collateral_adjectives")

            # Create a DataItem for each collateral adjective
            for adjective in collateral_adjectives:
                if adjective.strip():  # Skip empty adjectives
                    # Extract image URL for this animal
                    image_url = await self._extract_wiki_image_url(session, cells[0], animal_name)

                    item = DataItem(
                        name=animal_name,
                        source=self.source,
                        category=self.category,
                        image_url=image_url,
                        attributes={
                            "collateral_adjective": adjective.strip(),
                            "animal_name": animal_name,
                        },
                        metadata={
                            "scraped_at": datetime.now(timezone.utc).isoformat(),
                            "source_url": self.url,
                        },
                    )
                    items.append(item)

        logger.info(f"Scraped {len(items)} items from Wikipedia animals table")
        return items
