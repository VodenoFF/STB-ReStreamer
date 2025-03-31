# Portal WebSocket Events

This document provides details on WebSocket events related to portal management in STB-ReStreamer. WebSockets enable real-time updates and notifications about portal status and operations.

## Connecting to the WebSocket Server

To connect to the WebSocket server:

```javascript
// Using the Socket.IO client library
const socket = io.connect('http://your-server-address:5000');

// Listen for portal events
socket.on('portal_status_change', function(data) {
  console.log('Portal status changed:', data);
});
```

## Available Portal Events

### `portal_status_change`

Emitted when a portal's status changes (UP, DOWN, or DISABLED).

**Payload:**

```json
{
  "portal_id": "123",
  "status": "UP", 
  "name": "Example Portal",
  "timestamp": "2025-03-28T16:45:00Z"
}
```

- `portal_id`: Unique identifier of the portal
- `status`: New status of the portal (UP, DOWN, or DISABLED)
- `name`: Portal name
- `timestamp`: ISO 8601 timestamp of when the status changed

### `portal_test_result`

Emitted when a portal connection test is completed.

**Payload:**

```json
{
  "portal_id": "123",
  "success": true,
  "message": "Connection successful",
  "details": {
    "response_time": 1200,
    "channels_found": 152
  },
  "timestamp": "2025-03-28T16:46:00Z"
}
```

- `portal_id`: Unique identifier of the portal
- `success`: Boolean indicating if the test was successful
- `message`: Human-readable message about the test result
- `details`: Object containing additional test details
- `timestamp`: ISO 8601 timestamp of when the test completed

### `portal_created`

Emitted when a new portal is created in the system.

**Payload:**

```json
{
  "portal_id": "123",
  "name": "New Portal",
  "type": "stalker",
  "url": "http://example.com/stalker_portal",
  "status": "DOWN",
  "timestamp": "2025-03-28T16:47:00Z"
}
```

### `portal_updated`

Emitted when an existing portal is updated.

**Payload:**

```json
{
  "portal_id": "123",
  "name": "Updated Portal Name",
  "changes": ["name", "max_connections"],
  "timestamp": "2025-03-28T16:48:00Z"
}
```

- `changes`: Array of field names that were changed

### `portal_deleted`

Emitted when a portal is deleted from the system.

**Payload:**

```json
{
  "portal_id": "123",
  "name": "Deleted Portal",
  "timestamp": "2025-03-28T16:49:00Z"
}
```

### `test_all_started`

Emitted when a "Test All Portals" operation begins.

**Payload:**

```json
{
  "total_portals": 5,
  "timestamp": "2025-03-28T16:50:00Z"
}
```

### `test_all_progress`

Emitted during a "Test All Portals" operation to provide progress updates.

**Payload:**

```json
{
  "completed": 3,
  "total": 5,
  "current_portal_name": "Example Portal",
  "current_portal_id": "123",
  "timestamp": "2025-03-28T16:51:00Z"
}
```

### `test_all_completed`

Emitted when a "Test All Portals" operation is completed.

**Payload:**

```json
{
  "total_portals": 5,
  "success_count": 4,
  "failed_count": 1,
  "duration_ms": 12500,
  "timestamp": "2025-03-28T16:52:00Z"
}
```

## Client Implementation Example

Here's an example of how to implement a client that listens for portal events:

```javascript
// Connect to WebSocket server
const socket = io.connect('http://your-server-address:5000');

// Listen for portal status changes
socket.on('portal_status_change', function(data) {
  // Update UI to show new portal status
  updatePortalStatus(data.portal_id, data.status);
});

// Listen for test results
socket.on('portal_test_result', function(data) {
  // Display test result notification
  showTestResult(data.portal_id, data.success, data.message);
});

// "Test All" progress tracking
socket.on('test_all_started', function(data) {
  // Initialize progress UI
  initProgressBar(data.total_portals);
});

socket.on('test_all_progress', function(data) {
  // Update progress UI
  updateProgressBar(data.completed, data.total);
});

socket.on('test_all_completed', function(data) {
  // Show completion message and summary
  showCompletionSummary(data.success_count, data.failed_count);
});

// Example UI update functions
function updatePortalStatus(portalId, status) {
  const statusElement = document.querySelector(`#portal-${portalId} .status`);
  if (statusElement) {
    statusElement.className = `status ${status.toLowerCase()}`;
    statusElement.textContent = status;
  }
}

function showTestResult(portalId, success, message) {
  const notification = document.createElement('div');
  notification.className = `notification ${success ? 'success' : 'error'}`;
  notification.textContent = message;
  document.querySelector('#notifications').appendChild(notification);
  
  // Auto-remove notification after 5 seconds
  setTimeout(() => notification.remove(), 5000);
}
```

## Error Handling

If an error occurs with the WebSocket connection, the client should implement appropriate reconnection logic:

```javascript
socket.on('disconnect', function() {
  console.log('Disconnected from server. Attempting to reconnect...');
  // You might want to show a visual indicator that real-time updates are unavailable
});

socket.on('connect_error', function(error) {
  console.error('Connection error:', error);
  // Implement exponential backoff or other reconnection strategies
});
```

## Rate Limiting and Throttling

The WebSocket server implements rate limiting to prevent excessive event emissions. If many status changes happen simultaneously, events may be batched together to reduce network traffic.

## Compatibility Notes

- The WebSocket API requires browsers with WebSocket support (all modern browsers)
- For older browsers, Socket.IO provides fallback mechanisms to long polling
- Mobile applications can use native WebSocket clients or Socket.IO client libraries 