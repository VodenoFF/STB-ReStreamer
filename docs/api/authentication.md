# API Authentication

This document describes the authentication methods supported by the STB-ReStreamer API.

## Overview

STB-ReStreamer provides two authentication methods for API access:

1. **Session-based Authentication**: For web browser clients and applications that maintain session state
2. **API Key Authentication**: For scripts, integrations, and applications that need programmatic access

## Session-based Authentication

Session-based authentication uses cookies and is primarily designed for the web interface. When a user logs in via the web interface, a session is created and maintained using cookies.

### Login Endpoint

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**

```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Authentication successful",
  "data": {
    "username": "admin",
    "roles": ["admin"],
    "session_expires": "2025-03-29T16:00:00Z"
  }
}
```

### Session Verification

To verify if a session is active:

**Endpoint:** `GET /api/v1/auth/session`

**Response (Active Session):**

```json
{
  "success": true,
  "data": {
    "authenticated": true,
    "username": "admin",
    "roles": ["admin"],
    "session_expires": "2025-03-29T16:00:00Z"
  }
}
```

**Response (No Active Session):**

```json
{
  "success": true,
  "data": {
    "authenticated": false
  }
}
```

### Logout

**Endpoint:** `POST /api/v1/auth/logout`

**Response:**

```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

## API Key Authentication

API key authentication uses a static API key to authenticate requests. This method is suitable for programmatic access, scripts, and integrations.

### API Key Generation

API keys are generated in the web interface under Settings > API Keys. Users with admin roles can create, view, and revoke API keys.

### Using API Keys

To authenticate with an API key, include it in the `X-API-Key` header:

```
X-API-Key: your-api-key-here
```

Example cURL request:

```bash
curl -X GET http://your-server-address:5000/api/v1/portals \
  -H "X-API-Key: your-api-key-here"
```

### API Key Validation

To verify if an API key is valid:

**Endpoint:** `GET /api/v1/auth/verify-key`

**Headers:**

```
X-API-Key: your-api-key-here
```

**Response (Valid Key):**

```json
{
  "success": true,
  "data": {
    "valid": true,
    "name": "My API Key",
    "created_at": "2025-03-01T12:00:00Z",
    "permissions": ["read", "write"],
    "expires": null
  }
}
```

**Response (Invalid Key):**

```json
{
  "success": false,
  "error": "invalid_api_key",
  "message": "The provided API key is invalid or expired"
}
```

## API Key Management

### List API Keys

Lists all API keys for the current user (admin only).

**Endpoint:** `GET /api/v1/auth/api-keys`

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "1",
      "name": "Automation Script Key",
      "last_used": "2025-03-28T15:00:00Z",
      "created_at": "2025-03-01T12:00:00Z",
      "expires": null,
      "permissions": ["read", "write"]
    },
    {
      "id": "2",
      "name": "Monitoring System",
      "last_used": "2025-03-28T16:30:00Z",
      "created_at": "2025-03-15T09:00:00Z",
      "expires": "2025-06-15T09:00:00Z",
      "permissions": ["read"]
    }
  ]
}
```

### Create API Key

Creates a new API key.

**Endpoint:** `POST /api/v1/auth/api-keys`

**Request Body:**

```json
{
  "name": "New API Key",
  "permissions": ["read", "write"],
  "expires": "2025-12-31T23:59:59Z"  // Optional, null for no expiration
}
```

**Response:**

```json
{
  "success": true,
  "message": "API key created successfully",
  "data": {
    "id": "3",
    "name": "New API Key",
    "key": "STB-5f9c1b2a3d8e7f6g",  // Full key is only shown once
    "created_at": "2025-03-28T17:00:00Z",
    "expires": "2025-12-31T23:59:59Z",
    "permissions": ["read", "write"]
  }
}
```

**Important**: The full API key is only returned once when it's created. Store it securely.

### Revoke API Key

Revokes (deletes) an API key.

**Endpoint:** `DELETE /api/v1/auth/api-keys/{key_id}`

**Response:**

```json
{
  "success": true,
  "message": "API key revoked successfully"
}
```

## Permission Levels

The API supports the following permission levels:

- **read**: Allows read-only access to data
- **write**: Allows modification of data
- **admin**: Allows all operations, including API key management
- **stream**: Allows stream control (start/stop/monitor)

## Authentication Errors

### Unauthorized

Returned when no authentication is provided:

```json
{
  "success": false,
  "error": "unauthorized",
  "message": "Authentication required"
}
```

### Invalid Credentials

Returned for invalid login credentials:

```json
{
  "success": false,
  "error": "invalid_credentials",
  "message": "Invalid username or password"
}
```

### Insufficient Permissions

Returned when the authenticated user or API key doesn't have sufficient permissions:

```json
{
  "success": false,
  "error": "forbidden",
  "message": "Insufficient permissions to perform this action"
}
```

## Security Best Practices

1. **Use HTTPS**: Always secure your STB-ReStreamer instance with HTTPS in production.
2. **Regular Key Rotation**: Rotate API keys regularly (every 90 days is recommended).
3. **Secure Storage**: Store API keys securely in your client applications.
4. **Unique Keys per Integration**: Use separate API keys for each integration or script.
5. **Limited Scope**: Grant each API key only the permissions it needs.
6. **Monitor Usage**: Regularly review API key usage in the logs.
7. **Set Expirations**: Use expiration dates for API keys when possible.
8. **Revoke Unused Keys**: Regularly audit and revoke unused API keys.

## Rate Limiting

Authentication endpoints are rate limited to prevent brute force attacks:

- Login attempts are limited to 5 attempts per 15 minutes from the same IP address
- Failed API key authentications are limited to 10 attempts per minute from the same IP address

## Session Configuration

Session configuration can be customized in the application settings:

- **Session Duration**: Default is 24 hours
- **Remember Me Duration**: Default is 30 days when "Remember Me" is checked
- **Session Storage**: Default is server-side with a client cookie reference 