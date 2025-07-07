"""
Common library for source and category validation across all services.
This module provides centralized validation logic for data sources and categories.
"""

from typing import Dict, Set


# Supported sources and their categories
SupportedSources: Dict[str, Set[str]] = {
    "wikipedia": {"animals"},
    # Add more sources/categories as needed
}


class SourceValidator:
    """Validator for data sources and categories."""
    
    @classmethod
    def validate(cls, source: str, category: str) -> None:
        """
        Validate source and category combination.
        
        Args:
            source: Data source (e.g., "wikipedia")
            category: Data category (e.g., "animals")
            
        Raises:
            ValueError: If source or category is not supported
        """
        if source not in SupportedSources:
            raise ValueError(f"Invalid source: {source}. Available sources: {list(SupportedSources.keys())}")
        
        if category not in SupportedSources[source]:
            raise ValueError(f"Invalid category '{category}' for source '{source}'. Available categories: {list(SupportedSources[source])}")
    
    @classmethod
    def get_supported_sources(cls) -> Dict[str, Set[str]]:
        """
        Get all supported sources and their categories.
        
        Returns:
            Dictionary mapping sources to their supported categories
        """
        return SupportedSources 