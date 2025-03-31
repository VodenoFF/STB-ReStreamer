#!/usr/bin/env python3
"""
Test the StalkerProvider class implementation directly without making network requests
"""
import os
import sys
import re

def main():
    """
    Parse and analyze the StalkerProvider class without importing it
    """
    print("=== Analyzing StalkerProvider Authentication Implementation ===")
    
    # Path to the stalker_provider.py file
    provider_path = os.path.join('src', 'services', 'portal_providers', 'stalker_provider.py')
    
    try:
        # Read the provider file content
        with open(provider_path, 'r') as f:
            content = f.read()
        
        print(f"File size: {len(content)} bytes")
        
        # Extract the authentication code block
        auth_block_pattern = r'# Step 3: Authenticate with MAC.*?# Parse response'
        auth_block_match = re.search(auth_block_pattern, content, re.DOTALL)
        
        if auth_block_match:
            auth_block = auth_block_match.group(0)
            print("\nFound authentication code block:")
            print("-" * 50)
            print(auth_block)
            print("-" * 50)
            
            # Check for credential condition
            cred_check = re.search(r'if portal\.get\([\'"]username[\'"]\).*?portal\.get\([\'"]password[\'"]\)', auth_block)
            
            if cred_check:
                print("\n✅ Found credential check: " + cred_check.group(0))
                
                # Check username assignment
                username_set = re.search(r'params\[[\'"]login[\'"]\] = portal\.get\([\'"]username[\'"]\)', auth_block)
                if username_set:
                    print("✅ Sets login parameter to username: " + username_set.group(0))
                else:
                    print("❌ Does not set login parameter to username")
                
                # Check password assignment
                password_set = re.search(r'params\[[\'"]password[\'"]\] = portal\.get\([\'"]password[\'"]\)', auth_block)
                if password_set:
                    print("✅ Sets password parameter to password: " + password_set.group(0))
                else:
                    print("❌ Does not set password parameter to password")
                
                # Check MAC fallback (else branch)
                mac_fallback = re.search(r'else:.*?params\[[\'"]login[\'"]\] = mac_formatted', auth_block, re.DOTALL)
                if mac_fallback:
                    print("\n✅ Has MAC fallback mechanism")
                else:
                    print("\n❌ Missing MAC fallback mechanism")
                
                # Check logging
                log_creds = re.search(r'logger\.info.*username/password authentication', auth_block)
                log_mac = re.search(r'logger\.info.*MAC-only authentication', auth_block)
                
                if log_creds and log_mac:
                    print("\n✅ Has logging for both authentication methods")
                else:
                    print("\n❌ Missing logging for authentication methods")
                
                # Overall assessment
                if username_set and password_set and mac_fallback and log_creds and log_mac:
                    print("\n✅ AUTHENTICATION FIX IS CORRECTLY IMPLEMENTED")
                    print("The code properly checks for credentials and uses them when available,")
                    print("with a fallback to MAC-only authentication when credentials are missing.")
                else:
                    print("\n⚠️ AUTHENTICATION FIX MAY BE INCOMPLETE")
                    print("Check the implementation details above for what might be missing.")
            else:
                print("\n❌ NO CREDENTIAL CHECK FOUND")
                print("The code does not appear to check for username and password credentials.")
        else:
            print("\n❌ Could not find the authentication code block")
            print("The authentication step might have been significantly altered or removed.")
    
    except Exception as e:
        print(f"\nError analyzing file: {str(e)}")

if __name__ == "__main__":
    main() 