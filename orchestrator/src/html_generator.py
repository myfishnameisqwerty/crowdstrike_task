#!/usr/bin/env python3
"""
HTML Generator for orchestrator.
"""

import os
from typing import List, Dict
from collections import defaultdict


class HTMLGenerator:
    def __init__(self, output_path: str = "/tmp"):
        self.output_path = output_path
    
    def generate_html(self, source: str, category: str, items: List[Dict]) -> str:
        print("📄 Generating HTML output...")
        
        # Group items by collateral adjective (category) instead of animal name
        adjective_groups = defaultdict(list)
        for item in items:
            animal_name = item.get('name', 'Unknown')
            collateral_adj = item.get('attributes', {}).get('collateral_adjective', '')
            if collateral_adj.strip():  # Only include items with valid collateral adjectives
                adjective_groups[collateral_adj].append(animal_name)
        
        print(f"📊 Grouped {len(items)} items into {len(adjective_groups)} unique collateral adjectives")
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{category.title()} Collateral Adjectives from {source.title()}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; margin-bottom: 30px; }}
        .adjective-section {{ margin-bottom: 40px; border: 1px solid #ddd; border-radius: 8px; padding: 20px; background-color: white; }}
        .adjective-title {{ font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 20px; text-transform: capitalize; text-align: center; }}
        .images-row {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 15px; }}
        .animal-image {{ width: 120px; height: 120px; object-fit: cover; border-radius: 8px; border: 2px solid #ddd; }}
        .missing-image {{ width: 120px; height: 120px; background-color: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6c757d; font-size: 12px; text-align: center; }}
        .names-row {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }}
        .animal-name {{ 
            background-color: #ecf0f1; 
            padding: 4px 12px; 
            border-radius: 15px; 
            font-size: 14px;
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{category.title()} Collateral Adjectives</h1>
"""
        
        for collateral_adj, animal_names in sorted(adjective_groups.items()):
            html_content += f"""
        <div class="adjective-section">
            <div class="adjective-title">{collateral_adj}</div>
            <div class="images-row">
"""
            
            # Add images for all animals in this group
            for animal_name in animal_names:
                # Try different file extensions since downloader saves with correct extensions
                possible_extensions = ['.jpg', '.jpeg', '.png', '.gif']
                local_path = None
                
                for ext in possible_extensions:
                    filename = f"{animal_name.lower().replace(' ', '_')}{ext}"
                    test_path = f"/tmp/{source}_{category}/{filename}"
                    if os.path.exists(test_path) and os.path.getsize(test_path) > 0:
                        local_path = test_path
                        break
                
                if local_path:
                    html_content += f'                <img src="file://{local_path}" alt="{animal_name}" class="animal-image" />\n'
                else:
                    html_content += f'                <div class="missing-image">No Image<br/>{animal_name}</div>\n'
            
            html_content += f"""
            </div>
            <div class="names-row">
"""
            
            # Add names for all animals in this group
            for animal_name in animal_names:
                html_content += f'                <span class="animal-name">{animal_name}</span>\n'
            
            html_content += f"""
            </div>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        output_file = os.path.join(self.output_path, f"{source}_{category}_gallery.html")
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"✅ HTML generated: {output_file}")
        print(f"📊 HTML Summary: {len(adjective_groups)} unique collateral adjectives with animals")
        return output_file 