#!/usr/bin/env python3
"""
Test script for the fixed authentication manager.
"""
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from src.models.config import ConfigManager
from auth_fixed import FixedAuthManager

def main():
    print("Fixed AuthManager Test")
    print("=====================")
    
    # Load the current config
    print("Loading configuration...")
    config_file = "config.json"
    
    # Initialize managers
    print("\nInitializing config manager...")
    config_manager = ConfigManager(config_file)
    
    # Get credentials via ConfigManager's methods
    print("\nCredentials from config_manager.get_setting():")
    username = config_manager.get_setting("username", "DEFAULT")
    password = config_manager.get_setting("password", "DEFAULT")
    admin_username = config_manager.get_setting("admin_username", "DEFAULT")
    admin_password = config_manager.get_setting("admin_password", "DEFAULT")
    
    print(f"username: {username}")
    print(f"password: {password}")
    print(f"admin_username: {admin_username}")
    print(f"admin_password: {admin_password}")
    
    # Initialize fixed auth manager
    print("\nInitializing fixed auth manager...")
    auth_manager = FixedAuthManager(config_manager)
    
    # Test login with various credential combinations
    test_credentials = [
        ("admin", "admin"),
        ("admin", "12345"),
        (admin_username, admin_password),  # Should always work
    ]
    
    for username, password in test_credentials:
        print(f"\nTesting login with: {username} / {password}")
        success, token, error = auth_manager.login(username, password, "127.0.0.1")
        if success:
            print(f"✅ Login successful! Token: {token[:10]}...")
        else:
            print(f"❌ Login failed! Error: {error}")
    
    print("\nTest complete.")

if __name__ == "__main__":
    main() 