"""
Category manager for STB-ReStreamer.
Manages channel categories and the assignment of channels to categories.
"""
import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Set
from threading import Lock

# Configure logger
logger = logging.getLogger("STB-Proxy")

class CategoryManager:
    """
    Manager for channel categories.
    Handles the organization of channels into categories.
    """
    
    def __init__(self, config_manager):
        """
        Initialize the category manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.lock = Lock()
        self.categories = {}  # Format: {category_id: category_data}
        self.channel_categories = {}  # Format: {channel_id: set(category_ids)}
        
        # Initialize data directory
        if hasattr(self.config_manager, 'get_data_dir'):
            self.data_dir = self.config_manager.get_data_dir()
        else:
            # Fallback to default data directory
            self.data_dir = "data"
            os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize categories file
        self.categories_file = os.path.join(self.data_dir, "categories.json")
        
        # Create default categories if needed
        self._create_default_categories()
        
        # Load categories from file
        self._load_categories()
        
        logger.info("Category manager initialized")
        
    def _create_default_categories(self):
        """Create default categories if they don't exist."""
        with self.lock:
            # Check if categories file exists
            if not os.path.exists(self.categories_file):
                # Create default categories
                default_categories = {
                    "default": {
                        "id": "default",
                        "name": "Default",
                        "description": "Default category for all channels",
                        "icon": "fa-list",
                        "order": 0,
                        "system": True,
                        "created_at": int(time.time())
                    },
                    "favorites": {
                        "id": "favorites",
                        "name": "Favorites",
                        "description": "Favorite channels",
                        "icon": "fa-star",
                        "order": 1,
                        "system": True,
                        "created_at": int(time.time())
                    }
                }
                
                # Save to file
                try:
                    with open(self.categories_file, 'w', encoding='utf-8') as f:
                        json.dump(default_categories, f, indent=2)
                    logger.info("Created default categories")
                except Exception as e:
                    logger.error(f"Error creating default categories: {str(e)}")
                    
    def _load_categories(self):
        """Load categories from file."""
        with self.lock:
            try:
                if os.path.exists(self.categories_file):
                    with open(self.categories_file, 'r', encoding='utf-8') as f:
                        self.categories = json.load(f)
                    logger.info(f"Loaded {len(self.categories)} categories")
                    
                    # Load channel categories
                    channel_categories_file = os.path.join(self.data_dir, "channel_categories.json")
                    if os.path.exists(channel_categories_file):
                        with open(channel_categories_file, 'r', encoding='utf-8') as f:
                            # Convert dictionary of lists to dictionary of sets for faster operations
                            channel_data = json.load(f)
                            self.channel_categories = {k: set(v) for k, v in channel_data.items()}
                        logger.info(f"Loaded channel categories for {len(self.channel_categories)} channels")
            except Exception as e:
                logger.error(f"Error loading categories: {str(e)}")
                # Initialize with default categories
                self._create_default_categories()
                
    def _save_categories(self):
        """Save categories to file."""
        with self.lock:
            try:
                # Save categories
                with open(self.categories_file, 'w', encoding='utf-8') as f:
                    json.dump(self.categories, f, indent=2)
                    
                # Save channel categories
                channel_categories_file = os.path.join(self.data_dir, "channel_categories.json")
                # Convert sets to lists for JSON serialization
                channel_data = {k: list(v) for k, v in self.channel_categories.items()}
                with open(channel_categories_file, 'w', encoding='utf-8') as f:
                    json.dump(channel_data, f, indent=2)
                    
                logger.info("Saved categories data")
            except Exception as e:
                logger.error(f"Error saving categories: {str(e)}")
                
    def get_categories(self) -> Dict[str, Dict]:
        """
        Get all categories.
        
        Returns:
            Dictionary of categories
        """
        with self.lock:
            return self.categories.copy()
            
    def get_category(self, category_id: str) -> Optional[Dict]:
        """
        Get a category by ID.
        
        Args:
            category_id: Category ID
            
        Returns:
            Category data or None if not found
        """
        with self.lock:
            return self.categories.get(category_id)
            
    def add_category(self, name: str, description: str = "", icon: str = "fa-list") -> Optional[Dict]:
        """
        Add a new category.
        
        Args:
            name: Category name
            description: Category description
            icon: Category icon (Font Awesome class)
            
        Returns:
            New category data or None if failed
        """
        with self.lock:
            try:
                # Generate a unique ID
                category_id = name.lower().replace(' ', '_')
                
                # Make sure ID is unique
                if category_id in self.categories:
                    # Add a timestamp to make it unique
                    category_id = f"{category_id}_{int(time.time())}"
                    
                # Get the highest order value
                max_order = max([c.get('order', 0) for c in self.categories.values()], default=0)
                
                # Create new category
                category = {
                    "id": category_id,
                    "name": name,
                    "description": description,
                    "icon": icon,
                    "order": max_order + 1,
                    "system": False,
                    "created_at": int(time.time())
                }
                
                # Add to categories
                self.categories[category_id] = category
                
                # Save changes
                self._save_categories()
                
                return category
            except Exception as e:
                logger.error(f"Error adding category: {str(e)}")
                return None
                
    def update_category(self, category_id: str, data: Dict) -> Optional[Dict]:
        """
        Update a category.
        
        Args:
            category_id: Category ID
            data: New category data
            
        Returns:
            Updated category data or None if failed
        """
        with self.lock:
            try:
                # Check if category exists
                if category_id not in self.categories:
                    logger.error(f"Category not found: {category_id}")
                    return None
                    
                # Check if it's a system category
                if self.categories[category_id].get('system', False):
                    # Only allow certain fields to be updated for system categories
                    allowed_fields = ['description', 'icon', 'order']
                    category = self.categories[category_id].copy()
                    for field in allowed_fields:
                        if field in data:
                            category[field] = data[field]
                else:
                    # Update all fields except id and system
                    category = self.categories[category_id].copy()
                    for field, value in data.items():
                        if field not in ['id', 'system']:
                            category[field] = value
                            
                # Update categories
                self.categories[category_id] = category
                
                # Save changes
                self._save_categories()
                
                return category
            except Exception as e:
                logger.error(f"Error updating category: {str(e)}")
                return None
                
    def delete_category(self, category_id: str) -> bool:
        """
        Delete a category.
        
        Args:
            category_id: Category ID
            
        Returns:
            True if deleted, False if failed
        """
        with self.lock:
            try:
                # Check if category exists
                if category_id not in self.categories:
                    logger.error(f"Category not found: {category_id}")
                    return False
                    
                # Check if it's a system category
                if self.categories[category_id].get('system', False):
                    logger.error(f"Cannot delete system category: {category_id}")
                    return False
                    
                # Remove category
                del self.categories[category_id]
                
                # Remove category from all channels
                for channel_id, categories in self.channel_categories.items():
                    if category_id in categories:
                        categories.remove(category_id)
                        
                # Save changes
                self._save_categories()
                
                return True
            except Exception as e:
                logger.error(f"Error deleting category: {str(e)}")
                return False
                
    def assign_channel_to_category(self, channel_id: str, category_id: str) -> bool:
        """
        Assign a channel to a category.
        
        Args:
            channel_id: Channel ID
            category_id: Category ID
            
        Returns:
            True if assigned, False if failed
        """
        with self.lock:
            try:
                # Check if category exists
                if category_id not in self.categories:
                    logger.error(f"Category not found: {category_id}")
                    return False
                    
                # Initialize the channel's categories if not already present
                if channel_id not in self.channel_categories:
                    self.channel_categories[channel_id] = set()
                    
                # Add category to channel
                self.channel_categories[channel_id].add(category_id)
                
                # Save changes
                self._save_categories()
                
                return True
            except Exception as e:
                logger.error(f"Error assigning channel to category: {str(e)}")
                return False
                
    def remove_channel_from_category(self, channel_id: str, category_id: str) -> bool:
        """
        Remove a channel from a category.
        
        Args:
            channel_id: Channel ID
            category_id: Category ID
            
        Returns:
            True if removed, False if failed
        """
        with self.lock:
            try:
                # Check if channel has categories
                if channel_id not in self.channel_categories:
                    logger.error(f"Channel has no categories: {channel_id}")
                    return False
                    
                # Check if channel is in category
                if category_id not in self.channel_categories[channel_id]:
                    logger.error(f"Channel not in category: {channel_id} -> {category_id}")
                    return False
                    
                # Remove category from channel
                self.channel_categories[channel_id].remove(category_id)
                
                # If channel has no categories, assign to default
                if not self.channel_categories[channel_id]:
                    self.channel_categories[channel_id].add('default')
                    
                # Save changes
                self._save_categories()
                
                return True
            except Exception as e:
                logger.error(f"Error removing channel from category: {str(e)}")
                return False
                
    def get_channel_categories(self, channel_id: str) -> List[Dict]:
        """
        Get categories for a channel.
        
        Args:
            channel_id: Channel ID
            
        Returns:
            List of category data for the channel
        """
        with self.lock:
            try:
                # Check if channel has categories
                if channel_id not in self.channel_categories:
                    # Return default category
                    default_category = self.categories.get('default')
                    if default_category:
                        return [default_category]
                    return []
                    
                # Get category data for each category ID
                categories = []
                for category_id in self.channel_categories[channel_id]:
                    category = self.categories.get(category_id)
                    if category:
                        categories.append(category)
                        
                # Sort by order
                categories.sort(key=lambda c: c.get('order', 0))
                
                return categories
            except Exception as e:
                logger.error(f"Error getting channel categories: {str(e)}")
                return []
                
    def get_channels_in_category(self, category_id: str) -> List[str]:
        """
        Get channels in a category.
        
        Args:
            category_id: Category ID
            
        Returns:
            List of channel IDs in the category
        """
        with self.lock:
            try:
                # Check if category exists
                if category_id not in self.categories:
                    logger.error(f"Category not found: {category_id}")
                    return []
                    
                # Get all channels in the category
                channels = []
                for channel_id, categories in self.channel_categories.items():
                    if category_id in categories:
                        channels.append(channel_id)
                        
                return channels
            except Exception as e:
                logger.error(f"Error getting channels in category: {str(e)}")
                return []
                
    def set_channel_categories(self, channel_id: str, category_ids: List[str]) -> bool:
        """
        Set all categories for a channel.
        Replaces all existing categories.
        
        Args:
            channel_id: Channel ID
            category_ids: List of category IDs
            
        Returns:
            True if set, False if failed
        """
        with self.lock:
            try:
                # Validate all category IDs
                valid_ids = []
                for category_id in category_ids:
                    if category_id in self.categories:
                        valid_ids.append(category_id)
                    else:
                        logger.warning(f"Ignoring invalid category ID: {category_id}")
                        
                # If no valid IDs, assign to default
                if not valid_ids:
                    valid_ids = ['default']
                    
                # Set channel categories
                self.channel_categories[channel_id] = set(valid_ids)
                
                # Save changes
                self._save_categories()
                
                return True
            except Exception as e:
                logger.error(f"Error setting channel categories: {str(e)}")
                return False
                
    def add_channels_to_default(self, channel_ids: List[str]) -> int:
        """
        Add multiple channels to the default category.
        
        Args:
            channel_ids: List of channel IDs
            
        Returns:
            Number of channels added
        """
        with self.lock:
            try:
                count = 0
                for channel_id in channel_ids:
                    # Initialize the channel's categories if not already present
                    if channel_id not in self.channel_categories:
                        self.channel_categories[channel_id] = {'default'}
                        count += 1
                        
                # Save changes
                self._save_categories()
                
                return count
            except Exception as e:
                logger.error(f"Error adding channels to default: {str(e)}")
                return 0
                
    def clean_up_channels(self, existing_channel_ids: List[str]) -> int:
        """
        Clean up channel categories by removing non-existent channels.
        
        Args:
            existing_channel_ids: List of channel IDs that should be kept
            
        Returns:
            Number of channels removed
        """
        with self.lock:
            try:
                existing_set = set(existing_channel_ids)
                to_remove = []
                
                # Find channels to remove
                for channel_id in self.channel_categories:
                    if channel_id not in existing_set:
                        to_remove.append(channel_id)
                        
                # Remove channels
                for channel_id in to_remove:
                    del self.channel_categories[channel_id]
                    
                # Save changes
                if to_remove:
                    self._save_categories()
                    
                return len(to_remove)
            except Exception as e:
                logger.error(f"Error cleaning up channel categories: {str(e)}")
                return 0