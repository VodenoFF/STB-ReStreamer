"""
Channel group management for STB-ReStreamer.
Handles channel group configurations for improved organization.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from threading import Lock

# Configure logger
logger = logging.getLogger("STB-Proxy")

class ChannelGroupManager:
    """
    Thread-safe manager for channel group configurations.
    """
    def __init__(self, filename: str = "channel_groups.json"):
        """
        Initialize the channel group manager.
        
        Args:
            filename (str): Path to the channel groups storage file
        """
        self.filename = filename
        self.lock = Lock()
        self.groups = {}
        self._load_groups()
        logger.info(f"Channel group manager initialized with file: {filename}")
        
    def _load_groups(self) -> None:
        """
        Load channel groups from the storage file.
        """
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as file:
                    self.groups = json.load(file)
        except Exception as e:
            logger.error(f"Error loading channel groups: {str(e)}")
            self.groups = {}
            
    def _save_groups(self) -> None:
        """
        Save channel groups to the storage file.
        """
        try:
            with open(self.filename, 'w') as file:
                json.dump(self.groups, file, indent=4)
        except Exception as e:
            logger.error(f"Error saving channel groups: {str(e)}")
            
    def get_group(self, group_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a channel group by name.
        
        Args:
            group_name (str): Group name
            
        Returns:
            Optional[Dict[str, Any]]: Group configuration or None if not found
        """
        with self.lock:
            return self.groups.get(group_name)
            
    def get_all_groups(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all channel groups.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of all channel groups
        """
        with self.lock:
            return self.groups.copy()
            
    def get_sorted_groups(self) -> List[Dict[str, Any]]:
        """
        Get all channel groups sorted by priority.
        
        Returns:
            List[Dict[str, Any]]: List of channel groups with name and data
        """
        with self.lock:
            # Create list of (name, group) tuples
            groups_list = [(name, group) for name, group in self.groups.items()]
            
            # Sort by priority (higher priority first)
            groups_list.sort(key=lambda x: int(x[1].get("priority", 0)), reverse=True)
            
            # Transform to list of dictionaries with name and data
            return [{"name": name, "data": group} for name, group in groups_list]
            
    def add_group(self, group_name: str, group_data: Dict[str, Any]) -> None:
        """
        Add or update a channel group.
        
        Args:
            group_name (str): Group name
            group_data (Dict[str, Any]): Group configuration
        """
        with self.lock:
            self.groups[group_name] = group_data
            self._save_groups()
            
    def delete_group(self, group_name: str) -> bool:
        """
        Delete a channel group.
        
        Args:
            group_name (str): Group name
            
        Returns:
            bool: True if group was deleted, False if not found
        """
        with self.lock:
            if group_name in self.groups:
                del self.groups[group_name]
                self._save_groups()
                return True
            return False
            
    def get_channel_in_groups(self, channel_id: str) -> List[str]:
        """
        Find all groups containing a specific channel.
        
        Args:
            channel_id (str): Channel ID
            
        Returns:
            List[str]: List of group names
        """
        with self.lock:
            matching_groups = []
            for name, group in self.groups.items():
                channels = group.get("channels", [])
                if channel_id in channels:
                    matching_groups.append(name)
            return matching_groups