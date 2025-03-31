# Portal Management API Examples

This document provides practical examples of using the STB-ReStreamer API for portal management.

## Prerequisites

- STB-ReStreamer server running and accessible
- API key with appropriate permissions (or user credentials)
- A tool or library for making HTTP requests (examples use cURL and JavaScript)

## Example 1: List All Portals

### Using cURL

```bash
curl -X GET "http://your-server-address:5000/api/v1/portals" \
  -H "X-API-Key: your-api-key-here"
```

### Using JavaScript (Fetch API)

```javascript
async function listPortals() {
  const response = await fetch('http://your-server-address:5000/api/v1/portals', {
    method: 'GET',
    headers: {
      'X-API-Key': 'your-api-key-here'
    }
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`Found ${data.count} portals:`);
    data.data.forEach(portal => {
      console.log(`- ${portal.name} (${portal.type}): ${portal.status}`);
    });
  } else {
    console.error(`Error: ${data.message}`);
  }
}

listPortals();
```

### Using Python (requests library)

```python
import requests

def list_portals():
    url = "http://your-server-address:5000/api/v1/portals"
    headers = {
        "X-API-Key": "your-api-key-here"
    }
    
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data["success"]:
        print(f"Found {data['count']} portals:")
        for portal in data["data"]:
            print(f"- {portal['name']} ({portal['type']}): {portal['status']}")
    else:
        print(f"Error: {data['message']}")

if __name__ == "__main__":
    list_portals()
```

## Example 2: Create a New Portal

### Using cURL

```bash
curl -X POST "http://your-server-address:5000/api/v1/portals" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Stalker Portal",
    "type": "stalker",
    "url": "http://example.com/stalker_portal",
    "mac": "00:1A:79:12:34:56",
    "max_connections": 1,
    "enabled": true
  }'
```

### Using JavaScript (Fetch API)

```javascript
async function createPortal() {
  const portalData = {
    name: "My Stalker Portal",
    type: "stalker",
    url: "http://example.com/stalker_portal",
    mac: "00:1A:79:12:34:56",
    max_connections: 1,
    enabled: true
  };
  
  const response = await fetch('http://your-server-address:5000/api/v1/portals', {
    method: 'POST',
    headers: {
      'X-API-Key': 'your-api-key-here',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(portalData)
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`Portal created successfully with ID: ${data.data.id}`);
  } else {
    console.error(`Error: ${data.message}`);
    if (data.details) {
      console.error('Details:', data.details);
    }
  }
}

createPortal();
```

### Using Python (requests library)

```python
import requests

def create_portal():
    url = "http://your-server-address:5000/api/v1/portals"
    headers = {
        "X-API-Key": "your-api-key-here",
        "Content-Type": "application/json"
    }
    
    portal_data = {
        "name": "My Stalker Portal",
        "type": "stalker",
        "url": "http://example.com/stalker_portal",
        "mac": "00:1A:79:12:34:56",
        "max_connections": 1,
        "enabled": True
    }
    
    response = requests.post(url, headers=headers, json=portal_data)
    data = response.json()
    
    if data["success"]:
        print(f"Portal created successfully with ID: {data['data']['id']}")
    else:
        print(f"Error: {data['message']}")
        if "details" in data:
            print("Details:", data["details"])

if __name__ == "__main__":
    create_portal()
```

## Example 3: Test Portal Connection

### Using cURL

```bash
curl -X POST "http://your-server-address:5000/api/v1/portals/1/test" \
  -H "X-API-Key: your-api-key-here"
```

### Using JavaScript (Fetch API)

```javascript
async function testPortal(portalId) {
  const response = await fetch(`http://your-server-address:5000/api/v1/portals/${portalId}/test`, {
    method: 'POST',
    headers: {
      'X-API-Key': 'your-api-key-here'
    }
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`Test result: ${data.message}`);
    console.log(`Status: ${data.data.status}`);
    console.log(`Response time: ${data.data.response_time_ms}ms`);
    console.log(`Channels found: ${data.data.channels_found}`);
  } else {
    console.error(`Error: ${data.message}`);
  }
}

// Test portal with ID 1
testPortal(1);
```

### Using Python (requests library)

```python
import requests

def test_portal(portal_id):
    url = f"http://your-server-address:5000/api/v1/portals/{portal_id}/test"
    headers = {
        "X-API-Key": "your-api-key-here"
    }
    
    response = requests.post(url, headers=headers)
    data = response.json()
    
    if data["success"]:
        print(f"Test result: {data['message']}")
        print(f"Status: {data['data']['status']}")
        print(f"Response time: {data['data']['response_time_ms']}ms")
        print(f"Channels found: {data['data']['channels_found']}")
    else:
        print(f"Error: {data['message']}")

if __name__ == "__main__":
    # Test portal with ID 1
    test_portal(1)
```

## Example 4: Update an Existing Portal

### Using cURL

```bash
curl -X PUT "http://your-server-address:5000/api/v1/portals/1" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Portal Name",
    "max_connections": 2
  }'
```

### Using JavaScript (Fetch API)

```javascript
async function updatePortal(portalId, updateData) {
  const response = await fetch(`http://your-server-address:5000/api/v1/portals/${portalId}`, {
    method: 'PUT',
    headers: {
      'X-API-Key': 'your-api-key-here',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(updateData)
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`Portal updated successfully: ${data.message}`);
  } else {
    console.error(`Error: ${data.message}`);
  }
}

// Update portal with ID 1
updatePortal(1, {
  name: "Updated Portal Name",
  max_connections: 2
});
```

### Using Python (requests library)

```python
import requests

def update_portal(portal_id, update_data):
    url = f"http://your-server-address:5000/api/v1/portals/{portal_id}"
    headers = {
        "X-API-Key": "your-api-key-here",
        "Content-Type": "application/json"
    }
    
    response = requests.put(url, headers=headers, json=update_data)
    data = response.json()
    
    if data["success"]:
        print(f"Portal updated successfully: {data['message']}")
    else:
        print(f"Error: {data['message']}")

if __name__ == "__main__":
    # Update portal with ID 1
    update_data = {
        "name": "Updated Portal Name",
        "max_connections": 2
    }
    update_portal(1, update_data)
```

## Example 5: Delete a Portal

### Using cURL

```bash
curl -X DELETE "http://your-server-address:5000/api/v1/portals/1" \
  -H "X-API-Key: your-api-key-here"
```

### Using JavaScript (Fetch API)

```javascript
async function deletePortal(portalId) {
  const response = await fetch(`http://your-server-address:5000/api/v1/portals/${portalId}`, {
    method: 'DELETE',
    headers: {
      'X-API-Key': 'your-api-key-here'
    }
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`Portal deleted successfully: ${data.message}`);
  } else {
    console.error(`Error: ${data.message}`);
  }
}

// Delete portal with ID 1
deletePortal(1);
```

### Using Python (requests library)

```python
import requests

def delete_portal(portal_id):
    url = f"http://your-server-address:5000/api/v1/portals/{portal_id}"
    headers = {
        "X-API-Key": "your-api-key-here"
    }
    
    response = requests.delete(url, headers=headers)
    data = response.json()
    
    if data["success"]:
        print(f"Portal deleted successfully: {data['message']}")
    else:
        print(f"Error: {data['message']}")

if __name__ == "__main__":
    # Delete portal with ID 1
    delete_portal(1)
```

## Example 6: WebSocket Integration for Real-time Updates

### Using JavaScript (Socket.IO)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Portal Status Monitor</title>
    <script src="https://cdn.socket.io/4.4.1/socket.io.min.js"></script>
</head>
<body>
    <h1>Portal Status Monitor</h1>
    <div id="portal-status"></div>
    <div id="notifications"></div>

    <script>
        // Connect to WebSocket server
        const socket = io('http://your-server-address:5000');
        
        // Listen for portal status changes
        socket.on('portal_status_change', function(data) {
            console.log('Portal status changed:', data);
            
            // Update the UI
            const statusDiv = document.getElementById('portal-status');
            const statusItem = document.createElement('div');
            statusItem.innerHTML = `
                <p><strong>${data.name}</strong> status changed to <span class="${data.status.toLowerCase()}">${data.status}</span>
                at ${new Date(data.timestamp).toLocaleTimeString()}</p>
            `;
            statusDiv.prepend(statusItem);
        });
        
        // Listen for test results
        socket.on('portal_test_result', function(data) {
            console.log('Portal test result:', data);
            
            // Show notification
            const notificationsDiv = document.getElementById('notifications');
            const notification = document.createElement('div');
            notification.className = `notification ${data.success ? 'success' : 'error'}`;
            notification.innerHTML = `
                <p><strong>Test Result:</strong> ${data.message}</p>
                <p>Portal ID: ${data.portal_id}</p>
                <p>Time: ${new Date(data.timestamp).toLocaleTimeString()}</p>
            `;
            notificationsDiv.prepend(notification);
            
            // Auto-remove notification after 5 seconds
            setTimeout(() => notification.remove(), 5000);
        });
        
        // Handle connection errors
        socket.on('connect_error', function(error) {
            console.error('Connection error:', error);
            const statusDiv = document.getElementById('portal-status');
            statusDiv.innerHTML = '<p class="error">WebSocket connection error. Real-time updates unavailable.</p>';
        });
    </script>
    
    <style>
        .UP, .success { color: green; }
        .DOWN, .error { color: red; }
        .DISABLED { color: gray; }
        .notification {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .notification.success { background-color: #dff0d8; }
        .notification.error { background-color: #f2dede; }
    </style>
</body>
</html>
```

## Using WebSockets with Python

```python
import socketio
import time

# Create a Socket.IO client
sio = socketio.Client()

@sio.event
def connect():
    print("Connected to WebSocket server")

@sio.event
def disconnect():
    print("Disconnected from WebSocket server")

@sio.on('portal_status_change')
def on_portal_status_change(data):
    print(f"Portal status changed: {data['name']} is now {data['status']}")

@sio.on('portal_test_result')
def on_portal_test_result(data):
    print(f"Portal test result: {data['message']}")
    print(f"Success: {data['success']}")
    if 'details' in data:
        print(f"Details: {data['details']}")

@sio.on('test_all_progress')
def on_test_all_progress(data):
    print(f"Testing progress: {data['completed']}/{data['total']} - Currently testing: {data['current_portal_name']}")

@sio.on('test_all_completed')
def on_test_all_completed(data):
    print(f"Testing completed: {data['success_count']} successful, {data['failed_count']} failed")
    print(f"Total duration: {data['duration_ms']}ms")

def main():
    try:
        # Connect to the Socket.IO server
        sio.connect('http://your-server-address:5000')
        
        # Keep the connection open
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Disconnect on Ctrl+C
        sio.disconnect()

if __name__ == "__main__":
    main()
```

## Complete Application Example: Portal Management CLI

Here's a more complete example of a command-line interface (CLI) for managing portals using Python:

```python
import argparse
import json
import requests
import sys

API_BASE_URL = "http://your-server-address:5000/api/v1"
API_KEY = "your-api-key-here"

def get_headers():
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

def list_portals(args):
    """List all portals or filter by status/type"""
    url = f"{API_BASE_URL}/portals"
    params = {}
    
    if args.status:
        params["status"] = args.status
    if args.type:
        params["type"] = args.type
    if args.limit:
        params["limit"] = args.limit
    
    response = requests.get(url, headers=get_headers(), params=params)
    data = response.json()
    
    if data["success"]:
        print(f"Found {data['count']} portals:")
        for portal in data["data"]:
            status_color = "\033[92m" if portal["status"] == "up" else "\033[91m" if portal["status"] == "down" else "\033[90m"
            reset_color = "\033[0m"
            print(f"  {portal['id']}: {portal['name']} ({portal['type']}) - Status: {status_color}{portal['status']}{reset_color}")
    else:
        print(f"Error: {data['message']}")
        return 1
    return 0

def get_portal(args):
    """Get details for a specific portal"""
    url = f"{API_BASE_URL}/portals/{args.id}"
    response = requests.get(url, headers=get_headers())
    data = response.json()
    
    if data["success"]:
        portal = data["data"]
        print(f"Portal Details for ID {args.id}:")
        print(f"  Name: {portal['name']}")
        print(f"  Type: {portal['type']}")
        print(f"  URL: {portal['url']}")
        if "mac" in portal and portal["mac"]:
            print(f"  MAC: {portal['mac']}")
        print(f"  Status: {portal['status']}")
        print(f"  Max Connections: {portal['max_connections']}")
        print(f"  Enabled: {portal['enabled']}")
        print(f"  Last Check: {portal.get('last_check', 'Never')}")
        print(f"  Created: {portal['created_at']}")
        print(f"  Updated: {portal['updated_at']}")
        if args.json:
            print("\nJSON Output:")
            print(json.dumps(portal, indent=2))
    else:
        print(f"Error: {data['message']}")
        return 1
    return 0

def create_portal(args):
    """Create a new portal"""
    url = f"{API_BASE_URL}/portals"
    
    # Build the portal data from arguments
    portal_data = {
        "name": args.name,
        "type": args.type,
        "url": args.url,
        "enabled": True
    }
    
    if args.mac:
        portal_data["mac"] = args.mac
    if args.username:
        portal_data["username"] = args.username
    if args.password:
        portal_data["password"] = args.password
    if args.max_connections:
        portal_data["max_connections"] = args.max_connections
    if args.http_proxy:
        portal_data["http_proxy"] = args.http_proxy
    
    response = requests.post(url, headers=get_headers(), json=portal_data)
    data = response.json()
    
    if data["success"]:
        print(f"Portal created successfully with ID: {data['data']['id']}")
    else:
        print(f"Error: {data['message']}")
        if "details" in data:
            for field, errors in data["details"].items():
                print(f"  {field}: {', '.join(errors)}")
        return 1
    return 0

def update_portal(args):
    """Update an existing portal"""
    url = f"{API_BASE_URL}/portals/{args.id}"
    
    # Only include fields that are provided
    portal_data = {}
    if args.name:
        portal_data["name"] = args.name
    if args.url:
        portal_data["url"] = args.url
    if args.mac:
        portal_data["mac"] = args.mac
    if args.username:
        portal_data["username"] = args.username
    if args.password:
        portal_data["password"] = args.password
    if args.max_connections:
        portal_data["max_connections"] = args.max_connections
    if args.http_proxy:
        portal_data["http_proxy"] = args.http_proxy
    if args.enabled is not None:
        portal_data["enabled"] = args.enabled
    
    response = requests.put(url, headers=get_headers(), json=portal_data)
    data = response.json()
    
    if data["success"]:
        print(f"Portal updated successfully: {data['message']}")
    else:
        print(f"Error: {data['message']}")
        return 1
    return 0

def delete_portal(args):
    """Delete a portal"""
    if not args.force:
        confirm = input(f"Are you sure you want to delete portal {args.id}? (y/N): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return 0
    
    url = f"{API_BASE_URL}/portals/{args.id}"
    response = requests.delete(url, headers=get_headers())
    data = response.json()
    
    if data["success"]:
        print(f"Portal deleted successfully: {data['message']}")
    else:
        print(f"Error: {data['message']}")
        return 1
    return 0

def test_portal(args):
    """Test a portal connection"""
    url = f"{API_BASE_URL}/portals/{args.id}/test"
    response = requests.post(url, headers=get_headers())
    data = response.json()
    
    if data["success"]:
        print(f"Test result: {data['message']}")
        print(f"Status: {data['data']['status']}")
        print(f"Response time: {data['data']['response_time_ms']}ms")
        print(f"Channels found: {data['data']['channels_found']}")
        
        if "details" in data["data"]:
            print("\nAdditional Details:")
            for key, value in data["data"]["details"].items():
                print(f"  {key}: {value}")
    else:
        print(f"Error: {data['message']}")
        return 1
    return 0

def toggle_portal(args):
    """Enable or disable a portal"""
    url = f"{API_BASE_URL}/portals/{args.id}/toggle"
    payload = {"enabled": args.enable}
    
    response = requests.put(url, headers=get_headers(), json=payload)
    data = response.json()
    
    if data["success"]:
        state = "enabled" if args.enable else "disabled"
        print(f"Portal {state} successfully: {data['message']}")
    else:
        print(f"Error: {data['message']}")
        return 1
    return 0

def main():
    parser = argparse.ArgumentParser(description="STB-ReStreamer Portal Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List portals command
    list_parser = subparsers.add_parser("list", help="List all portals")
    list_parser.add_argument("--status", choices=["up", "down", "disabled"], help="Filter by status")
    list_parser.add_argument("--type", help="Filter by portal type")
    list_parser.add_argument("--limit", type=int, help="Limit number of results")
    
    # Get portal command
    get_parser = subparsers.add_parser("get", help="Get portal details")
    get_parser.add_argument("id", help="Portal ID")
    get_parser.add_argument("--json", action="store_true", help="Show raw JSON output")
    
    # Create portal command
    create_parser = subparsers.add_parser("create", help="Create a new portal")
    create_parser.add_argument("--name", required=True, help="Portal name")
    create_parser.add_argument("--type", required=True, choices=["stalker", "ministra", "xtream", "m3u", "xcupdates"], help="Portal type")
    create_parser.add_argument("--url", required=True, help="Portal URL")
    create_parser.add_argument("--mac", help="MAC address (required for stalker/ministra)")
    create_parser.add_argument("--username", help="Username (required for xtream)")
    create_parser.add_argument("--password", help="Password (required for xtream)")
    create_parser.add_argument("--max-connections", type=int, default=1, help="Maximum connections")
    create_parser.add_argument("--http-proxy", help="HTTP proxy URL")
    
    # Update portal command
    update_parser = subparsers.add_parser("update", help="Update an existing portal")
    update_parser.add_argument("id", help="Portal ID")
    update_parser.add_argument("--name", help="Portal name")
    update_parser.add_argument("--url", help="Portal URL")
    update_parser.add_argument("--mac", help="MAC address")
    update_parser.add_argument("--username", help="Username")
    update_parser.add_argument("--password", help="Password")
    update_parser.add_argument("--max-connections", type=int, help="Maximum connections")
    update_parser.add_argument("--http-proxy", help="HTTP proxy URL")
    update_parser.add_argument("--enabled", type=bool, help="Enable/disable portal")
    
    # Delete portal command
    delete_parser = subparsers.add_parser("delete", help="Delete a portal")
    delete_parser.add_argument("id", help="Portal ID")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    
    # Test portal command
    test_parser = subparsers.add_parser("test", help="Test portal connection")
    test_parser.add_argument("id", help="Portal ID")
    
    # Toggle portal command
    toggle_parser = subparsers.add_parser("toggle", help="Enable or disable a portal")
    toggle_parser.add_argument("id", help="Portal ID")
    toggle_parser.add_argument("--enable", action="store_true", help="Enable portal (default is disable)")
    
    args = parser.parse_args()
    
    if args.command == "list":
        return list_portals(args)
    elif args.command == "get":
        return get_portal(args)
    elif args.command == "create":
        return create_portal(args)
    elif args.command == "update":
        return update_portal(args)
    elif args.command == "delete":
        return delete_portal(args)
    elif args.command == "test":
        return test_portal(args)
    elif args.command == "toggle":
        return toggle_portal(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

Usage examples:

```
# List all portals
python portal_cli.py list

# List only UP portals
python portal_cli.py list --status up

# Get details for portal ID 1
python portal_cli.py get 1

# Create a new Stalker portal
python portal_cli.py create --name "My Stalker Portal" --type stalker --url "http://example.com/stalker_portal" --mac "00:1A:79:12:34:56"

# Update a portal
python portal_cli.py update 1 --name "Updated Portal Name" --max-connections 2

# Test a portal connection
python portal_cli.py test 1

# Disable a portal
python portal_cli.py toggle 1

# Enable a portal
python portal_cli.py toggle 1 --enable

# Delete a portal
python portal_cli.py delete 1
``` 