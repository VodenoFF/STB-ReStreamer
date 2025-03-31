"""
Portal management for STB-ReStreamer.
Handles IPTV portal configurations.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from threading import Lock

# Configure logger
logger = logging.getLogger("STB-Proxy")

class PortalManager:
    """
    Thread-safe manager for IPTV portal configurations.
    """
    def __init__(self, filename: str = "portals.json"):
        """
        Initialize the portal manager.
        
        Args:
            filename (str): Path to the portals storage file
        """
        self.filename = filename
        self.lock = Lock()
        self.portals = {}
        self._load_portals()
        logger.info(f"Portal manager initialized with file: {filename}")
        
    def _load_portals(self) -> None:
        """
        Load portals from the storage file.
        """
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as file:
                    self.portals = json.load(file)
        except Exception as e:
            logger.error(f"Error loading portals: {str(e)}")
            self.portals = {}
            
    def _save_portals(self) -> None:
        """
        Save portals to the storage file.
        """
        try:
            with open(self.filename, 'w') as file:
                json.dump(self.portals, file, indent=4)
        except Exception as e:
            logger.error(f"Error saving portals: {str(e)}")
            
    def get_portal(self, portal_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a portal by ID.
        
        Args:
            portal_id (str): Portal ID
            
        Returns:
            Optional[Dict[str, Any]]: Portal configuration or None if not found
        """
        with self.lock:
            return self.portals.get(portal_id)
            
    def get_all_portals(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all portals.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of all portals
        """
        with self.lock:
            return self.portals.copy()
            
    def get_enabled_portals(self) -> Dict[str, Dict[str, Any]]:
        """
        Get only enabled portals.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of enabled portals
        """
        with self.lock:
            enabled_portals = {}
            for k, v in self.portals.items():
                # Handle different ways 'enabled' might be stored:
                # - Boolean true
                # - String "true" (case insensitive)
                # - String "1"
                # - String "yes" (case insensitive)
                enabled_value = v.get("enabled")
                
                is_enabled = False
                if isinstance(enabled_value, bool):
                    is_enabled = enabled_value
                elif isinstance(enabled_value, str):
                    is_enabled = enabled_value.lower() in ["true", "1", "yes"]
                
                if is_enabled:
                    enabled_portals[k] = v
            
            logger.debug(f"Found {len(enabled_portals)} enabled portals out of {len(self.portals)} total")
            return enabled_portals
            
    def add_portal(self, portal_id: str, portal_data: Dict[str, Any]) -> None:
        """
        Add or update a portal.
        
        Args:
            portal_id (str): Portal ID
            portal_data (Dict[str, Any]): Portal configuration
        """
        with self.lock:
            self.portals[portal_id] = portal_data
            self._save_portals()
            
    def delete_portal(self, portal_id: str) -> bool:
        """
        Delete a portal.
        
        Args:
            portal_id (str): Portal ID
            
        Returns:
            bool: True if portal was deleted, False if not found
        """
        with self.lock:
            if portal_id in self.portals:
                del self.portals[portal_id]
                self._save_portals()
                return True
            return False
            
    def move_mac(self, portal_id: str, mac: str) -> bool:
        """
        Move a MAC address to the end of the rotation list.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.lock:
            if portal_id in self.portals and mac in self.portals[portal_id].get("macs", {}):
                # Get MAC data
                mac_data = self.portals[portal_id]["macs"][mac]
                
                # Remove and re-add to put at the end
                del self.portals[portal_id]["macs"][mac]
                self.portals[portal_id]["macs"][mac] = mac_data
                
                self._save_portals()
                return True
            return False