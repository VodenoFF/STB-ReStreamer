"""
Channel category management for STB-ReStreamer.
Handles creation, modification, and assignment of channel categories.
"""
import os
import json
import uuid
import logging
from threading import Lock
from typing import Dict, List, Any, Optional, Set

# Configure logger
logger = logging.getLogger("STB-Proxy")

class CategoryManager:
    """
    Manager for channel categories.
    Handles CRUD operations for categories and channel assignments.
    """
    
    def __init__(self, filename: str = "categories.json"):
        """
        Initialize the category manager.
        
        Args:
            filename (str): Path to the categories JSON file
        """
        self.filename = filename
        self.lock = Lock()
        self.categories = {}  # id -> category
        self.channel_categories = {}  # channel_id -> set(category_ids)
        self._load_categories()
        logger.info(f"Category manager initialized with file: {filename}")
    
    def _load_categories(self) -> None:
        """
        Load categories from the JSON file.
        If the file doesn't exist, create an empty categories list.
        """
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.categories = data.get('categories', {})
                    self.channel_categories = {}
                    
                    # Convert channel_categories from list to set for each channel
                    for channel_id, category_ids in data.get('channel_categories', {}).items():
                        self.channel_categories[channel_id] = set(category_ids)
                        
                    logger.debug(f"Loaded {len(self.categories)} categories and {len(self.channel_categories)} channel assignments")
            else:
                # Create default categories
                self.categories = {
                    "default": {
                        "id": "default",
                        "name": "Default",
                        "description": "Default category for all channels",
                        "color": "#6c757d",
                        "icon": "fas fa-th-list",
                        "order": 0,
                        "system": True
                    },
                    "favorites": {
                        "id": "favorites",
                        "name": "Favorites",
                        "description": "Favorite channels",
                        "color": "#ffc107",
                        "icon": "fas fa-star",
                        "order": 1,
                        "system": True
                    }
                }
                self.channel_categories = {}
                self._save_categories()
                logger.debug("Created default categories")
        except Exception as e:
            logger.error(f"Error loading categories: {str(e)}")
            # Create default categories
            self.categories = {
                "default": {
                    "id": "default",
                    "name": "Default",
                    "description": "Default category for all channels",
                    "color": "#6c757d",
                    "icon": "fas fa-th-list",
                    "order": 0,
                    "system": True
                }
            }
            self.channel_categories = {}
    
    def _save_categories(self) -> None:
        """
        Save categories to the JSON file.
        """
        try:
            # Convert channel_categories from set to list for JSON serialization
            channel_categories_json = {}
            for channel_id, category_ids in self.channel_categories.items():
                channel_categories_json[channel_id] = list(category_ids)
                
            data = {
                'categories': self.categories,
                'channel_categories': channel_categories_json
            }
            
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                logger.debug(f"Saved {len(self.categories)} categories and {len(self.channel_categories)} channel assignments")
        except Exception as e:
            logger.error(f"Error saving categories: {str(e)}")
    
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """
        Get all categories.
        
        Returns:
            List[Dict[str, Any]]: List of all categories
        """
        with self.lock:
            # Convert to list and sort by order
            categories = list(self.categories.values())
            categories.sort(key=lambda x: x.get('order', 0))
            return categories
    
    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a category by ID.
        
        Args:
            category_id (str): Category ID
            
        Returns:
            Optional[Dict[str, Any]]: Category or None if not found
        """
        with self.lock:
            return self.categories.get(category_id)
    
    def add_category(self, name: str, description: str = "", color: str = "#6c757d", 
                      icon: str = "fas fa-th-list", order: int = 0) -> str:
        """
        Add a new category.
        
        Args:
            name (str): Category name
            description (str, optional): Category description
            color (str, optional): Category color (hex)
            icon (str, optional): Category icon (FontAwesome class)
            order (int, optional): Display order
            
        Returns:
            str: ID of the new category
        """
        with self.lock:
            # Generate a unique ID
            category_id = str(uuid.uuid4())
            
            # Create category
            self.categories[category_id] = {
                'id': category_id,
                'name': name,
                'description': description,
                'color': color,
                'icon': icon,
                'order': order,
                'system': False
            }
            
            self._save_categories()
            logger.info(f"Added category: {name} ({category_id})")
            return category_id
    
    def update_category(self, category_id: str, name: Optional[str] = None, 
                         description: Optional[str] = None, color: Optional[str] = None,
                         icon: Optional[str] = None, order: Optional[int] = None) -> bool:
        """
        Update a category.
        
        Args:
            category_id (str): Category ID
            name (Optional[str]): New category name
            description (Optional[str]): New category description
            color (Optional[str]): New category color
            icon (Optional[str]): New category icon
            order (Optional[int]): New display order
            
        Returns:
            bool: True if the category was updated, False otherwise
        """
        with self.lock:
            # Check if the category exists
            if category_id not in self.categories:
                logger.error(f"Category not found: {category_id}")
                return False
            
            # Check if it's a system category
            if self.categories[category_id].get('system', False):
                logger.error(f"Cannot update system category: {category_id}")
                return False
            
            # Update category
            category = self.categories[category_id]
            if name is not None:
                category['name'] = name
            if description is not None:
                category['description'] = description
            if color is not None:
                category['color'] = color
            if icon is not None:
                category['icon'] = icon
            if order is not None:
                category['order'] = order
            
            self._save_categories()
            logger.info(f"Updated category: {category_id}")
            return True
    
    def delete_category(self, category_id: str) -> bool:
        """
        Delete a category.
        
        Args:
            category_id (str): Category ID
            
        Returns:
            bool: True if the category was deleted, False otherwise
        """
        with self.lock:
            # Check if the category exists
            if category_id not in self.categories:
                logger.error(f"Category not found: {category_id}")
                return False
            
            # Check if it's a system category
            if self.categories[category_id].get('system', False):
                logger.error(f"Cannot delete system category: {category_id}")
                return False
            
            # Delete category
            del self.categories[category_id]
            
            # Remove category from channel assignments
            for channel_id in self.channel_categories:
                if category_id in self.channel_categories[channel_id]:
                    self.channel_categories[channel_id].remove(category_id)
            
            self._save_categories()
            logger.info(f"Deleted category: {category_id}")
            return True
    
    def get_channel_categories(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Get categories for a channel.
        
        Args:
            channel_id (str): Channel ID
            
        Returns:
            List[Dict[str, Any]]: List of categories for the channel
        """
        with self.lock:
            # Get category IDs for the channel
            category_ids = self.channel_categories.get(channel_id, set())
            
            # Get categories
            categories = []
            for category_id in category_ids:
                category = self.categories.get(category_id)
                if category:
                    categories.append(category)
            
            # Sort by order
            categories.sort(key=lambda x: x.get('order', 0))
            return categories
    
    def assign_channel_to_category(self, channel_id: str, category_id: str) -> bool:
        """
        Assign a channel to a category.
        
        Args:
            channel_id (str): Channel ID
            category_id (str): Category ID
            
        Returns:
            bool: True if the channel was assigned, False otherwise
        """
        with self.lock:
            # Check if the category exists
            if category_id not in self.categories:
                logger.error(f"Category not found: {category_id}")
                return False
            
            # Initialize set if not exists
            if channel_id not in self.channel_categories:
                self.channel_categories[channel_id] = set()
            
            # Add to set
            self.channel_categories[channel_id].add(category_id)
            
            self._save_categories()
            logger.debug(f"Assigned channel {channel_id} to category {category_id}")
            return True
    
    def unassign_channel_from_category(self, channel_id: str, category_id: str) -> bool:
        """
        Unassign a channel from a category.
        
        Args:
            channel_id (str): Channel ID
            category_id (str): Category ID
            
        Returns:
            bool: True if the channel was unassigned, False otherwise
        """
        with self.lock:
            # Check if the channel has categories
            if channel_id not in self.channel_categories:
                logger.error(f"Channel has no categories: {channel_id}")
                return False
            
            # Check if the channel is in the category
            if category_id not in self.channel_categories[channel_id]:
                logger.error(f"Channel {channel_id} not in category {category_id}")
                return False
            
            # Remove from set
            self.channel_categories[channel_id].remove(category_id)
            
            # Remove empty set
            if not self.channel_categories[channel_id]:
                del self.channel_categories[channel_id]
            
            self._save_categories()
            logger.debug(f"Unassigned channel {channel_id} from category {category_id}")
            return True
    
    def set_channel_categories(self, channel_id: str, category_ids: List[str]) -> bool:
        """
        Set categories for a channel (replaces all existing assignments).
        
        Args:
            channel_id (str): Channel ID
            category_ids (List[str]): List of category IDs
            
        Returns:
            bool: True if the categories were set, False otherwise
        """
        with self.lock:
            # Validate category IDs
            valid_category_ids = []
            for category_id in category_ids:
                if category_id in self.categories:
                    valid_category_ids.append(category_id)
                else:
                    logger.warning(f"Invalid category ID: {category_id}")
            
            # Set categories
            if valid_category_ids:
                self.channel_categories[channel_id] = set(valid_category_ids)
            else:
                # Remove channel if no valid categories
                if channel_id in self.channel_categories:
                    del self.channel_categories[channel_id]
            
            self._save_categories()
            logger.debug(f"Set {len(valid_category_ids)} categories for channel {channel_id}")
            return True
    
    def get_channels_in_category(self, category_id: str) -> List[str]:
        """
        Get channels in a category.
        
        Args:
            category_id (str): Category ID
            
        Returns:
            List[str]: List of channel IDs in the category
        """
        with self.lock:
            # Check if the category exists
            if category_id not in self.categories:
                logger.error(f"Category not found: {category_id}")
                return []
            
            # Find channels in the category
            channels = []
            for channel_id, category_ids in self.channel_categories.items():
                if category_id in category_ids:
                    channels.append(channel_id)
            
            return channels