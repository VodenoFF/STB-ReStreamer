#!/usr/bin/env python3
"""
Test script for STB-ReStreamer authentication.
This will print the credentials being used from the config.
"""
import json
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from src.models.config import ConfigManager
from src.utils.auth import AuthManager

def inspect_config(config):
    """Print detailed info about a config dictionary"""
    print(f"Config type: {type(config)}")
    print(f"Config keys: {list(config.keys())}")
    for key in ['username', 'password', 'admin_username', 'admin_password']:
        print(f"Config['{key}'] exists: {key in config}")
        if key in config:
            print(f"  Value: {config[key]} (type: {type(config[key])})")

def main():
    print("STB-ReStreamer Authentication Test")
    print("==================================")
    
    # Load the current config
    print("Loading configuration...")
    config_file = "config.json"
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            print(f"Raw config contents: {json.dumps(config_data, indent=2)}")
            print("\nInspecting raw config:")
            inspect_config(config_data)
    except Exception as e:
        print(f"Error reading config file: {e}")
        sys.exit(1)
    
    # Initialize managers
    print("\nInitializing config manager...")
    config_manager = ConfigManager(config_file)
    
    # Get all settings and inspect
    all_settings = config_manager.get_all_settings()
    print("\nInspecting config_manager.get_all_settings():")
    inspect_config(all_settings)
    
    # Try direct config access
    print("\nTrying direct config access:")
    username_direct = config_manager.config.get("username", "NOT_FOUND")
    password_direct = config_manager.config.get("password", "NOT_FOUND")
    admin_username_direct = config_manager.config.get("admin_username", "NOT_FOUND")
    admin_password_direct = config_manager.config.get("admin_password", "NOT_FOUND")
    
    print(f"Direct username: {username_direct}")
    print(f"Direct password: {password_direct}")
    print(f"Direct admin_username: {admin_username_direct}")
    print(f"Direct admin_password: {admin_password_direct}")
    
    # Get credentials via ConfigManager's methods
    print("\nUsing config_manager.get_setting():")
    old_username = config_manager.get_setting("username")
    old_password = config_manager.get_setting("password")
    admin_username_setting = config_manager.get_setting("admin_username")
    admin_password_setting = config_manager.get_setting("admin_password")
    
    print(f"username: {old_username}")
    print(f"password: {old_password}")
    print(f"admin_username: {admin_username_setting}")
    print(f"admin_password: {admin_password_setting}")
    
    print("\nUsing config_manager.get():")
    admin_username = config_manager.get("admin_username", "ADMIN_DEFAULT")
    admin_password = config_manager.get("admin_password", "ADMIN_DEFAULT")
    
    print(f"admin_username: {admin_username}")
    print(f"admin_password: {admin_password}")
    
    # For debugging, explicitly set the admin values 
    print("\nTrying to set admin credentials explicitly...")
    config_manager.set_setting("admin_username", "admin")
    config_manager.set_setting("admin_password", "admin")
    
    # Get values again after setting
    print("\nAfter setting, using config_manager.get():")
    admin_username_after = config_manager.get("admin_username", "ADMIN_DEFAULT")
    admin_password_after = config_manager.get("admin_password", "ADMIN_DEFAULT")
    
    print(f"admin_username: {admin_username_after}")
    print(f"admin_password: {admin_password_after}")
    
    # Print credential info
    print("\nCredential Information Summary:")
    print(f"Old-style credentials (username/password):")
    print(f"  Username: {old_username}")
    print(f"  Password: {old_password}")
    
    print(f"\nNew-style credentials (admin_username/admin_password):")
    print(f"  Admin Username: {admin_username_after}")
    print(f"  Admin Password: {admin_password_after}")
    
    # Initialize auth manager
    print("\nInitializing auth manager...")
    auth_manager = AuthManager(config_manager)
    
    # Test a login
    test_username = "admin"
    test_password = "admin"
    print(f"\nTesting login with: {test_username} / {test_password}")
    success, token, error = auth_manager.login(test_username, test_password, "127.0.0.1")
    if success:
        print(f"Login successful! Token: {token[:10]}...")
    else:
        print(f"Login failed! Error: {error}")
    
    # Test again with other potential credentials
    test_username = "admin"
    test_password = "12345"
    print(f"\nTesting login with: {test_username} / {test_password}")
    success, token, error = auth_manager.login(test_username, test_password, "127.0.0.2")
    if success:
        print(f"Login successful! Token: {token[:10]}...")
    else:
        print(f"Login failed! Error: {error}")
    
    print("\nTest complete.")

if __name__ == "__main__":
    main() 