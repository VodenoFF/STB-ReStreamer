# STB-ReStreamer API Documentation

Welcome to the STB-ReStreamer API documentation. This section describes the RESTful API endpoints, WebSocket events, and data models that can be used to interact with STB-ReStreamer programmatically.

## API Overview

STB-ReStreamer provides several APIs for different purposes:

1. **REST API**: Traditional HTTP endpoints for management and data retrieval
2. **WebSocket API**: Real-time events and updates
3. **HDHomeRun API**: Emulation of HDHomeRun device API for integration with third-party applications

## Authentication

Most API endpoints require authentication. STB-ReStreamer supports:

- Session-based authentication (using cookies)
- API key authentication (using the `X-API-Key` header)

See the [Authentication](authentication.md) page for details.

## REST API

The REST API allows you to manage and interact with STB-ReStreamer using standard HTTP methods.

### Endpoints

- [Portals API](rest/portals.md): Manage IPTV portals
- [Channels API](rest/channels.md): Access channel information
- [Streams API](rest/streams.md): Control and query streams
- [Categories API](rest/categories.md): Manage channel categories
- [EPG API](rest/epg.md): Access EPG data
- [System API](rest/system.md): Configure and monitor the system

### Response Format

All API responses are in JSON format and include:

- HTTP status code
- Response body with data or error information
- Standard headers

Example successful response:

```json
{
  "success": true,
  "data": {
    "id": "123456",
    "name": "Example Portal"
  }
}
```

Example error response:

```json
{
  "success": false,
  "error": {
    "code": "not_found",
    "message": "Portal not found"
  }
}
```

## WebSocket API

The WebSocket API provides real-time updates for various aspects of STB-ReStreamer.

### Events

- [Stream Events](websocket/stream-events.md): Real-time stream status updates
- [Portal Events](websocket/portal-events.md): Portal connection status events
- [System Events](websocket/system-events.md): System-wide notifications

### Connection

To connect to the WebSocket API:

1. Connect to `ws://your-server:8001/socket.io/` using a Socket.IO client
2. Authenticate using the same session or API key used for REST API
3. Subscribe to specific events of interest

Example with JavaScript:

```javascript
const socket = io('http://your-server:8001');

socket.on('connect', () => {
  console.log('Connected to WebSocket');
  socket.emit('request_status'); // Request initial status
});

socket.on('stream_status_update', (data) => {
  console.log('Stream status update:', data);
});

socket.on('portal_status_update', (data) => {
  console.log('Portal status update:', data);
});
```

## HDHomeRun Emulation API

STB-ReStreamer emulates the HDHomeRun API to allow integration with compatible applications like Plex, Emby, and Channels DVR.

See the [HDHomeRun API](hdhr/index.md) documentation for details.

## Data Models

The following data models are used throughout the STB-ReStreamer API:

- [Portal Model](models/portal.md): IPTV portal configuration
- [Channel Model](models/channel.md): Channel information
- [Stream Model](models/stream.md): Stream status and configuration
- [Category Model](models/category.md): Channel category
- [EPG Model](models/epg.md): Electronic Program Guide data

## API Versioning

The current API version is v1. The version is included in the URL path:

```
/api/v1/resource
```

## Rate Limiting

API requests are subject to rate limiting to prevent abuse. By default:

- 30 requests per minute for authenticated requests
- 5 requests per minute for unauthenticated requests

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 29
X-RateLimit-Reset: 1619712000
```

## Error Codes

Common error codes you may encounter:

- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## API Examples

For practical examples of using the API, see the [Examples](examples/index.md) section. 