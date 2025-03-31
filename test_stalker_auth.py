#!/usr/bin/env python3
"""
Test script for Stalker provider authentication
"""
import logging
import json
import sys
import os

# Add the current directory to the path to ensure imports work
sys.path.insert(0, os.path.abspath('.'))

# Now import from the project
from src.services.portal_providers.stalker_provider import StalkerProvider

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test-stalker")

def main():
    """
    Test Stalker provider authentication with and without credentials
    """
    print("=== Testing Stalker Provider Authentication ===")
    
    # Load the portal configuration
    try:
        with open('portals.json', 'r') as f:
            portals = json.load(f)
        
        # Find the test_stalker portal
        if 'test_stalker' in portals:
            portal = portals['test_stalker']
            print(f"Found test portal: {portal['name']}")
            
            # Create provider
            provider = StalkerProvider()
            
            # Test with credentials
            print("\n=== Testing with credentials ===")
            # Ensure the credentials are present
            if not portal.get('username') or not portal.get('password'):
                portal['username'] = 'user123'
                portal['password'] = 'pass123'
                print(f"Added test credentials: {portal['username']} / {portal['password']}")
            
            # Get a MAC from the portal
            mac = next(iter(portal.get('macs', {})))
            if not mac:
                mac = "00:1A:79:00:00:01"
                portal['macs'] = {mac: {"serial": "012345", "device_id": "012345", "device_id2": "012345"}}
                print(f"Added test MAC: {mac}")
            
            # Try to get token
            print(f"Attempting to get token for MAC {mac} with credentials")
            try:
                token = provider.get_token(portal, mac)
                print(f"SUCCESS! Token received: {token}")
            except Exception as e:
                print(f"FAILED! Error: {str(e)}")
            
            # Test without credentials
            print("\n=== Testing without credentials ===")
            portal_no_creds = portal.copy()
            if 'username' in portal_no_creds:
                del portal_no_creds['username']
            if 'password' in portal_no_creds:
                del portal_no_creds['password']
            
            print(f"Attempting to get token for MAC {mac} without credentials")
            try:
                token = provider.get_token(portal_no_creds, mac)
                print(f"SUCCESS! Token received: {token}")
            except Exception as e:
                print(f"FAILED! Error: {str(e)}")
            
        else:
            print("No test_stalker portal found in portals.json")
            print("Available portals: " + ", ".join(portals.keys()))
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 