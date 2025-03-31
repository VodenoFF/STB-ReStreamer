"""
Simple test script to check imports separately.
"""
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test-imports")

# Add src to the path
sys.path.insert(0, os.path.abspath("."))

# Test individual imports
try:
    logger.info("Testing individual imports...")
    
    logger.info("Importing base_provider...")
    from src.services.portal_providers.base_provider import BasePortalProvider
    logger.info("OK")
    
    logger.info("Importing stalker_provider...")
    from src.services.portal_providers.stalker_provider import StalkerPortalProvider
    logger.info("OK")
    
    logger.info("Importing xtream_provider...")
    from src.services.portal_providers.xtream_provider import XtreamPortalProvider
    logger.info("OK")
    
    logger.info("Importing ministra_provider...")
    from src.services.portal_providers.ministra_provider import MinistraPortalProvider
    logger.info("OK")
    
    logger.info("Importing xc_updates_provider...")
    from src.services.portal_providers.xc_updates_provider import XCUpdatesPortalProvider
    logger.info("OK")
    
    logger.info("Importing m3u_provider...")
    from src.services.portal_providers.m3u_provider import M3UPlaylistProvider
    logger.info("OK")
    
    logger.info("All provider imports successful!")
    
except Exception as e:
    logger.error(f"Import error: {e}")
    import traceback
    traceback.print_exc()