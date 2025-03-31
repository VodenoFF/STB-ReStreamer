# Stalker/Ministra Authentication Fix

## Issue Description

The application was failing to authenticate with Stalker/Ministra portals when credentials (username and password) were required. Instead of using the provided credentials, it was attempting to authenticate using only the MAC address, resulting in authentication failures.

Error message:
```
Authentication error: Login and password required
```

## Fix Implementation

We updated the `get_token` method in the `StalkerProvider` class (located in `src/services/portal_providers/stalker_provider.py`) to properly handle username and password authentication.

### Changes Made:

1. Added a condition to check if username and password credentials are provided in the portal configuration:
   ```python
   if portal.get('username') and portal.get('password'):
   ```

2. When credentials are available, use them for authentication:
   ```python
   # Use username/password authentication
   params['login'] = portal.get('username')
   params['password'] = portal.get('password')
   params['device_id'] = mac_formatted
   params['device_id2'] = mac_formatted
   logger.info(f"Using username/password authentication for MAC {mac_formatted}")
   ```

3. Added a fallback to MAC-only authentication when credentials are not available:
   ```python
   # Fallback to MAC-only authentication
   params['login'] = mac_formatted
   params['password'] = ''
   params['device_id'] = ''
   params['device_id2'] = ''
   logger.info(f"Using MAC-only authentication for {mac_formatted}")
   ```

4. Added appropriate logging to track which authentication method is being used

## Testing

We created a test script (`test_stalker_provider.py`) to verify the authentication code implementation. The test confirmed that:

1. The code correctly checks for username and password credentials
2. When credentials are available, it uses them for authentication
3. When credentials are not available, it falls back to MAC-only authentication
4. Proper logging is in place for both authentication scenarios

## Portal Configuration

For Stalker/Ministra portals that require username and password authentication, the portal configuration should include the credentials:

```json
{
  "id": "stalker_portal",
  "name": "Stalker Portal",
  "type": "stalker",
  "url": "http://portal-url.com",
  "username": "your_username",
  "password": "your_password",
  "macs": {
    "00:1A:79:00:00:01": {
      "serial": "012345",
      "device_id": "012345",
      "device_id2": "012345"
    }
  },
  "enabled": true
}
```

## Notes

- This authentication method also applies to Ministra portals, as they use the same authentication mechanism as Stalker portals.
- The code will now detect and use either authentication method automatically based on the portal configuration.
- Existing portals that use MAC-only authentication will continue to work without modification.
- New portals that require username/password authentication should include the username and password fields. 