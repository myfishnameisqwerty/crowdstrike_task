import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.api import app
from src.models import (
    DataItem, ScrapingResponse
)


class TestAPIBasicEndpoints(unittest.TestCase):
    """Test basic API endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_endpoint_200(self):
        """Test health endpoint returns 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "data-scraper-service")

    def test_health_endpoint_503(self):
        """Test health endpoint returns 503 when unhealthy."""
        with patch('src.api.image_cache.get_stats', side_effect=Exception("Cache error")):
            response = self.client.get("/health")
            self.assertEqual(response.status_code, 503)
            
            data = response.json()
            self.assertEqual(data["status"], "unhealthy")
            self.assertIn("error", data)

    def test_cache_stats_endpoint_200(self):
        """Test cache stats endpoint returns 200."""
        with patch('src.api.image_cache.get_stats') as mock_cache:
            mock_cache.return_value = {
                "status": "active",
                "total_cached_items": 5,
                "ttl_hours": 24,
            }
            
            response = self.client.get("/cache/stats")
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertEqual(data["status"], "active")
            self.assertEqual(data["total_cached_items"], 5)


class TestAPIScrapeEndpoints(unittest.TestCase):
    """Test scraping endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch('src.api.scrape_data')
    def test_scrape_endpoint_200_end_to_end(self, mock_scrape_data):
        """Test scrape endpoint returns 200 with end-to-end flow validation."""
        mock_items = [
            DataItem(
                name="Lion",
                source="wikipedia",
                category="animals",
                image_url="https://example.com/lion.jpg",
                attributes={"collateral_adjective": "leonine"},
            ),
            DataItem(
                name="Tiger",
                source="wikipedia",
                category="animals",
                image_url="https://example.com/tiger.jpg",
                attributes={"collateral_adjective": "tigerine"},
            ),
        ]
        
        mock_response = ScrapingResponse(
            items=mock_items,
            total_count=2,
            source="wikipedia",
            category="animals",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={"original_count": 2, "limit_applied": True, "limit_value": 10},
        )
        mock_scrape_data.return_value = mock_response

        response = self.client.get("/scrape?source=wikipedia&category=animals&limit=10")
        
        # Validate 200 status and complete flow
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["source"], "wikipedia")
        self.assertEqual(data["category"], "animals")
        self.assertEqual(len(data["items"]), 2)
        
        # Validate item data integrity
        lion = data["items"][0]
        self.assertEqual(lion["name"], "Lion")
        self.assertEqual(lion["attributes"]["collateral_adjective"], "leonine")
        
        tiger = data["items"][1]
        self.assertEqual(tiger["name"], "Tiger")
        self.assertEqual(tiger["attributes"]["collateral_adjective"], "tigerine")

    def test_scrape_endpoint_400_invalid_params(self):
        """Test scrape endpoint returns 400 for invalid parameters."""
        response = self.client.get("/scrape?source=invalid&category=invalid")
        self.assertEqual(response.status_code, 400)

    @patch('src.api.scrape_data')
    def test_scrape_endpoint_200_with_limit(self, mock_scrape_data):
        """Test scrape endpoint returns 200 with limit functionality."""
        mock_items = [
            DataItem(name="Lion", source="wikipedia", category="animals"),
            DataItem(name="Tiger", source="wikipedia", category="animals"),
            DataItem(name="Elephant", source="wikipedia", category="animals"),
        ]
        
        mock_response = ScrapingResponse(
            items=mock_items[:2],  # Only first 2 items due to limit
            total_count=2,
            source="wikipedia",
            category="animals",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={"original_count": 3, "limit_applied": True, "limit_value": 2},
        )
        mock_scrape_data.return_value = mock_response

        response = self.client.get("/scrape?source=wikipedia&category=animals&limit=2")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["name"], "Lion")
        self.assertEqual(data["items"][1]["name"], "Tiger")

    @patch('src.api.scrape_data')
    def test_scrape_endpoint_200_with_offset(self, mock_scrape_data):
        """Test scrape endpoint returns 200 with offset functionality."""
        mock_items = [
            DataItem(name="Lion", source="wikipedia", category="animals"),
            DataItem(name="Tiger", source="wikipedia", category="animals"),
            DataItem(name="Elephant", source="wikipedia", category="animals"),
        ]
        
        mock_response = ScrapingResponse(
            items=mock_items[1:],  # Skip first item due to offset
            total_count=2,
            source="wikipedia",
            category="animals",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={"original_count": 3, "offset_applied": True, "offset_value": 1},
        )
        mock_scrape_data.return_value = mock_response

        response = self.client.get("/scrape?source=wikipedia&category=animals&offset=1")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["name"], "Tiger")
        self.assertEqual(data["items"][1]["name"], "Elephant")
