"""
Rate limiting utilities for STB-ReStreamer.
Provides token bucket rate limiting for API requests.
"""
import time
import logging
from threading import Lock
from typing import Dict, Tuple

# Configure logger
logger = logging.getLogger("STB-Proxy")

class RateLimiter:
    """
    Thread-safe token bucket rate limiter for API requests.
    """
    def __init__(self, rate: float = 5.0, capacity: int = 10):
        """
        Initialize the rate limiter.
        
        Args:
            rate (float): Token refill rate per second
            capacity (int): Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.lock = Lock()
        # Store buckets as {key: (tokens, last_refill_time)}
        self.buckets: Dict[str, Tuple[float, float]] = {}
        logger.info(f"Rate limiter initialized with rate {rate}/s and capacity {capacity}")
        
    def is_allowed(self, key: str) -> bool:
        """
        Check if a request is allowed based on rate limiting.
        Also consumes a token if allowed.
        
        Args:
            key (str): Rate limiting key (e.g., IP address, portal_id)
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        with self.lock:
            # Get or create bucket
            if key not in self.buckets:
                self.buckets[key] = (self.capacity, time.time())
                return True
                
            # Get bucket
            tokens, last_refill = self.buckets[key]
            
            # Calculate time since last refill
            now = time.time()
            time_since_refill = now - last_refill
            
            # Refill tokens
            new_tokens = tokens + time_since_refill * self.rate
            new_tokens = min(new_tokens, self.capacity)
            
            # Check if allowed
            if new_tokens < 1:
                # Update bucket with refilled tokens
                self.buckets[key] = (new_tokens, now)
                return False
                
            # Consume token
            new_tokens -= 1
            self.buckets[key] = (new_tokens, now)
            return True
            
    def get_retry_after(self, key: str) -> float:
        """
        Get the time in seconds to wait before retrying.
        
        Args:
            key (str): Rate limiting key
            
        Returns:
            float: Time in seconds to wait, or 0 if no wait needed
        """
        with self.lock:
            if key not in self.buckets:
                return 0
                
            tokens, last_refill = self.buckets[key]
            
            # If tokens available, no wait needed
            if tokens >= 1:
                return 0
                
            # Calculate wait time
            tokens_needed = 1 - tokens
            wait_time = tokens_needed / self.rate
            return max(0, wait_time)
            
    def reset(self, key: str = None) -> None:
        """
        Reset rate limiting for a key or for all keys.
        
        Args:
            key (str, optional): Key to reset, or None to reset all
        """
        with self.lock:
            if key is None:
                self.buckets.clear()
            elif key in self.buckets:
                self.buckets[key] = (self.capacity, time.time())
                
    def get_stats(self) -> Dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dict: Statistics about the rate limiter
        """
        with self.lock:
            now = time.time()
            stats = {
                "total_keys": len(self.buckets),
                "limited_keys": sum(1 for tokens, _ in self.buckets.values() if tokens < 1),
                "capacity": self.capacity,
                "rate": self.rate,
            }
            return stats