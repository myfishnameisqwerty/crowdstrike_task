#!/usr/bin/env python3
"""
Tests for threading-based image downloader.
"""

import os
import pytest
from src.downloader import ImageDownloader
from src.models import DownloadRequest, BatchDownloadRequest
from pydantic import ValidationError

def test_basic_downloader_initialization():
    """Test that the downloader can be initialized."""
    downloader = ImageDownloader(max_workers=5)
    assert downloader is not None
    assert downloader.max_workers == 5

def test_downloader_with_default_workers():
    """Test downloader with default worker count."""
    downloader = ImageDownloader()
    assert downloader.max_workers == 15

def test_single_image_download_to_tmp():
    """Test downloading a single image to /tmp."""
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Short_tailed_Albatross1.jpg/330px-Short_tailed_Albatross1.jpg"
    name = "Albatross"
    source = "wikipedia"
    category = "animals"
    target_path = f"/tmp/{source}_{category}/{name.lower().replace(' ', '_')}.jpg"
    
    # Clean up any existing file
    if os.path.exists(target_path):
        os.remove(target_path)
    
    download_request = DownloadRequest(
        image_url=image_url,
        name=name,
        source=source,
        category=category
    )
    batch_request = BatchDownloadRequest(downloads=[download_request])
    downloader = ImageDownloader(max_workers=1)
    result = downloader.download_batch(batch_request)
    
    assert result.success_count == 1
    assert result.failure_count == 0
    assert os.path.exists(target_path)
    file_size = os.path.getsize(target_path)
    assert file_size > 0
    
    # Clean up
    os.remove(target_path)

def test_batch_download_with_models():
    """Test batch download with multiple images."""
    requests = [
        DownloadRequest(
            image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Short_tailed_Albatross1.jpg/330px-Short_tailed_Albatross1.jpg",
            name="Albatross",
            source="wikipedia",
            category="animals"
        ),
        DownloadRequest(
            image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Alpaca_%2831562329701%29.jpg/250px-Alpaca_%2831562329701%29.jpg",
            name="Alpaca",
            source="wikipedia",
            category="animals"
        )
    ]
    batch_request = BatchDownloadRequest(
        downloads=requests,
        max_concurrent=2,
        timeout_seconds=30
    )
    downloader = ImageDownloader(max_workers=2)
    result = downloader.download_batch(batch_request)
    
    assert result.success_count == 2
    
    # Check files were created
    for req in requests:
        expected_filename = f"{req.name.lower().replace(' ', '_')}.jpg"
        file_path = f"/tmp/{req.source}_{req.category}/{expected_filename}"
        assert os.path.exists(file_path)
        file_size = os.path.getsize(file_path)
        assert file_size > 0
        os.remove(file_path)

def test_concurrent_download_limits():
    """Test that concurrent download limits work correctly."""
    requests = [
        DownloadRequest(
            image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Short_tailed_Albatross1.jpg/330px-Short_tailed_Albatross1.jpg",
            name=f"TestImage_{i}",
            source="wikipedia",
            category="animals"
        )
        for i in range(3)
    ]
    
    batch_request = BatchDownloadRequest(
        downloads=requests,
        max_concurrent=2,
        timeout_seconds=30
    )
    downloader = ImageDownloader(max_workers=2)
    result = downloader.download_batch(batch_request)
    
    assert result.success_count > 0
    
    # Clean up
    for req in requests:
        file_path = f"/tmp/{req.source}_{req.category}/{req.name.lower().replace(' ', '_')}.jpg"
        if os.path.exists(file_path):
            os.remove(file_path)

def test_download_error_handling():
    """Test error handling for invalid URLs."""
    # Test with invalid URL that will fail
    invalid_request = DownloadRequest(
        image_url="https://invalid-domain-that-does-not-exist-12345.com/image.jpg",
        name="InvalidImage",
        source="wikipedia",
        category="animals"
    )
    
    batch_request = BatchDownloadRequest(
        downloads=[invalid_request],
        max_concurrent=1,
        timeout_seconds=5
    )
    downloader = ImageDownloader(max_workers=1)
    result = downloader.download_batch(batch_request)
    
    assert result.success_count == 0
    assert result.failure_count == 1
    assert not result.results[0].is_successful
    assert result.results[0].error_message


