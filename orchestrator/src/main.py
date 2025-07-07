#!/usr/bin/env python3
"""
Main entry point for the orchestrator CLI.
"""

import os
from cli import CLI

if __name__ == "__main__":
    # Get service URLs from environment variables with defaults
    data_scraper_url = os.getenv('DATA_SCRAPER_URL', 'http://data-scraper-service:9001')
    image_downloader_url = os.getenv('IMAGE_DOWNLOADER_URL', 'http://image-downloader:9002')
    
    cli = CLI(
        data_scraper_url=data_scraper_url,
        image_downloader_url=image_downloader_url
    )
    cli.run() 