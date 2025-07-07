#!/usr/bin/env python3
"""
Tests for the Image Downloader API endpoints.
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.api import app
from src.models import (
    DownloadRequest, BatchDownloadRequest,
    DownloadResult, BatchDownloadResult
)


class TestAPIBasicEndpoints(unittest.TestCase):
    """Test basic API endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_root_endpoint_200(self):
        """Test root endpoint returns 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["service"], "Image Downloader Service")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("endpoints", data)

    def test_health_endpoint_200(self):
        """Test health endpoint returns 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "image-downloader")
        self.assertIn("capabilities", data)
        self.assertIn("threading", data["capabilities"])


class TestAPIDownloadEndpoints(unittest.TestCase):
    """Test download endpoints including error handling."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch('src.api.downloader.download_batch')
    def test_download_endpoint_200_batch_download(self, mock_download_batch):
        """Test download endpoint returns 200 with batch download."""
        # Mock successful download results
        mock_results = [
            DownloadResult(
                image_url="https://example.com/lion.jpg",
                target_path="/tmp/wikipedia_animals/lion.jpg",
                is_successful=True,
        file_size=12345,
        download_time=1.23
            ),
            DownloadResult(
                image_url="https://example.com/tiger.jpg",
                target_path="/tmp/wikipedia_animals/tiger.jpg",
                is_successful=True,
                file_size=15678,
                download_time=1.45
            )
        ]
        
        mock_batch_result = BatchDownloadResult(
            results=mock_results,
            total_count=2,
            success_count=2,
            failure_count=0,
            total_time=2.68,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        mock_download_batch.return_value = mock_batch_result

        # Test request
        request_data = {
            "downloads": [
                {
                    "image_url": "https://example.com/lion.jpg",
            "name": "Lion",
                    "source": "wikipedia",
                    "category": "animals"
                },
                {
                    "image_url": "https://example.com/tiger.jpg",
                    "name": "Tiger",
                    "source": "wikipedia",
                    "category": "animals"
                }
            ],
            "max_concurrent": 2,
            "timeout_seconds": 30
        }

        response = self.client.post("/download", json=request_data)
        
        # Validate 200 status and complete flow
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["success_count"], 2)
        self.assertEqual(data["failure_count"], 0)
        self.assertEqual(len(data["results"]), 2)

    def test_download_endpoint_400_empty_downloads(self):
        """Test download endpoint returns 400 for empty downloads."""
        request_data = {
            "downloads": [],
            "max_concurrent": 2,
            "timeout_seconds": 30
        }

        response = self.client.post("/download", json=request_data)
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn("No downloads specified", data["detail"])

    def test_download_endpoint_422_invalid_request(self):
        """Test download endpoint returns 422 for invalid request."""
        # Missing required fields
        request_data = {
            "downloads": [
                {
                    "name": "Lion"  # Missing image_url, source, category
                }
            ]
        }

        response = self.client.post("/download", json=request_data)
        self.assertEqual(response.status_code, 422)

    def test_download_endpoint_422_invalid_url_format(self):
        """Test download endpoint returns 422 for invalid URL format."""
        request_data = {
            "downloads": [
                {
                    "image_url": "not-a-valid-url",
                    "name": "Lion",
                    "source": "wikipedia",
                    "category": "animals"
                }
            ],
            "max_concurrent": 2,
            "timeout_seconds": 30
        }

        response = self.client.post("/download", json=request_data)
        self.assertEqual(response.status_code, 422)

    @patch('src.api.downloader.download_batch')
    def test_download_endpoint_500_downloader_exception(self, mock_download_batch):
        """Test download endpoint returns 500 when downloader raises exception."""
        mock_download_batch.side_effect = Exception("Downloader error")

        request_data = {
            "downloads": [
                {
                    "image_url": "https://example.com/lion.jpg",
                    "name": "Lion",
                    "source": "wikipedia",
                    "category": "animals"
                }
            ],
            "max_concurrent": 2,
            "timeout_seconds": 30
        }

        response = self.client.post("/download", json=request_data)
        self.assertEqual(response.status_code, 500)
        
        data = response.json()
        self.assertEqual(data["error"], "HTTP Error")
        self.assertIn("timestamp", data)
        self.assertIn("path", data)

    @patch('src.api.downloader.download_batch')
    def test_download_single_endpoint_200(self, mock_download_batch):
        """Test download-single endpoint returns 200."""
        # Mock successful single download
        mock_result = DownloadResult(
            image_url="https://example.com/lion.jpg",
            target_path="/tmp/wikipedia_animals/lion.jpg",
            is_successful=True,
        file_size=12345,
        download_time=1.23
    )
    
        mock_batch_result = BatchDownloadResult(
            results=[mock_result],
        total_count=1,
        success_count=1,
        failure_count=0,
        total_time=1.23,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        mock_download_batch.return_value = mock_batch_result

        # Test request
        request_data = {
            "image_url": "https://example.com/lion.jpg",
            "name": "Lion",
            "source": "wikipedia",
            "category": "animals"
        }

        response = self.client.post("/download-single", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["image_url"], "https://example.com/lion.jpg")
        self.assertTrue(data["is_successful"])

    @patch('src.api.downloader.download_batch')
    def test_download_single_endpoint_500_no_results(self, mock_download_batch):
        """Test download-single endpoint returns 500 when no results."""
        # Mock empty results
        mock_batch_result = BatchDownloadResult(
            results=[],
            total_count=0,
            success_count=0,
            failure_count=0,
            total_time=0.0,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        mock_download_batch.return_value = mock_batch_result

        request_data = {
            "image_url": "https://example.com/lion.jpg",
            "name": "Lion",
            "source": "wikipedia",
            "category": "animals"
        }

        response = self.client.post("/download-single", json=request_data)
        self.assertEqual(response.status_code, 500)
        
        data = response.json()
        self.assertIn("No result returned from download", data["detail"]) 