"""
Base portal provider for STB-ReStreamer.
Defines the interface for all portal providers.
"""
import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

# Configure logger
logger = logging.getLogger("STB-Proxy")

class BasePortalProvider(ABC):
    """
    Abstract base class for portal providers.
    All portal providers must implement these methods.
    """
    
    @abstractmethod
    def get_token(self, portal: Dict[str, Any], mac: str) -> Optional[str]:
        """
        Get an authentication token for the portal.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            
        Returns:
            Optional[str]: Authentication token or None if failed
        """
        pass
        
    @abstractmethod
    def get_profile(self, portal: Dict[str, Any], mac: str, token: Optional[str] = None) -> Optional[Dict]:
        """
        Get user profile information.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            token (Optional[str]): Authentication token
            
        Returns:
            Optional[Dict]: User profile information or None if failed
        """
        pass
        
    @abstractmethod
    def get_channels(self, portal: Dict[str, Any], mac: str, token: Optional[str] = None) -> List[Dict]:
        """
        Get channel list for a portal.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            token (Optional[str]): Authentication token
            
        Returns:
            List[Dict]: List of channels
        """
        pass
        
    @abstractmethod
    def get_stream_url(self, portal: Dict[str, Any], mac: str, channel_id: str, token: Optional[str] = None) -> Optional[str]:
        """
        Get stream URL for a channel.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            channel_id (str): Channel ID
            token (Optional[str]): Authentication token
            
        Returns:
            Optional[str]: Stream URL or None if failed
        """
        pass
        
    @abstractmethod
    def get_epg(self, portal: Dict[str, Any], mac: str, channel_id: Optional[str] = None, 
                token: Optional[str] = None, start_time: Optional[int] = None, 
                end_time: Optional[int] = None) -> Dict:
        """
        Get EPG data.
        
        Args:
            portal (Dict[str, Any]): Portal configuration
            mac (str): MAC address
            channel_id (Optional[str]): Channel ID for specific channel, or None for all
            token (Optional[str]): Authentication token
            start_time (Optional[int]): Start time timestamp, or None for current time
            end_time (Optional[int]): End time timestamp, or None for 24 hours from start
            
        Returns:
            Dict: EPG data
        """
        pass