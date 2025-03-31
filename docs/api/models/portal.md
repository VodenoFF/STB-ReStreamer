# Portal Data Model

This document describes the Portal data model used in STB-ReStreamer. The Portal model represents a connection to an IPTV service provider.

## Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the portal |
| `name` | string | Display name of the portal |
| `type` | string | Type of portal (see Portal Types below) |
| `url` | string | URL of the portal service |
| `mac` | string | MAC address used for connecting to Stalker/Ministra portals |
| `username` | string | Username for portal authentication (if required) |
| `password` | string | Password for portal authentication (if required) |
| `http_proxy` | string | HTTP proxy URL (optional) |
| `max_connections` | integer | Maximum allowed concurrent connections |
| `enabled` | boolean | Whether the portal is enabled |
| `status` | string | Current status of the portal (UP, DOWN, DISABLED) |
| `options` | object | Additional portal-specific options |
| `last_check` | datetime | Timestamp of the last connection check |
| `created_at` | datetime | Timestamp when the portal was created |
| `updated_at` | datetime | Timestamp when the portal was last updated |

## Portal Types

The following portal types are supported:

### Stalker Portal

- **Type identifier**: `stalker`
- **Required fields**: `url`, `mac`
- **Optional fields**: `username`, `password`, `http_proxy`
- **Description**: The traditional Stalker Portal middleware, used by many IPTV providers

### Ministra Portal

- **Type identifier**: `ministra`
- **Required fields**: `url`, `mac`
- **Optional fields**: `username`, `password`, `http_proxy`
- **Description**: Newer version of the Stalker Portal middleware with enhanced features

### Xtream Codes

- **Type identifier**: `xtream`
- **Required fields**: `url`, `username`, `password`
- **Optional fields**: `http_proxy`
- **Description**: API compatible with the Xtream Codes platform

### M3U Playlist

- **Type identifier**: `m3u`
- **Required fields**: `url`
- **Optional fields**: `epg_url`, `http_proxy`, `refresh_interval`
- **Description**: Standard M3U/M3U8 playlist files, both local and remote

### XC Updates

- **Type identifier**: `xcupdates`
- **Required fields**: `url`, `username`, `password`
- **Optional fields**: `http_proxy`
- **Description**: XC Updates API for providers using this platform

## Status Values

- **UP**: The portal is reachable and working
- **DOWN**: The portal is unreachable or not functioning correctly
- **DISABLED**: The portal has been manually disabled by the user
- **UNKNOWN**: The portal status has not been checked yet

## Example JSON Representation

```json
{
  "id": "1",
  "name": "Main Stalker Portal",
  "type": "stalker",
  "url": "http://example.com/stalker_portal",
  "mac": "00:1A:79:XX:XX:XX",
  "username": "user123",
  "password": "•••••••",
  "http_proxy": "",
  "max_connections": 1,
  "enabled": true,
  "status": "UP",
  "options": {
    "timeout": 30,
    "retries": 3
  },
  "last_check": "2025-03-28T16:30:00Z",
  "created_at": "2025-03-01T12:00:00Z",
  "updated_at": "2025-03-28T16:00:00Z"
}
```

## Portal Options

The `options` object can contain additional configuration specific to each portal type:

### Common Options (All Portal Types)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `timeout` | integer | 30 | Connection timeout in seconds |
| `retries` | integer | 3 | Number of connection retry attempts |

### M3U Specific Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `refresh_interval` | integer | 24 | Hours between playlist refresh |
| `user_agent` | string | Default | User-Agent header for requests |
| `preserve_groups` | boolean | true | Keep original channel groups |

### Stalker/Ministra Specific Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `token_refresh_interval` | integer | 12 | Hours between token refreshes |
| `server_timeout` | integer | 5 | Server response timeout in seconds |

### Xtream/XC Updates Specific Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `stream_format` | string | "ts" | Preferred stream format (ts, m3u8) |
| `include_vod` | boolean | false | Include VOD content |

## Database Schema

In the SQLite database, the Portal model is stored in the `portals` table with the following schema:

```sql
CREATE TABLE portals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL, 
    url TEXT NOT NULL,
    mac TEXT,
    username TEXT,
    password TEXT,
    http_proxy TEXT,
    max_connections INTEGER DEFAULT 1,
    enabled INTEGER DEFAULT 1,
    status TEXT DEFAULT 'UNKNOWN',
    options TEXT,
    last_check TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

Note: The `options` field is stored as a JSON string in the database.

## Relationships

The Portal model has relationships with the following models:

- **Channels**: A portal has many channels
- **EPG**: A portal can have one EPG source
- **Streams**: Active streams are associated with channels from portals

## Validation Rules

When creating or updating Portal objects, the following validation rules are applied:

- `name`: Required, between 1-100 characters
- `type`: Required, must be a valid portal type
- `url`: Required, must be a valid URL or file path
- `mac`: Required for Stalker/Ministra, must be a valid MAC address format (XX:XX:XX:XX:XX:XX)
- `username`: Required for Xtream/XC Updates
- `password`: Required for Xtream/XC Updates
- `max_connections`: Optional, integer between 1-50
- `options`: Optional, must be a valid JSON object

## Business Logic

- When a portal is disabled, all its associated active streams are stopped
- Portals are periodically checked for connectivity, with the status updated accordingly
- If a portal goes DOWN, the system attempts to reconnect automatically based on retry settings 