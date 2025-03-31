"""
Test script for STB-ReStreamer portal providers.
This script will test the functionality of all implemented portal providers.
"""
import sys
import os
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test-providers")

# Add src to the path
sys.path.insert(0, os.path.abspath("."))

# Import providers
from src.services.portal_providers.base_provider import BasePortalProvider
from src.services.portal_providers.stalker_provider import StalkerPortalProvider
from src.services.portal_providers.xtream_provider import XtreamPortalProvider
from src.services.portal_providers.ministra_provider import MinistraPortalProvider
from src.services.portal_providers.xc_updates_provider import XCUpdatesPortalProvider
from src.services.portal_providers.m3u_provider import M3UPlaylistProvider

def test_provider(provider_class, config):
    """
    Test a provider with the given configuration.
    
    Args:
        provider_class: The provider class to test
        config: Provider configuration
        
    Returns:
        bool: True if successful, False otherwise
    """
    provider_name = provider_class.__name__
    logger.info(f"Testing {provider_name}...")
    
    try:
        # Create provider instance
        provider = provider_class()
        logger.info(f"Created {provider_name} instance")
        
        # Test get_token
        token = provider.get_token(config, "00:11:22:33:44:55")
        logger.info(f"Got token: {token[:10] if len(token) > 10 else token}...")
        
        # Test get_profile
        profile = provider.get_profile(config, "00:11:22:33:44:55", token)
        logger.info(f"Got profile with status: {profile.get('status', 'unknown')}")
        
        # Test get_channels
        channels = provider.get_channels(config, "00:11:22:33:44:55", token)
        if not channels:
            logger.warning(f"No channels returned for {provider_name}")
        else:
            logger.info(f"Got {len(channels)} channels")
            
            # Test first channel
            first_channel = channels[0]
            channel_id = first_channel.get("id", "")
            channel_name = first_channel.get("name", "Unknown")
            logger.info(f"First channel: {channel_name} (ID: {channel_id})")
            
            # Test get_stream_url
            stream_url = provider.get_stream_url(config, "00:11:22:33:44:55", channel_id, token)
            logger.info(f"Got stream URL: {stream_url}")
        
        logger.info(f"{provider_name} tests PASSED")
        return True
    except Exception as e:
        logger.error(f"{provider_name} test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point for the script."""
    logger.info("Starting provider tests...")
    
    # Test configurations
    test_configs = {
        "stalker": {
            "provider": StalkerPortalProvider,
            "config": {
                "name": "Test Stalker",
                "type": "stalker",
                "url": "http://example.com",
                "username": "test",
                "password": "test"
            }
        },
        "xtream": {
            "provider": XtreamPortalProvider,
            "config": {
                "name": "Test Xtream",
                "type": "xtream",
                "url": "http://example.com",
                "username": "test",
                "password": "test"
            }
        },
        "ministra": {
            "provider": MinistraPortalProvider,
            "config": {
                "name": "Test Ministra",
                "type": "ministra",
                "url": "http://example.com",
                "username": "test",
                "password": "test"
            }
        },
        "xc_updates": {
            "provider": XCUpdatesPortalProvider,
            "config": {
                "name": "Test XC Updates",
                "type": "xcupdates",
                "url": "http://example.com",
                "username": "test",
                "password": "test"
            }
        },
        "m3u": {
            "provider": M3UPlaylistProvider,
            "config": {
                "name": "Test M3U",
                "type": "m3u",
                "url": "http://example.com/playlist.m3u"
            }
        }
    }
    
    # Run tests
    results = {}
    for provider_name, test_info in test_configs.items():
        logger.info(f"\n=== Testing {provider_name} provider ===")
        results[provider_name] = test_provider(test_info["provider"], test_info["config"])
    
    # Print results
    logger.info("\n=== Test Results ===")
    all_passed = True
    for provider_name, success in results.items():
        status = "PASSED" if success else "FAILED"
        logger.info(f"{provider_name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        logger.info("\nAll tests passed!")
        return 0
    else:
        logger.error("\nSome tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())