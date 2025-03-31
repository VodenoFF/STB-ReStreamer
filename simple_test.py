"""
Simple test script to check imports.
"""
try:
    with open('import_test_results.txt', 'w') as f:
        f.write("Testing imports...\n")
        import sys
        import os
        
        # Add src to the path
        sys.path.insert(0, os.path.abspath('.'))
        
        f.write("Importing base provider...\n")
        from src.services.portal_providers.base_provider import BasePortalProvider
        f.write("Base provider imported successfully\n")
        
        f.write("Importing stalker provider...\n")
        from src.services.portal_providers.stalker_provider import StalkerPortalProvider
        f.write("Stalker provider imported successfully\n")
        
        f.write("Importing xtream provider...\n")
        from src.services.portal_providers.xtream_provider import XtreamPortalProvider
        f.write("Xtream provider imported successfully\n")
        
        f.write("Importing M3U provider...\n")
        from src.services.portal_providers.m3u_provider import M3UPlaylistProvider
        f.write("M3U provider imported successfully\n")
        
        f.write("Importing ministra provider...\n")
        from src.services.portal_providers.ministra_provider import MinistraPortalProvider
        f.write("Ministra provider imported successfully\n")
        
        f.write("Importing XC Updates provider...\n")
        from src.services.portal_providers.xc_updates_provider import XCUpdatesPortalProvider
        f.write("XC Updates provider imported successfully\n")
        
        f.write("\nAll individual imports successful!\n")
        
        f.write("\nTesting combined import...\n")
        from src.services.portal_providers import (
            BasePortalProvider,
            StalkerPortalProvider,
            XtreamPortalProvider,
            M3UPlaylistProvider,
            MinistraPortalProvider,
            XCUpdatesPortalProvider
        )
        f.write("Combined import successful!\n")
        
        f.write("\nTesting StbApi...\n")
        from src.services.stb_api import StbApi
        f.write("StbApi imported successfully!\n")
        
        f.write("\nAll tests passed!\n")
    
    print("Test completed. Results written to import_test_results.txt")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    with open('import_test_results.txt', 'a') as f:
        f.write(f"\nError: {e}\n")
        import traceback
        traceback.print_exc(file=f)