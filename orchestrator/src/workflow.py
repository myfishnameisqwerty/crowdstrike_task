#!/usr/bin/env python3
"""
Simple workflow logic for orchestrator.
"""

import os
from typing import List, Dict
from services import ServiceClient
from html_generator import HTMLGenerator


class Workflow:
    def __init__(self, data_scraper_url: str, image_downloader_url: str):
        self.service_client = ServiceClient(data_scraper_url, image_downloader_url)
        self.html_generator = HTMLGenerator()
        self._is_running = False
    
    def is_running(self) -> bool:
        return self._is_running
    
    def run(self, trigger: str) -> dict:
        """Run a complete workflow for the given trigger."""
        if self._is_running:
            return {"status": "error", "message": "Workflow already running"}
        
        try:
            self._is_running = True
            print(f"🚀 Starting workflow for trigger: {trigger}")
            
            # Parse trigger
            source, category = self._parse_trigger(trigger)
            
            # Check service health
            if not self.service_client.check_services_health():
                return {"status": "error", "message": "Services not healthy"}
            
            # Scrape data
            items = self.service_client.scrape_data(source, category)
            if not items:
                return {"status": "error", "message": "No data found"}
            
            # Check existing images and download new ones
            items_to_download = self._check_existing_images(source, category, items)
            if items_to_download:
                self.service_client.download_images(items_to_download)
            
            # Generate HTML
            html_file = self.html_generator.generate_html(source, category, items)
            
            print(f"🎉 Workflow completed successfully!")
            print(f"📄 HTML output: {html_file}")
            
            return {
                "status": "success", 
                "html_file": os.path.basename(html_file),
                "html_url": f"http://localhost:9003/html/{os.path.basename(html_file)}"
            }
            
        except ValueError as e:
            return {"status": "error", "message": f"Invalid trigger: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Workflow failed: {e}"}
        finally:
            self._is_running = False
    
    def _parse_trigger(self, trigger: str) -> tuple[str, str]:
        """Parse trigger into source and category."""
        if '-' not in trigger:
            raise ValueError(f"Invalid trigger format: {trigger}. Expected format: {{source}}-{{category}}")
        
        source, category = trigger.split('-', 1)
        return source, category
    
    def _check_existing_images(self, source: str, category: str, items: List[Dict]) -> List[Dict]:
        """Check which images already exist and return items that need downloading."""
        print("🔍 Checking existing images...")
        
        base_path = f"/tmp/{source}_{category}"
        items_to_download = []
        
        for item in items:
            image_url = item.get('image_url')
            name = item.get('name', 'unknown')
            
            if not image_url:
                continue
            
            # Check for different file extensions
            possible_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            exists = False
            
            for ext in possible_extensions:
                filename = f"{name.lower().replace(' ', '_')}{ext}"
                file_path = f"{base_path}/{filename}"
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    print(f"  ⏭️  Skipping {name} - image already exists")
                    exists = True
                    break
            
            if not exists:
                print(f"  📥 Will download {name}")
                items_to_download.append(item)
        
        print(f"✅ {len(items_to_download)} images need downloading")
        return items_to_download 