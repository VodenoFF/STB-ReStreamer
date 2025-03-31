#!/usr/bin/env python3
"""
Direct test for Stalker provider authentication
"""
import sys
import json
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("test-auth-direct")

def main():
    """
    Test the portal authentication directly using HTTP requests
    """
    print("=== Testing Portal Authentication Directly ===")
    
    try:
        # Load portal configuration
        with open('portals.json', 'r') as f:
            portals = json.load(f)
        
        for portal_id, portal in portals.items():
            print(f"\nTesting portal: {portal['name']} (type: {portal.get('type')})")
            
            # Skip non-stalker portals
            if portal.get('type') not in ['stalker', 'ministra']:
                print(f"Skipping non-stalker/ministra portal")
                continue
            
            # Check if credentials exist
            if portal.get('username') and portal.get('password'):
                print(f"Portal has credentials: {portal['username']} / {portal['password']}")
            else:
                print("Portal does not have credentials")
            
            # Get a MAC address
            if not portal.get('macs'):
                print("Portal has no MACs defined, skipping")
                continue
            
            mac = next(iter(portal.get('macs', {})))
            print(f"Using MAC: {mac}")
            
            # Test direct API call for checking fix
            # We'll simulate the handshake + authenticate process
            base_url = portal.get('url')
            if not base_url:
                print("Portal has no URL defined, skipping")
                continue
            
            print(f"Testing URL: {base_url}")
            
            # Step 1: Handshake
            handshake_url = f"{base_url}/stalker_portal/server/load.php"
            handshake_params = {
                'type': 'stb',
                'action': 'handshake',
                'token': '',
                'JsHttpRequest': '1-xml'
            }
            
            print("Step 1: Sending handshake request...")
            handshake_response = requests.get(handshake_url, params=handshake_params, timeout=10)
            
            if handshake_response.status_code != 200:
                print(f"Handshake failed: Status code {handshake_response.status_code}")
                continue
            
            try:
                handshake_data = handshake_response.json()
                print(f"Handshake successful. Response: {handshake_data}")
                
                # Extract token
                if 'js' in handshake_data and 'token' in handshake_data['js']:
                    token = handshake_data['js']['token']
                    print(f"Received token: {token}")
                else:
                    print("No token in handshake response")
                    continue
            except Exception as e:
                print(f"Error parsing handshake response: {str(e)}")
                continue
            
            # Step 2: Authentication
            auth_url = f"{base_url}/stalker_portal/server/load.php"
            
            # MAC formatting
            formatted_mac = mac.replace(':', '').lower()
            
            auth_params = {
                'type': 'stb',
                'action': 'do_auth',
                'token': token,
                'JsHttpRequest': '1-xml'
            }
            
            auth_headers = {
                'User-Agent': 'Mozilla/5.0 (QtEmbedded; U; Linux; C)',
                'Cookie': f'mac={formatted_mac}; stb_lang=en; timezone=Europe/London'
            }
            
            # Test with both username/password and MAC-only authentication
            auth_tests = [
                {"name": "With credentials", "use_creds": True},
                {"name": "MAC-only", "use_creds": False}
            ]
            
            for test in auth_tests:
                print(f"\nStep 2: {test['name']} authentication...")
                
                if test['use_creds'] and portal.get('username') and portal.get('password'):
                    auth_data = {
                        'login': portal['username'],
                        'password': portal['password'],
                        'device_id': "",
                        'device_id2': ""
                    }
                    print(f"Using username/password: {portal['username']} / {portal['password']}")
                else:
                    auth_data = {
                        'login': formatted_mac,
                        'password': "",
                        'device_id': "",
                        'device_id2': ""
                    }
                    print(f"Using MAC-only authentication: {formatted_mac}")
                
                auth_response = requests.post(
                    auth_url, 
                    params=auth_params, 
                    headers=auth_headers, 
                    data=auth_data,
                    timeout=10
                )
                
                if auth_response.status_code != 200:
                    print(f"Authentication failed: Status code {auth_response.status_code}")
                    continue
                
                try:
                    auth_data = auth_response.json()
                    print(f"Authentication response: {auth_data}")
                    
                    if 'js' in auth_data:
                        if auth_data.get('js') is False:
                            print("Authentication failed: Server returned False")
                        else:
                            print("Authentication successful!")
                    else:
                        print("No 'js' data in authentication response")
                except Exception as e:
                    print(f"Error parsing authentication response: {str(e)}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 