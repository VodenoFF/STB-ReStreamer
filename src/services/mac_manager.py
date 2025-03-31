"""
MAC address management service for STB-ReStreamer.
"""
import time
import logging
from typing import Dict, Any, Optional, List
from threading import Lock

# Configure logger
logger = logging.getLogger("STB-Proxy")

class MacManager:
    """
    Thread-safe manager for MAC address allocation and tracking.
    """
    def __init__(self):
        """
        Initialize the MAC manager.
        """
        self.lock = Lock()
        self.occupied_macs = {}  # Format: {portal_id: {mac: {channel_id: timestamp}}}
        logger.info("MAC manager initialized")
        
    def is_mac_free(self, portal_id: str, mac: str, max_streams: int) -> bool:
        """
        Check if a MAC has available capacity for additional streams.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            max_streams (int): Maximum allowed streams per MAC
            
        Returns:
            bool: True if MAC is free, False otherwise
        """
        with self.lock:
            if max_streams == 0:  # Unlimited streams
                return True
                
            # Get streams for this MAC
            if portal_id not in self.occupied_macs:
                return True
                
            if mac not in self.occupied_macs[portal_id]:
                return True
                
            # Count active streams
            active_streams = len(self.occupied_macs[portal_id][mac])
            return active_streams < max_streams
            
    def occupy_mac(self, portal_id: str, mac: str, channel_id: str, channel_name: str, 
                  client_ip: str, portal_name: str) -> bool:
        """
        Mark a MAC address as occupied for a specific channel.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            channel_id (str): Channel ID
            channel_name (str): Channel name
            client_ip (str): Client IP address
            portal_name (str): Portal name
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.lock:
            # Initialize portal and MAC if needed
            if portal_id not in self.occupied_macs:
                self.occupied_macs[portal_id] = {}
                
            if mac not in self.occupied_macs[portal_id]:
                self.occupied_macs[portal_id][mac] = {}
                
            # Occupy MAC for this channel
            self.occupied_macs[portal_id][mac][channel_id] = {
                "timestamp": time.time(),
                "channel_name": channel_name,
                "client_ip": client_ip,
                "portal_name": portal_name
            }
            
            return True
            
    def release_mac(self, portal_id: str, mac: str, channel_id: str, 
                   channel_name: str, client_ip: str, portal_name: str) -> bool:
        """
        Release an occupied MAC address.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            channel_id (str): Channel ID
            channel_name (str): Channel name
            client_ip (str): Client IP address
            portal_name (str): Portal name
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.lock:
            if (portal_id in self.occupied_macs and
                mac in self.occupied_macs[portal_id] and
                channel_id in self.occupied_macs[portal_id][mac]):
                
                # Release MAC for this channel
                del self.occupied_macs[portal_id][mac][channel_id]
                
                # Clean up empty dictionaries
                if not self.occupied_macs[portal_id][mac]:
                    del self.occupied_macs[portal_id][mac]
                    
                if not self.occupied_macs[portal_id]:
                    del self.occupied_macs[portal_id]
                    
                return True
                
            return False
            
    def move_mac(self, portal_id: str, mac: str) -> bool:
        """
        Move a MAC address to the end of the rotation list.
        Simply update the timestamp to simulate this.
        
        Args:
            portal_id (str): Portal ID
            mac (str): MAC address
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.lock:
            if (portal_id in self.occupied_macs and
                mac in self.occupied_macs[portal_id]):
                
                # Update timestamps for all channels using this MAC
                for channel_id in self.occupied_macs[portal_id][mac]:
                    self.occupied_macs[portal_id][mac][channel_id]["timestamp"] = time.time()
                    
                return True
                
            return False
            
    def get_occupied_macs(self, portal_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about currently occupied MACs.
        
        Args:
            portal_id (Optional[str]): Filter by portal ID
            
        Returns:
            Dict[str, Any]: Dictionary of occupied MACs with details
        """
        with self.lock:
            result = {}
            
            if portal_id:
                # Filter by portal ID
                if portal_id in self.occupied_macs:
                    result[portal_id] = self.occupied_macs[portal_id].copy()
            else:
                # All portals
                result = {pid: portals.copy() for pid, portals in self.occupied_macs.items()}
                
            return result