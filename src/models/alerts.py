"""
Alert management for STB-ReStreamer.
Handles storage and retrieval of system alerts.
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional
from threading import Lock

# Configure logger
logger = logging.getLogger("STB-Proxy")

class AlertManager:
    """
    Thread-safe manager for system alerts with persistence.
    """
    def __init__(self, filename: str = "alerts.json"):
        """
        Initialize the alert manager.
        
        Args:
            filename (str): Path to the alerts storage file
        """
        self.filename = filename
        self.lock = Lock()
        self.alerts = []
        self._load_alerts()
        logger.info(f"Alert manager initialized with file: {filename}")
        
    def _load_alerts(self) -> None:
        """
        Load alerts from the storage file.
        """
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as file:
                    self.alerts = json.load(file)
        except Exception as e:
            logger.error(f"Error loading alerts: {str(e)}")
            self.alerts = []
            
    def _save_alerts(self) -> None:
        """
        Save alerts to the storage file.
        """
        try:
            with open(self.filename, 'w') as file:
                json.dump(self.alerts, file, indent=4)
        except Exception as e:
            logger.error(f"Error saving alerts: {str(e)}")
            
    def add_alert(self, level: str, title: str, message: str) -> None:
        """
        Add a new alert.
        
        Args:
            level (str): Alert level (info, warning, error)
            title (str): Alert title
            message (str): Alert message
        """
        with self.lock:
            alert = {
                "id": int(time.time() * 1000),
                "timestamp": int(time.time()),
                "level": level,
                "title": title,
                "message": message
            }
            
            self.alerts.append(alert)
            
            # Trim alerts to max 100
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]
                
            self._save_alerts()
            
    def get_alerts(self, limit: Optional[int] = None, level: Optional[str] = None) -> List[Dict]:
        """
        Get alerts, optionally filtered by level.
        
        Args:
            limit (Optional[int]): Maximum number of alerts to return
            level (Optional[str]): Filter by alert level
            
        Returns:
            List[Dict]: List of alert dictionaries
        """
        with self.lock:
            if level:
                filtered = [a for a in self.alerts if a.get("level") == level]
            else:
                filtered = self.alerts.copy()
                
            # Sort by timestamp (newest first)
            filtered.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            
            if limit and limit > 0:
                return filtered[:limit]
            return filtered