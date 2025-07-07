import unittest
from unittest.mock import MagicMock

from src.models import DataItem
from src.scraper import DataScraper
from src.wiki_scraper import WikipediaAnimalsScraper


class TestDataItem(unittest.TestCase):
    """Test DataItem model."""

    def test_data_item_creation(self):
        """Test DataItem creation with all fields."""
        item = DataItem(
            name="Lion",
            source="wikipedia",
            category="animals",
            image_url="https://example.com/lion.jpg",
            attributes={"collateral_adjective": "leonine"},
            metadata={"scraped_at": "2023-01-01T00:00:00Z"},
        )

        self.assertEqual(item.name, "Lion")
        self.assertEqual(item.source, "wikipedia")
        self.assertEqual(item.category, "animals")
        self.assertEqual(item.image_url, "https://example.com/lion.jpg")
        self.assertEqual(item.attributes["collateral_adjective"], "leonine")


class TestDataScraper(unittest.TestCase):
    """Test DataScraper class."""

    def setUp(self):
        """Set up test fixtures."""
        DataScraper._instance = None
        DataScraper._initialized = False

    def test_filter_application(self):
        """Test filter application to items list."""
        scraper = DataScraper()
        items = [
            DataItem(name="Lion", source="wikipedia", category="animals"),
            DataItem(name="Tiger", source="wikipedia", category="animals"),
            DataItem(name="Elephant", source="wikipedia", category="animals"),
        ]
        
        filters = {"name_in": ["Lion", "Tiger"]}
        filtered = scraper._apply_filters_only(items, filters)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].name, "Lion")
        self.assertEqual(filtered[1].name, "Tiger")

    def test_filter_application_case_insensitive(self):
        """Test filter application is case insensitive."""
        scraper = DataScraper()
        items = [
            DataItem(name="Lion", source="wikipedia", category="animals"),
            DataItem(name="Tiger", source="wikipedia", category="animals"),
        ]
        
        filters = {"name_in": ["lion", "TIGER"]}  # Mixed case
        filtered = scraper._apply_filters_only(items, filters)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].name, "Lion")
        self.assertEqual(filtered[1].name, "Tiger")


class TestWikipediaAnimalsScraper(unittest.TestCase):
    """Test WikipediaAnimalsScraper class."""

    def test_extract_animal_name(self):
        """Test animal name extraction."""
        scraper = WikipediaAnimalsScraper()
        
        # Mock BeautifulSoup element
        mock_cell = MagicMock()
        mock_link = MagicMock()
        mock_link.get.return_value = "Lion"
        mock_cell.find.return_value = mock_link
        
        result = scraper._extract_animal_name(mock_cell)
        self.assertEqual(result, "Lion")

    def test_extract_column_values_with_citations(self):
        """Test column values extraction with citations."""
        scraper = WikipediaAnimalsScraper()
        
        # Mock cell with citations
        mock_cell = MagicMock()
        mock_cell.__str__.return_value = "leonine [1]<br>feline [2]<br>carnivorous [3]"
        
        result = scraper._extract_column_values(mock_cell, "collateral_adjectives")
        
        self.assertEqual(len(result), 3)
        self.assertIn("leonine", result)
        self.assertIn("feline", result)
        self.assertIn("carnivorous", result)
        # Citations should be removed
        self.assertNotIn("[1]", result[0])
        self.assertNotIn("[2]", result[1])
        self.assertNotIn("[3]", result[2])
