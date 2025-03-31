"""
Caching utilities for STB-ReStreamer.
Provides in-memory caching with TTL.
"""
import time
import logging
from threading import Lock
from typing import Dict, Any, Tuple, Optional

# Configure logger
logger = logging.getLogger("STB-Proxy")

class LinkCache:
    """
    Thread-safe cache for stream links and FFmpeg commands with TTL.
    """
    def __init__(self, max_size: int = 1000, default_ttl: int = 8):
        """
        Initialize the link cache.
        
        Args:
            max_size (int): Maximum number of items in cache
            default_ttl (int): Default TTL in hours
        """
        self.max_size = max_size
        self.default_ttl = default_ttl * 3600  # Convert to seconds
        self.lock = Lock()
        self.cache = {}  # Format: {key: (value, ffmpeg_cmd, expiry_time)}
        logger.info(f"Link cache initialized with size {max_size} and TTL {default_ttl} hours")
        
    def get(self, key: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get a cached item.
        
        Args:
            key (str): Cache key
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (value, ffmpeg_cmd) or (None, None) if not found or expired
        """
        with self.lock:
            if key in self.cache:
                value, ffmpeg_cmd, expiry_time = self.cache[key]
                
                # Check if expired
                if time.time() < expiry_time:
                    return value, ffmpeg_cmd
                else:
                    # Remove expired item
                    del self.cache[key]
                    
            return None, None
            
    def set(self, key: str, value: str, ffmpeg_cmd: Optional[str] = None, ttl: Optional[int] = None) -> None:
        """
        Set a cached item.
        
        Args:
            key (str): Cache key
            value (str): Value to cache
            ffmpeg_cmd (Optional[str]): FFmpeg command to cache
            ttl (Optional[int]): TTL in seconds, or None for default
        """
        with self.lock:
            # Clean up if at max size
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._cleanup()
                
            # Set TTL
            if ttl is None:
                ttl = self.default_ttl
                
            # Add to cache
            self.cache[key] = (value, ffmpeg_cmd, time.time() + ttl)
            
    def _cleanup(self) -> None:
        """
        Clean up expired items and remove oldest items if still at max size.
        """
        # Current time
        now = time.time()
        
        # Remove expired items
        expired = [k for k, (_, _, t) in self.cache.items() if now > t]
        for k in expired:
            del self.cache[k]
            
        # If still at max size, remove oldest items
        if len(self.cache) >= self.max_size:
            # Sort by expiry time
            items = list(self.cache.items())
            items.sort(key=lambda x: x[1][2])
            
            # Remove oldest items
            to_remove = len(self.cache) - self.max_size + 1
            for i in range(to_remove):
                if i < len(items):
                    del self.cache[items[i][0]]
                    
    def clear(self) -> None:
        """
        Clear the cache.
        """
        with self.lock:
            self.cache.clear()
            
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        with self.lock:
            # Count expired items
            now = time.time()
            expired = sum(1 for _, _, t in self.cache.values() if now > t)
            
            return {
                "total": len(self.cache),
                "expired": expired,
                "active": len(self.cache) - expired,
                "max_size": self.max_size
            }