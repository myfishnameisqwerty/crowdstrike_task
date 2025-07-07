import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import threading

# Configure logging
logger = logging.getLogger(__name__)


class ImageCache:
    """In-memory cache for image URLs to avoid repeated extraction."""

    def __init__(self, ttl_hours: int = 24):
        """
        Initialize the image cache.

        Args:
            ttl_hours: Time to live for cached entries in hours
        """
        self.ttl_seconds = ttl_hours * 3600
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        logger.info(f"Initialized in-memory image cache with {ttl_hours}h TTL")

    def _get_cache_key(self, category: str, item_name: str) -> str:
        """Generate cache key for an item."""
        return f"{category}:{item_name.lower()}"

    def _is_expired(self, cached_at: str) -> bool:
        """Check if a cached entry has expired."""
        try:
            cached_time = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
            current_time = datetime.now(timezone.utc)
            age_seconds = (current_time - cached_time).total_seconds()
            return age_seconds > self.ttl_seconds
        except Exception as e:
            logger.warning(f"Error checking cache expiration: {e}")
            return True  # Treat as expired if we can't parse the timestamp

    def get_image_url(self, category: str, item_name: str) -> Optional[str]:
        """
        Get cached image URL for an item.

        Args:
            category: Category of data (e.g., animals)
            item_name: Name of the item (e.g., "Lion")

        Returns:
            Cached image URL or None if not found or expired
        """
        with self._lock:
            cache_key = self._get_cache_key(category, item_name)
            cached_data = self._cache.get(cache_key)

            if cached_data:
                # Check if expired
                if self._is_expired(cached_data["cached_at"]):
                    logger.debug(f"Cache expired for {item_name}")
                    del self._cache[cache_key]
                    return None

                logger.debug(f"Cache hit for {item_name}: {cached_data['url']}")
                return cached_data["url"]

            logger.debug(f"Cache miss for {item_name}")
            return None

    def set_image_url(
        self,
        category: str,
        item_name: str,
        image_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Cache image URL for an item.

        Args:
            category: Category of data (e.g., animals)
            item_name: Name of the item (e.g., "Lion")
            image_url: URL of the image
            metadata: Additional metadata to store
        """
        with self._lock:
            cache_key = self._get_cache_key(category, item_name)
            cache_data = {
                "url": image_url,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }

            self._cache[cache_key] = cache_data
            logger.debug(f"Cached image URL for {item_name}: {image_url}")

    def has_changed(self, category: str, item_name: str, new_url: str) -> bool:
        """
        Check if image URL has changed for an item.

        Args:
            category: Category of data (e.g., animals)
            item_name: Name of the item (e.g., "Lion")
            new_url: New image URL to compare

        Returns:
            True if URL has changed or doesn't exist, False if same
        """
        cached_url = self.get_image_url(category, item_name)
        return cached_url != new_url

    def clear_by_category(self, category: Optional[str] = None) -> int:
        """
        Clear cache entries by category.

        Args:
            category: If specified, clear only entries for this category

        Returns:
            Number of entries cleared
        """
        with self._lock:
            if category:
                # Clear entries for specific category
                keys_to_remove = [
                    key for key in self._cache.keys() if key.startswith(f"{category}:")
                ]
                for key in keys_to_remove:
                    del self._cache[key]
                logger.info(
                    f"Cleared {len(keys_to_remove)} cache entries for category: {category}"
                )
                return len(keys_to_remove)
            else:
                # Clear all entries
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Cleared all {count} cache entries")
                return count

    def clear_by_source_category(self, source: str, category: str) -> int:
        """
        Clear cache entries for a specific source:category combination.
        
        Args:
            source: Source name (e.g., wikipedia)
            category: Category name (e.g., animals)
            
        Returns:
            Number of entries cleared
        """
        # For now, we only cache by category, so this is equivalent to clear_by_category
        # In the future, we could extend the cache key to include source
        return self.clear_by_category(category)

    def clear_all(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        return self.clear_by_category()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            # Clean up expired entries first
            expired_keys = []
            for key, data in self._cache.items():
                if self._is_expired(data["cached_at"]):
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return {
                "status": "active",
                "total_cached_items": len(self._cache),
                "ttl_hours": self.ttl_seconds // 3600,
                "expired_cleaned": len(expired_keys),
            }

    def get_cache_keys(self) -> list:
        """Get all cache keys (for debugging)."""
        with self._lock:
            return list(self._cache.keys())


# Global cache instance
image_cache = ImageCache()
