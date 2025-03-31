# STB-ReStreamer: Old Application Architecture Analysis

## 1. Overview

The original STB-ReStreamer application is a Flask-based web application that functions as a proxy/middleware for IPTV services. It allows users to manage and stream content from various IPTV portals (primarily Stalker/Ministra portals but also Xtream and M3U playlists) through a single interface. The application handles authentication, channel management, and stream generation.

## 2. Core Architecture

### 2.1. Main Components

The old application architecture consists of these primary components:

1. **Flask Web Application (`app.py`)**: 
   - Core of the application containing route handlers, utility functions, and application logic
   - Handles HTTP requests and responses
   - Manages application state

2. **STB API Module (`stb.py`)**: 
   - Handles communication with Stalker/Ministra portals
   - Contains functions for authentication, channel retrieval, and stream generation
   - Acts as a client for the IPTV portal APIs

3. **Caching & Rate Limiting**:
   - `LinkCache`: Caches stream links to reduce redundant API calls
   - `RateLimiter`: Prevents excessive requests to the same channel/portal

4. **Web Templates (`templates/`)**: 
   - Jinja2 templates for rendering the UI
   - Contains HTML for dashboard, portal management, channel editor, etc.

### 2.2. Data Storage

The application uses simple JSON files for data persistence:

- `config.json`: Application configuration
- `portals.json`: Portal definitions and credentials
- `channel_groups.json`: Channel grouping definitions

## 3. Key Functionality

### 3.1. Portal Management

The application allows users to:
- Add, edit, and remove IPTV portals
- Configure portal properties (URL, credentials, MAC addresses)
- Test portal connectivity
- Toggle portal status (enabled/disabled)

**Key components:**
- `/portals` route: Renders the portal management UI
- `/portal/add`, `/portal/update`, `/portal/remove` routes: Handle portal CRUD operations
- `getPortals()`, `savePortals()` functions: Load/save portal data

### 3.2. Authentication

The application implements authentication for:
- User access to the admin interface
- Communication with IPTV portals

**Key components:**
- `authorise` decorator: Protects routes requiring authentication
- `getToken()` function in `stb.py`: Authenticates with Stalker portals

### 3.3. Channel Management

The application provides channel management features:
- Viewing all available channels from portals
- Creating channel groups
- Organizing channels into groups
- Reordering channels within groups

**Key components:**
- `/channels` route: Channel management UI
- `/editor` route: Channel editor UI
- Various helper routes for specific channel operations
- `saveChannelGroups()` function: Persists channel group configuration

### 3.4. Stream Generation

Core streaming functionality includes:
- Generating and proxying streams from IPTV portals
- Handling different stream formats and protocols
- Managing stream caching and rotation of MAC addresses
- FFmpeg integration for transcoding

**Key components:**
- `/play/<portalId>/<channelId>` route: Main streaming endpoint
- Stream generation logic in `channel()` function
- `getLink()` function in `stb.py`: Gets stream URLs from portals

### 3.5. HDHR Emulation

The application emulates an HDHomeRun device to support streaming to compatible clients:
- Device discovery
- Channel lineup information
- Stream URL generation

**Key components:**
- `/discover.json`, `/lineup_status.json`, `/lineup.json` routes
- `hdhr` decorator: Special handling for HDHR requests

### 3.6. Additional Features

Other significant features include:
- **Dashboard**: A simple dashboard showing system status
- **Alert System**: Tracks and displays system alerts
- **Logging**: Comprehensive logging of application activity
- **Settings Management**: User-configurable application settings

## 4. Code Organization

### 4.1. Code Structure

The old application has a relatively flat structure, with most functionality in the main `app.py` file:

```
/
├── app.py                   # Main application file
├── stb.py                   # STB API functions
├── config.json              # Configuration file
├── portals.json             # Portal data
├── channel_groups.json      # Channel groups
├── static/                  # Static assets (CSS, JS, images)
└── templates/               # Jinja2 templates
    ├── base.html            # Base template
    ├── dashboard.html       # Dashboard template
    ├── portals.html         # Portal management
    ├── channels.html        # Channel management
    ├── editor.html          # Channel editor
    └── settings.html        # Settings page
```

### 4.2. Monolithic Design

The original application follows a monolithic design pattern:
- Most functionality exists within the main `app.py` file
- Limited separation of concerns
- Minimal modularization
- Direct references between components

## 5. Technical Implementation Details

### 5.1. Streaming Mechanism

The streaming functionality works as follows:
1. Client requests a stream via `/play/<portalId>/<channelId>`
2. Application authenticates with the portal if needed
3. Application requests stream URL from the portal
4. Application proxies or processes the stream (using FFmpeg if configured)
5. Stream is delivered to the client with proper headers

### 5.2. MAC Address Rotation

For portals that limit concurrent connections by MAC address:
1. Portals are configured with multiple MAC addresses
2. Application rotates through available MACs
3. `moveMac()` function moves a used MAC to the end of the rotation list

### 5.3. Caching

The application implements two types of caching:
1. **Link Caching**: Caches stream URLs to reduce API calls
2. **Session Caching**: Maintains state between requests

### 5.4. Error Handling

Error handling strategies include:
- Try/except blocks for API calls
- Fallback mechanisms for failed requests
- Alert system for persistent errors
- Logging of errors for troubleshooting

## 6. UI Components

The UI is built with:
- Bootstrap 4 for styling
- jQuery for client-side interactivity
- Custom JavaScript for specific functionality
- Jinja2 templates for rendering

Key UI components include:
- Navigation sidebar
- Modal dialogs for forms
- Tables for data display
- Status indicators
- Form controls

## 7. Security Considerations

Security measures in the original app:
- Basic authentication for admin access
- MAC address obfuscation
- Token-based authentication with portals
- Session management
- Input validation (limited)

## 8. Limitations and Challenges

The original application had several limitations:
- Monolithic codebase making maintenance difficult
- Limited modularization
- Minimal separation of concerns
- File-based storage without proper database
- Basic error handling
- Limited scalability
- Minimal testing capabilities 