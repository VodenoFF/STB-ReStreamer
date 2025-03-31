"""
Channel model for STB-ReStreamer.
Defines channel and stream data structures.
"""
from typing import Dict, List, Optional, Any


class ChannelStream:
    """
    Channel stream information.
    Contains information about a stream for a channel.
    """
    
    def __init__(self, url: str, quality: str = "SD", codec: str = "unknown"):
        """
        Initialize a new channel stream.
        
        Args:
            url (str): Stream URL
            quality (str): Stream quality (SD, HD, FHD, etc.)
            codec (str): Stream codec (h264, h265, etc.)
        """
        self.url = url
        self.quality = quality
        self.codec = codec
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "url": self.url,
            "quality": self.quality,
            "codec": self.codec
        }
        
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ChannelStream':
        """
        Create from dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary representation
            
        Returns:
            ChannelStream: New instance
        """
        return ChannelStream(
            url=data.get("url", ""),
            quality=data.get("quality", "SD"),
            codec=data.get("codec", "unknown")
        )


class Channel:
    """
    Channel information.
    Contains information about a TV channel.
    """
    
    def __init__(self, channel_id: str, name: str, number: int = 0, 
                category: str = "", logo: str = "", streams: List[ChannelStream] = None):
        """
        Initialize a new channel.
        
        Args:
            channel_id (str): Channel ID
            name (str): Channel name
            number (int): Channel number
            category (str): Channel category
            logo (str): Channel logo URL
            streams (List[ChannelStream]): Channel streams
        """
        self.id = channel_id
        self.name = name
        self.number = number
        self.category = category
        self.logo = logo
        self.streams = streams or []
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "id": self.id,
            "name": self.name,
            "number": self.number,
            "category": self.category,
            "logo": self.logo,
            "streams": [stream.to_dict() for stream in self.streams]
        }
        
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Channel':
        """
        Create from dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary representation
            
        Returns:
            Channel: New instance
        """
        streams = []
        if "streams" in data and isinstance(data["streams"], list):
            streams = [ChannelStream.from_dict(s) for s in data["streams"]]
        elif "url" in data:
            # For backwards compatibility with old format
            streams = [ChannelStream(data.get("url", ""))]
            
        return Channel(
            channel_id=data.get("id", ""),
            name=data.get("name", ""),
            number=data.get("number", 0),
            category=data.get("category", ""),
            logo=data.get("logo", ""),
            streams=streams
        )