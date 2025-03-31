"""
Secure token storage for STB-ReStreamer.
Handles encryption and secure storage of provider tokens.
"""
import os
import json
import time
import base64
import sqlite3
import logging
from threading import Lock
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

try:
    # Try to import cryptography for secure token storage
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

# Configure logger
logger = logging.getLogger("STB-Proxy")

class TokenStorage:
    """
    Secure storage for provider tokens.
    Uses encryption for sensitive data when possible.
    """
    
    def __init__(self, db_path: str = "tokens.db", encryption_key: Optional[str] = None):
        """
        Initialize the token storage.
        
        Args:
            db_path (str): Path to the SQLite database
            encryption_key (Optional[str]): Optional key for encryption. If not provided,
                                          a secure key will be generated and stored.
        """
        self.db_path = db_path
        self.lock = Lock()
        self.cipher_suite = None
        
        # Initialize encryption if available
        if CRYPTOGRAPHY_AVAILABLE:
            self._setup_encryption(encryption_key)
        else:
            logger.warning("Cryptography package not available. Tokens will be stored without encryption.")
            
        # Initialize database
        self._init_db()
        
        logger.info("Token storage initialized")
        
    def _setup_encryption(self, encryption_key: Optional[str] = None):
        """
        Set up encryption for token storage.
        
        Args:
            encryption_key (Optional[str]): Optional key for encryption
        """
        try:
            # If encryption key is provided, use it
            if encryption_key:
                key = self._derive_key(encryption_key.encode())
            else:
                # Check if we have a stored key
                key_path = Path(".encryption_key")
                if key_path.exists():
                    with open(key_path, "rb") as f:
                        key = f.read()
                else:
                    # Generate a new key
                    logger.info("Generating new encryption key")
                    key = Fernet.generate_key()
                    with open(key_path, "wb") as f:
                        f.write(key)
            
            # Create cipher suite
            self.cipher_suite = Fernet(key)
            logger.info("Encryption initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up encryption: {str(e)}")
            self.cipher_suite = None
    
    def _derive_key(self, password: bytes, salt: Optional[bytes] = None) -> bytes:
        """
        Derive a key from a password using PBKDF2.
        
        Args:
            password (bytes): Password to derive key from
            salt (Optional[bytes]): Salt for key derivation, generated if not provided
            
        Returns:
            bytes: Derived key
        """
        if salt is None:
            salt = os.urandom(16)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        # Derive a URL-safe base64-encoded key
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def _init_db(self):
        """Initialize the SQLite database for token storage."""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create tokens table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portal_id TEXT NOT NULL,
                    mac TEXT NOT NULL,
                    token TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    UNIQUE(portal_id, mac)
                )
                ''')
                
                # Create index for faster lookups
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_portal_mac ON tokens (portal_id, mac)')
                
                conn.commit()
                logger.info("Token database initialized")
                
        except Exception as e:
            logger.error(f"Error initializing token database: {str(e)}")
    
    def store_token(self, portal_id: str, mac: str, token: str, ttl: int = 12 * 3600) -> bool:
        """
        Securely store a token.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            token (str): Token to store
            ttl (int): Time to live in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            current_time = int(time.time())
            expires_at = current_time + ttl
            
            # Encrypt token if available
            encrypted_token = token
            if self.cipher_suite:
                encrypted_token = self.cipher_suite.encrypt(token.encode()).decode()
            
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert or replace token
                cursor.execute('''
                INSERT OR REPLACE INTO tokens (portal_id, mac, token, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ''', (portal_id, mac, encrypted_token, current_time, expires_at))
                
                conn.commit()
                logger.debug(f"Stored token for {portal_id}:{mac}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing token: {str(e)}")
            return False
    
    def get_token(self, portal_id: str, mac: str) -> Optional[str]:
        """
        Retrieve a token from storage.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            
        Returns:
            Optional[str]: Retrieved token or None if not found or expired
        """
        try:
            current_time = int(time.time())
            
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get token if not expired
                cursor.execute('''
                SELECT token, expires_at FROM tokens
                WHERE portal_id = ? AND mac = ? AND expires_at > ?
                ''', (portal_id, mac, current_time))
                
                result = cursor.fetchone()
                if not result:
                    return None
                    
                token, expires_at = result
                
                # Decrypt token if encrypted
                if self.cipher_suite:
                    try:
                        token = self.cipher_suite.decrypt(token.encode()).decode()
                    except Exception as e:
                        logger.error(f"Error decrypting token: {str(e)}")
                        return None
                
                logger.debug(f"Retrieved token for {portal_id}:{mac} (expires in {expires_at - current_time}s)")
                return token
                
        except Exception as e:
            logger.error(f"Error retrieving token: {str(e)}")
            return None
    
    def delete_token(self, portal_id: str, mac: str) -> bool:
        """
        Delete a token from storage.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            
        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete token
                cursor.execute('''
                DELETE FROM tokens
                WHERE portal_id = ? AND mac = ?
                ''', (portal_id, mac))
                
                conn.commit()
                affected = cursor.rowcount > 0
                
                if affected:
                    logger.debug(f"Deleted token for {portal_id}:{mac}")
                else:
                    logger.debug(f"No token found to delete for {portal_id}:{mac}")
                    
                return affected
                
        except Exception as e:
            logger.error(f"Error deleting token: {str(e)}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired tokens.
        
        Returns:
            int: Number of tokens deleted
        """
        try:
            current_time = int(time.time())
            
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete expired tokens
                cursor.execute('''
                DELETE FROM tokens
                WHERE expires_at <= ?
                ''', (current_time,))
                
                conn.commit()
                count = cursor.rowcount
                
                if count > 0:
                    logger.info(f"Cleaned up {count} expired tokens")
                    
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored tokens.
        
        Returns:
            Dict[str, Any]: Statistics about stored tokens
        """
        try:
            current_time = int(time.time())
            
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute('SELECT COUNT(*) FROM tokens')
                total = cursor.fetchone()[0]
                
                # Get active count
                cursor.execute('SELECT COUNT(*) FROM tokens WHERE expires_at > ?', (current_time,))
                active = cursor.fetchone()[0]
                
                # Get expired count
                cursor.execute('SELECT COUNT(*) FROM tokens WHERE expires_at <= ?', (current_time,))
                expired = cursor.fetchone()[0]
                
                # Get portals count
                cursor.execute('SELECT COUNT(DISTINCT portal_id) FROM tokens')
                portals = cursor.fetchone()[0]
                
                # Get MACs count
                cursor.execute('SELECT COUNT(DISTINCT mac) FROM tokens')
                macs = cursor.fetchone()[0]
                
                return {
                    'total': total,
                    'active': active,
                    'expired': expired,
                    'portals': portals,
                    'macs': macs,
                    'encrypted': self.cipher_suite is not None
                }
                
        except Exception as e:
            logger.error(f"Error getting token stats: {str(e)}")
            return {
                'total': 0,
                'active': 0,
                'expired': 0,
                'portals': 0,
                'macs': 0,
                'encrypted': self.cipher_suite is not None,
                'error': str(e)
            }
    
    def list_tokens(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        List all stored tokens.
        
        Args:
            active_only (bool): Only list active tokens
            
        Returns:
            List[Dict[str, Any]]: List of token information
        """
        try:
            current_time = int(time.time())
            
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if active_only:
                    cursor.execute('''
                    SELECT portal_id, mac, created_at, expires_at FROM tokens
                    WHERE expires_at > ?
                    ORDER BY expires_at DESC
                    ''', (current_time,))
                else:
                    cursor.execute('''
                    SELECT portal_id, mac, created_at, expires_at FROM tokens
                    ORDER BY expires_at DESC
                    ''')
                
                tokens = []
                for row in cursor.fetchall():
                    portal_id, mac, created_at, expires_at = row
                    tokens.append({
                        'portal_id': portal_id,
                        'mac': mac,
                        'created_at': created_at,
                        'expires_at': expires_at,
                        'ttl': max(0, expires_at - current_time),
                        'active': expires_at > current_time
                    })
                
                return tokens
                
        except Exception as e:
            logger.error(f"Error listing tokens: {str(e)}")
            return []