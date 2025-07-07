#!/usr/bin/env python3
"""
Simplified service client for orchestrator.
"""

import os
import requests
from typing import List, Dict
from collections import defaultdict


class ServiceClient:
    def __init__(self, data_scraper_url: str, image_downloader_url: str):
        self.data_scraper_url = data_scraper_url
        self.image_downloader_url = image_downloader_url
    
    def check_services_health(self) -> bool:
        """Check if all services are healthy."""
        print("🔍 Checking service health...")
        
        scraper_healthy = self._check_service_health(self.data_scraper_url)
        downloader_healthy = self._check_service_health(self.image_downloader_url)
        
        if scraper_healthy:
            print("✅ Data Scraper Service is healthy")
        else:
            print("❌ Data Scraper Service is not responding")
        
        if downloader_healthy:
            print("✅ Image Downloader Service is healthy")
        else:
            print("❌ Image Downloader Service is not responding")
        
        return scraper_healthy and downloader_healthy
    
    def _check_service_health(self, url: str) -> bool:
        """Check if a service is healthy."""
        try:
            response = requests.get(f"{url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def scrape_data(self, source: str, category: str) -> List[Dict]:
        """Scrape data from the data scraper service."""
        print(f"📊 Scraping {category} from {source}...")
        
        try:
            params = {
                'source': source,
                'category': category
            }
            response = requests.get(f"{self.data_scraper_url}/scrape", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            print(f"✅ Found {len(items)} {category}")
            
            # Log animals grouped by collateral adjectives
            adjective_groups = defaultdict(list)
            for item in items:
                animal_name = item.get('name', 'Unknown')
                collateral_adj = item.get('attributes', {}).get('collateral_adjective', '')
                if collateral_adj.strip():
                    adjective_groups[collateral_adj].append(animal_name)
            
            print(f"📋 Animals grouped by collateral adjectives:")
            for adj, animals in sorted(adjective_groups.items()):
                print(f"   {adj}: {', '.join(animals)}")
            
            return items
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error scraping data: {e}")
            raise
    
    def download_images(self, items: List[Dict]) -> None:
        """Download images using the image downloader service."""
        if not items:
            print("⏭️  No images to download")
            return
        
        print(f"🖼️  Downloading {len(items)} images...")
        
        try:
            downloads = []
            for item in items:
                downloads.append({
                    'image_url': item['image_url'],
                    'name': item['name'],
                    'source': item.get('source', 'wikipedia'),
                    'category': item.get('category', 'animals')
                })
            
            request_data = {
                'downloads': downloads,
                'max_concurrent': 15,
                'timeout_seconds': 30
            }
            
            response = requests.post(f"{self.image_downloader_url}/download", 
                                   json=request_data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            success_count = result.get('success_count', 0)
            failure_count = result.get('failure_count', 0)
            
            print(f"✅ Downloaded {success_count} images successfully")
            if failure_count > 0:
                print(f"⚠️  {failure_count} downloads failed")
            
        except Exception as e:
            print(f"❌ Error downloading images: {e}")
            raise 