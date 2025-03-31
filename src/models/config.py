"""
Configuration management for STB-ReStreamer.
Handles loading, saving, and retrieving application settings.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from threading import Lock

# Configure logger
logger = logging.getLogger("STB-Proxy")

class ConfigManager:
    """
    Thread-safe manager for application configuration settings.
    """
    def __init__(self, filename: str = "config.json"):
        """
        Initialize the configuration manager.
        
        Args:
            filename (str): Path to the configuration file
        """
        self.filename = filename
        self.lock = Lock()
        self.config = {}
        self._load_config()
        logger.info(f"Config manager initialized with file: {filename}")
        
    def _load_config(self) -> None:
        """
        Load configuration from the configuration file.
        Create a default configuration if the file doesn't exist.
        """
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as file:
                    self.config = json.load(file)
            else:
                # Create default configuration
                self.config = {
                    "port": 8001,
                    "security": "false",
                    "username": "admin",
                    "password": "admin",
                    "cache size": 1000,
                    "cache ttl": 8,
                    "rate limit": 30,
                    "rate limit cleanup": 300,
                    "stream method": "ffmpeg",
                    "ffmpeg timeout": 5,
                    "test streams": "true",
                    "try all macs": "false",
                    "security": {
                        "encryption_key": "",
                        "token_lifetime": 12 * 3600,  # 12 hours in seconds
                        "secure_cookies": False
                    },
                    "paths": {
                        "data_dir": "data",
                        "logs_dir": "logs",
                        "plugins_dir": "plugins"
                    }
                }
                # Save default configuration
                self._save_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            # Use default configuration
            self.config = {
                "port": 8001,
                "security": "false",
                "paths": {
                    "data_dir": "data"
                }
            }
            
    def _save_config(self) -> None:
        """
        Save configuration to the configuration file.
        """
        try:
            with open(self.filename, 'w') as file:
                json.dump(self.config, file, indent=4)
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.
        
        Args:
            key (str): Setting key
            default (Any): Default value if key doesn't exist
            
        Returns:
            Any: Setting value or default
        """
        with self.lock:
            return self.config.get(key, default)
            
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            key (str): Setting key
            value (Any): Setting value
        """
        with self.lock:
            self.config[key] = value
            self._save_config()
            
    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary of all settings
        """
        with self.lock:
            return self.config.copy()
            
    def get(self, *keys, default: Any = None) -> Any:
        """
        Get a nested setting value by keys.
        
        Args:
            *keys: Sequence of keys to traverse nested dictionaries
            default (Any): Default value if path doesn't exist
            
        Returns:
            Any: Setting value or default
        """
        with self.lock:
            current = self.config
            for key in keys:
                if not isinstance(current, dict) or key not in current:
                    return default
                current = current[key]
            return current
            
    def set(self, *keys_and_value) -> None:
        """
        Set a nested setting value.
        
        Args:
            *keys_and_value: Sequence of keys followed by the value
        """
        if len(keys_and_value) < 2:
            raise ValueError("Must provide at least one key and a value")
            
        keys = keys_and_value[:-1]
        value = keys_and_value[-1]
        
        with self.lock:
            current = self.config
            for key in keys[:-1]:
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
            self._save_config()
            
    def get_data_dir(self) -> str:
        """
        Get the data directory path.
        
        Returns:
            str: Path to the data directory
        """
        data_dir = self.get("paths", "data_dir", default="data")
        
        # Create the directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        return data_dir