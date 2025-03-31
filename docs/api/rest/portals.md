# Portal Management REST API

This document describes the REST API endpoints for managing IPTV portals in STB-ReStreamer.

## Base URL

All API endpoints are relative to the base URL:

```
http://your-server-address:5000/api/v1
```

## Authentication

All API requests require authentication. You can use one of the following methods:

1. **Session-based Authentication**: Include cookies from browser login
2. **API Key Authentication**: Include the API key in the `X-API-Key` header

For more details, see the [Authentication](/docs/api/authentication.md) documentation.

## Portal Endpoints

### List All Portals

Retrieves a list of all configured portals.

**Endpoint:** `GET /portals`

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | (Optional) Filter by status: `up`, `down`, or `disabled` |
| `type` | string | (Optional) Filter by portal type: `stalker`, `xtream`, `m3u`, etc. |
| `limit` | integer | (Optional) Limit the number of results (default: 100) |
| `offset` | integer | (Optional) Offset for pagination (default: 0) |

**Response:**

```json
{
  "success": true,
  "count": 2,
  "total": 2,
  "data": [
    {
      "id": "1",
      "name": "Main Stalker Portal",
      "type": "stalker",
      "url": "http://example.com/stalker_portal",
      "mac": "00:1A:79:XX:XX:XX",
      "status": "up",
      "max_connections": 1,
      "enabled": true,
      "created_at": "2025-03-01T12:00:00Z",
      "updated_at": "2025-03-28T16:00:00Z",
      "last_check": "2025-03-28T16:30:00Z"
    },
    {
      "id": "2",
      "name": "Backup M3U Portal",
      "type": "m3u",
      "url": "http://example.com/playlist.m3u8",
      "epg_url": "http://example.com/epg.xml",
      "status": "up",
      "max_connections": 2,
      "enabled": true,
      "created_at": "2025-03-15T14:00:00Z",
      "updated_at": "2025-03-28T15:00:00Z",
      "last_check": "2025-03-28T16:30:00Z"
    }
  ]
}
```

### Get Portal Details

Retrieves details for a specific portal.

**Endpoint:** `GET /portals/{portal_id}`

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "1",
    "name": "Main Stalker Portal",
    "type": "stalker",
    "url": "http://example.com/stalker_portal",
    "mac": "00:1A:79:XX:XX:XX",
    "status": "up",
    "max_connections": 1,
    "username": "user123",
    "password": "•••••••",  // Passwords are masked in responses
    "http_proxy": "",
    "enabled": true,
    "options": {
      "timeout": 30,
      "retries": 3
    },
    "created_at": "2025-03-01T12:00:00Z",
    "updated_at": "2025-03-28T16:00:00Z",
    "last_check": "2025-03-28T16:30:00Z"
  }
}
```

### Create Portal

Creates a new portal.

**Endpoint:** `POST /portals`

**Request Body:**

```json
{
  "name": "New Portal",
  "type": "stalker",
  "url": "http://example.com/stalker_portal",
  "mac": "00:1A:79:XX:XX:XX", 
  "max_connections": 1,
  "username": "user123",  // Optional depending on portal type
  "password": "pass123",  // Optional depending on portal type
  "http_proxy": "",       // Optional
  "enabled": true,
  "options": {            // Optional portal-specific options
    "timeout": 30,
    "retries": 3
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Portal created successfully",
  "data": {
    "id": "3",
    "name": "New Portal",
    "type": "stalker",
    "url": "http://example.com/stalker_portal",
    "mac": "00:1A:79:XX:XX:XX",
    "status": "unknown",
    "max_connections": 1,
    "enabled": true,
    "created_at": "2025-03-28T17:00:00Z",
    "updated_at": "2025-03-28T17:00:00Z"
  }
}
```

### Update Portal

Updates an existing portal.

**Endpoint:** `PUT /portals/{portal_id}`

**Request Body:**

```json
{
  "name": "Updated Portal Name",
  "max_connections": 2,
  "enabled": true
  // Include only fields that need to be updated
}
```

**Response:**

```json
{
  "success": true,
  "message": "Portal updated successfully",
  "data": {
    "id": "1",
    "name": "Updated Portal Name",
    "type": "stalker",
    "url": "http://example.com/stalker_portal",
    "mac": "00:1A:79:XX:XX:XX",
    "status": "up",
    "max_connections": 2,
    "enabled": true,
    "updated_at": "2025-03-28T17:30:00Z"
  }
}
```

### Delete Portal

Deletes a portal.

**Endpoint:** `DELETE /portals/{portal_id}`

**Response:**

```json
{
  "success": true,
  "message": "Portal deleted successfully"
}
```

### Test Portal Connection

Tests the connection to a portal.

**Endpoint:** `POST /portals/{portal_id}/test`

**Response:**

```json
{
  "success": true,
  "message": "Portal connection test successful",
  "data": {
    "status": "up",
    "response_time_ms": 1200,
    "channels_found": 152,
    "details": {
      "server_version": "5.6.0",
      "authentication": "successful",
      "channel_categories": 12
    }
  }
}
```

### Test All Portals

Tests the connection to all enabled portals.

**Endpoint:** `POST /portals/test-all`

**Response:**

```json
{
  "success": true,
  "message": "Test all portals initiated",
  "data": {
    "operation_id": "test-all-20250328-175000",
    "total_portals": 5
  }
}
```

Note: This operation runs asynchronously. Results are delivered via WebSocket events. See the [WebSocket API documentation](/docs/api/websocket/portal-events.md) for details.

### Get Portal Status

Retrieves the current status of a portal.

**Endpoint:** `GET /portals/{portal_id}/status`

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "1",
    "name": "Main Stalker Portal",
    "status": "up",
    "last_check": "2025-03-28T17:45:00Z",
    "details": {
      "response_time_ms": 850,
      "uptime_percentage": 99.8,
      "channels_available": 152
    }
  }
}
```

### Enable/Disable Portal

Enables or disables a portal.

**Endpoint:** `PUT /portals/{portal_id}/toggle`

**Request Body:**

```json
{
  "enabled": false
}
```

**Response:**

```json
{
  "success": true,
  "message": "Portal disabled successfully",
  "data": {
    "id": "1",
    "name": "Main Stalker Portal",
    "status": "disabled",
    "enabled": false,
    "updated_at": "2025-03-28T18:00:00Z"
  }
}
```

## Error Responses

### Invalid Request

```json
{
  "success": false,
  "error": "invalid_request",
  "message": "The request was invalid",
  "details": {
    "name": ["This field is required"],
    "url": ["Invalid URL format"]
  }
}
```

### Portal Not Found

```json
{
  "success": false,
  "error": "not_found",
  "message": "Portal with ID 999 not found"
}
```

### Authentication Error

```json
{
  "success": false,
  "error": "unauthorized",
  "message": "Authentication required"
}
```

### Server Error

```json
{
  "success": false,
  "error": "server_error",
  "message": "An internal server error occurred"
}
```

## Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid request parameters |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource conflict |
| 500 | Internal Server Error - Server error |

## Rate Limiting

API endpoints are rate limited to prevent abuse. The current limits are:

- 60 requests per minute for authenticated users
- 30 requests per minute for API key users

When a rate limit is exceeded, the API will respond with a 429 status code.

## Pagination

List endpoints support pagination using the `limit` and `offset` parameters. The response includes:

- `count`: Number of items returned in this response
- `total`: Total number of items available

## Filtering

List endpoints support filtering using query parameters. For the portals endpoint:

- `status`: Filter by portal status (`up`, `down`, `disabled`)
- `type`: Filter by portal type (`stalker`, `xtream`, `m3u`, etc.)

Example: `GET /portals?status=up&type=stalker` 