"""
Simple test script to verify portal providers functionality.
"""
import os
import sys
import logging
import json
from typing import Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import STB API service and portal providers
from src.services.stb_api import StbApi
from src.services.portal_providers import (
    StalkerPortalProvider,
    XtreamPortalProvider,
    M3UPlaylistProvider,
    MinistraPortalProvider,
    XCUpdatesPortalProvider
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger()

class MockConfigManager:
    """Mock configuration manager for testing."""
    
    def __init__(self):
        """Initialize with default settings."""
        self.settings = {
            'security': {
                'encryption_key': 'test_key',
                'token_lifetime': 12 * 3600
            }
        }
        
    def get(self, section, key, default=None):
        """Get a setting by section and key."""
        return self.settings.get(section, {}).get(key, default)
        
    def get_setting(self, key, default=None):
        """Legacy method to get a setting."""
        for section in self.settings.values():
            if key in section:
                return section[key]
        return default
        
    def get_data_dir(self):
        """Get data directory."""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

def create_test_portal(portal_type: str) -> Dict:
    """
    Create a test portal configuration.
    
    Args:
        portal_type: Type of portal (stalker, xtream, m3u, ministra, xc_updates)
        
    Returns:
        Portal configuration dictionary
    """
    base_config = {
        'id': f'test_{portal_type}',
        'name': f'Test {portal_type.capitalize()} Portal',
        'type': portal_type,
        'enabled': True
    }
    
    if portal_type in ('stalker', 'ministra'):
        base_config.update({
            'url': 'http://example.com',
            'username': 'user123',
            'password': 'pass123'
        })
    elif portal_type in ('xtream', 'xc_updates'):
        base_config.update({
            'url': 'http://example.com',
            'username': 'user123',
            'password': 'pass123',
            'stream_format': 'ts'
        })
    elif portal_type == 'm3u':
        base_config.update({
            'url': 'http://example.com/playlist.m3u',
            'refresh_interval': 24  # hours
        })
        
    return base_config

def test_stb_api():
    """Test the STB API with different providers."""
    logger.info("TESTING STB API SERVICE")
    
    # Create mock config manager
    config_manager = MockConfigManager()
    
    # Initialize STB API
    stb_api = StbApi(config_manager)
    
    # Check if all providers are initialized
    logger.info(f"Available providers: {', '.join(stb_api.providers.keys())}")
    
    # Create a test MAC address
    test_mac = '00:11:22:33:44:55'
    
    # Test each provider type
    for provider_type in stb_api.providers:
        logger.info(f"\nTesting provider: {provider_type}")
        
        # Create a test portal
        test_portal = create_test_portal(provider_type)
        portal_id = test_portal['id']
        
        # Mock the _get_portal method to return our test portal
        stb_api._get_portal = lambda x: test_portal if x == portal_id else None
        
        # Test method calls (these will use dummy implementations)
        logger.info("Testing get_token:")
        token = stb_api.get_token(portal_id, test_mac)
        logger.info(f"  Result: {'Success' if token else 'Failed'}")
        
        logger.info("Testing get_profile:")
        profile = stb_api.get_profile(portal_id, test_mac)
        logger.info(f"  Result: {'Success' if profile else 'Failed'}")
        
        logger.info("Testing get_channels:")
        channels = stb_api.get_channels(portal_id, test_mac)
        logger.info(f"  Result: {'Success' if channels else 'Failed'} (Got {len(channels)} channels)")
        
        if channels:
            # Get a test channel ID
            test_channel_id = channels[0]['id']
            
            logger.info("Testing get_stream_url:")
            stream_url = stb_api.get_stream_url(portal_id, test_mac, test_channel_id)
            logger.info(f"  Result: {'Success' if stream_url else 'Failed'}")
            
            logger.info("Testing get_epg:")
            epg = stb_api.get_epg(portal_id, test_mac, test_channel_id)
            logger.info(f"  Result: {'Success' if epg else 'Failed'}")

def test_individual_providers():
    """Test each provider directly."""
    logger.info("\nTESTING INDIVIDUAL PROVIDERS")
    
    providers = {
        'stalker': StalkerPortalProvider(),
        'xtream': XtreamPortalProvider(),
        'm3u': M3UPlaylistProvider(),
        'ministra': MinistraPortalProvider(),
        'xc_updates': XCUpdatesPortalProvider()
    }
    
    # Create a test MAC address
    test_mac = '00:11:22:33:44:55'
    
    for provider_type, provider in providers.items():
        logger.info(f"\nTesting provider: {provider_type}")
        
        # Create a test portal
        test_portal = create_test_portal(provider_type)
        
        # Test method calls
        logger.info("Testing provider interface:")
        logger.info(f"  Provider class: {provider.__class__.__name__}")
        
        # This will use dummy implementations since we're not connecting to real servers
        try:
            # Get token (will use dummy implementation)
            dummy_token = provider.get_token(test_portal, test_mac)
            logger.info(f"  get_token: {'Success' if dummy_token else 'Failed'}")
            
            # Get profile (will use dummy implementation)
            dummy_profile = provider.get_profile(test_portal, test_mac, dummy_token)
            logger.info(f"  get_profile: {'Success' if dummy_profile else 'Failed'}")
            
            # Get channels (will use dummy implementation)
            dummy_channels = provider.get_channels(test_portal, test_mac, dummy_token)
            logger.info(f"  get_channels: {'Success' if dummy_channels else 'Failed'}")
            
            # Get a dummy channel ID
            dummy_channel_id = "ch1"
            
            # Get stream URL (will use dummy implementation)
            dummy_stream_url = provider.get_stream_url(test_portal, test_mac, dummy_channel_id, dummy_token)
            logger.info(f"  get_stream_url: {'Success' if dummy_stream_url else 'Failed'}")
            
            # Get EPG (will use dummy implementation)
            dummy_epg = provider.get_epg(test_portal, test_mac, dummy_channel_id, dummy_token)
            logger.info(f"  get_epg: {'Success' if dummy_epg else 'Failed'}")
            
        except Exception as e:
            logger.error(f"Error testing {provider_type} provider: {str(e)}")

if __name__ == "__main__":
    # Create data directory if it doesn't exist
    os.makedirs(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data')), exist_ok=True)
    
    # Run tests
    test_stb_api()
    test_individual_providers()
    
    logger.info("\nAll tests completed. Note that these are smoke tests only.")
    logger.info("They verify the interface but use dummy implementations.")