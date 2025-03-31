"""
Authentication utilities for STB-ReStreamer.
Provides basic authentication for web UI access.
"""
import os
import time
import logging
import hashlib
import secrets
from threading import Lock
from typing import Dict, Optional, Tuple, List

# Configure logger
logger = logging.getLogger("STB-Proxy")

class AuthManager:
    """
    Thread-safe authentication manager for web UI access.
    """
    def __init__(self, config_manager):
        """
        Initialize the authentication manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.lock = Lock()
        self.sessions: Dict[str, Dict] = {}  # Format: {token: {username, expiry}}
        self.failed_attempts: Dict[str, List[float]] = {}  # Format: {ip: [timestamps]}
        self.session_lifetime = 24 * 3600  # 24 hours in seconds
        self.max_failed_attempts = 5
        self.lockout_duration = 15 * 60  # 15 minutes in seconds
        logger.info("Authentication manager initialized")
        
    def login(self, username: str, password: str, ip: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Authenticate a user and generate a session token.
        
        Args:
            username (str): Username
            password (str): Password
            ip (str): Client IP address
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, token, error_message)
        """
        with self.lock:
            # Check if IP is locked out due to too many failed attempts
            if self._is_ip_locked(ip):
                logger.warning(f"Login attempt from locked IP: {ip}")
                remaining = self._get_lockout_remaining(ip)
                return False, None, f"Too many failed attempts. Try again in {int(remaining / 60)} minutes."
                
            # Get UI credentials from config - using get_setting() instead of get()
            admin_username = self.config_manager.get_setting("admin_username", "admin")
            admin_password = self.config_manager.get_setting("admin_password", "admin")
            
            # Verify credentials
            if username != admin_username or password != admin_password:
                # Record failed attempt
                self._record_failed_attempt(ip)
                
                # Check if this attempt caused a lockout
                if self._is_ip_locked(ip):
                    logger.warning(f"IP locked out after failed login attempts: {ip}")
                    remaining = self._get_lockout_remaining(ip)
                    return False, None, f"Too many failed attempts. Try again in {int(remaining / 60)} minutes."
                    
                logger.warning(f"Failed login attempt for user {username} from {ip}")
                return False, None, "Invalid username or password"
                
            # Generate token
            token = secrets.token_hex(32)
            expiry = time.time() + self.session_lifetime
            
            # Store session
            self.sessions[token] = {
                "username": username,
                "expiry": expiry,
                "ip": ip
            }
            
            # Clear failed attempts for this IP
            if ip in self.failed_attempts:
                del self.failed_attempts[ip]
                
            logger.info(f"User {username} logged in successfully from {ip}")
            return True, token, None
            
    def validate_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a session token.
        
        Args:
            token (str): Session token
            
        Returns:
            Tuple[bool, Optional[str]]: (valid, username)
        """
        with self.lock:
            if token not in self.sessions:
                return False, None
                
            session = self.sessions[token]
            
            # Check if expired
            if time.time() > session["expiry"]:
                del self.sessions[token]
                return False, None
                
            return True, session["username"]
            
    def logout(self, token: str) -> bool:
        """
        Invalidate a session token.
        
        Args:
            token (str): Session token
            
        Returns:
            bool: True if token was found and invalidated, False otherwise
        """
        with self.lock:
            if token in self.sessions:
                del self.sessions[token]
                return True
            return False
            
    def _record_failed_attempt(self, ip: str) -> None:
        """
        Record a failed login attempt.
        
        Args:
            ip (str): Client IP address
        """
        now = time.time()
        
        if ip not in self.failed_attempts:
            self.failed_attempts[ip] = []
            
        # Add current attempt
        self.failed_attempts[ip].append(now)
        
        # Remove attempts older than lockout duration
        self.failed_attempts[ip] = [
            t for t in self.failed_attempts[ip]
            if now - t < self.lockout_duration
        ]
        
    def _is_ip_locked(self, ip: str) -> bool:
        """
        Check if an IP is locked out due to too many failed attempts.
        
        Args:
            ip (str): Client IP address
            
        Returns:
            bool: True if IP is locked out, False otherwise
        """
        if ip not in self.failed_attempts:
            return False
            
        # Clean up old attempts
        now = time.time()
        self.failed_attempts[ip] = [
            t for t in self.failed_attempts[ip]
            if now - t < self.lockout_duration
        ]
        
        # Check if there are too many recent attempts
        return len(self.failed_attempts[ip]) >= self.max_failed_attempts
        
    def _get_lockout_remaining(self, ip: str) -> float:
        """
        Get the remaining lockout time for an IP.
        
        Args:
            ip (str): Client IP address
            
        Returns:
            float: Remaining lockout time in seconds
        """
        if ip not in self.failed_attempts or not self.failed_attempts[ip]:
            return 0
            
        now = time.time()
        oldest_relevant = min(t for t in self.failed_attempts[ip])
        return max(0, oldest_relevant + self.lockout_duration - now)
        
    def cleanup_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            int: Number of sessions removed
        """
        with self.lock:
            now = time.time()
            expired = [token for token, session in self.sessions.items() 
                      if session["expiry"] < now]
                      
            for token in expired:
                del self.sessions[token]
                
            return len(expired)
            
    def get_stats(self) -> Dict:
        """
        Get authentication statistics.
        
        Returns:
            Dict: Statistics about authentication
        """
        with self.lock:
            now = time.time()
            active_sessions = sum(1 for session in self.sessions.values() 
                               if session["expiry"] > now)
            
            locked_ips = sum(1 for ip, attempts in self.failed_attempts.items()
                          if len(attempts) >= self.max_failed_attempts)
                          
            return {
                "active_sessions": active_sessions,
                "total_sessions": len(self.sessions),
                "locked_ips": locked_ips,
                "session_lifetime_hours": self.session_lifetime / 3600
            }