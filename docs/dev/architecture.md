# STB-ReStreamer Architecture Overview

This document provides a technical overview of the STB-ReStreamer architecture, designed to help developers understand the system's components, their interactions, and the design patterns used.

## System Architecture

STB-ReStreamer follows a modular architecture organized around the Flask web framework with the following key components:

```
STB-ReStreamer
├── Application Core
│   ├── Config Manager
│   ├── Alert Manager
│   └── Authentication System
├── Service Layer
│   ├── Portal Manager
│   ├── Channel Manager
│   ├── Category Manager
│   ├── EPG Manager
│   ├── Stream Manager
│   └── MAC Manager
├── Data Layer
│   ├── SQLite Database
│   ├── Cache System
│   └── File Storage
├── Portal Providers
│   ├── Stalker Provider
│   ├── Xtream Provider
│   ├── M3U Provider
│   ├── Ministra Provider
│   └── XC Updates Provider
├── API Layer
│   ├── REST API
│   ├── WebSocket API
│   └── HDHomeRun API
└── Presentation Layer
    ├── Templates
    ├── Static Assets
    └── JavaScript Components
```

## Core Components

### Application Core

#### Config Manager (`ConfigManager`)

The Configuration Manager handles all application settings, providing a centralized interface for accessing and modifying configuration parameters.

- Loads settings from configuration files
- Provides validation of configuration values
- Supports nested configuration structures
- Manages data directories
- Persists configuration changes

#### Alert Manager (`AlertManager`)

The Alert Manager provides a system-wide mechanism for creating, tracking, and displaying user notifications.

- Supports different alert types (success, error, warning, info)
- Manages alert persistence across sessions
- Implements alert clearing and expiration

#### Authentication System (`AuthManager`)

The Authentication System manages user authentication and authorization.

- Handles user login/logout operations
- Manages session tokens
- Provides role-based access control
- Supports API key authentication

### Service Layer

#### Portal Manager (`PortalManager`)

The Portal Manager handles the registration, updating, and management of IPTV portals.

- Maintains a registry of configured portals
- Provides thread-safe operations for portal CRUD operations
- Manages portal connection status
- Handles portal testing and validation

#### Channel Manager (`ChannelManager`)

The Channel Manager handles channel metadata and organization.

- Maintains channel information from various portals
- Provides channel search and filtering
- Handles channel metadata updates
- Links channels to categories

#### Category Manager (`CategoryManager`)

The Category Manager handles the organization of channels into user-defined categories.

- Manages category CRUD operations
- Handles channel-to-category assignments
- Provides category filtering and sorting

#### EPG Manager (`EPGManager`)

The Electronic Program Guide (EPG) Manager handles TV program data.

- Parses XMLTV format EPG data
- Associates EPG data with channels
- Handles EPG data updates and caching
- Provides program search and filtering

#### Stream Manager (`StreamManager`)

The Stream Manager handles active stream creation, monitoring, and termination.

- Creates stream sessions
- Monitors active streams
- Handles stream resource allocation and cleanup
- Manages stream quality and transcoding options

#### MAC Manager (`MacManager`)

The MAC Manager handles MAC address assignment and tracking for Stalker/Ministra portals.

- Provides thread-safe MAC allocation
- Handles MAC address validation
- Manages MAC-to-stream associations
- Implements MAC rotation strategies

### Data Layer

#### SQLite Database

The application uses SQLite for persistent data storage, with the following key tables:

- `portals` - Configured IPTV portals
- `categories` - User-defined channel categories
- `category_assignments` - Channel-to-category mappings
- `channels` - Channel information
- `stream_history` - Historic stream data
- `users` - User account information
- `settings` - Application settings

#### Cache System

The caching system improves performance by storing frequently accessed data:

- Link cache for stream URLs
- EPG data cache
- Portal response cache
- Channel data cache

#### File Storage

The application manages several types of files:

- Configuration files
- Logs
- EPG data files
- M3U playlist files
- Temporary stream files

### Portal Providers

The system uses a provider pattern to support different IPTV portal APIs:

#### Base Portal Provider

An abstract base class defining the interface all providers must implement:

- `authenticate()` - Authenticate with the portal
- `get_channels()` - Retrieve channel list
- `get_stream_url()` - Get playable stream URL
- `get_epg()` - Retrieve EPG data (if available)
- `test_connection()` - Test portal connectivity

#### Specific Providers

1. **Stalker Provider** - Traditional Stalker middleware API
2. **Xtream Provider** - Xtream Codes API
3. **M3U Provider** - M3U/M3U8 playlist files
4. **Ministra Provider** - Newer Ministra middleware API
5. **XC Updates Provider** - Enhanced Xtream Codes API

### API Layer

#### REST API

The REST API provides a programmatic interface for integrating with other systems:

- Portal management endpoints
- Channel information endpoints
- Stream control endpoints
- Category management endpoints
- EPG data endpoints
- System configuration endpoints

#### WebSocket API

The WebSocket API provides real-time updates:

- Stream status updates
- Portal connection status changes
- System notifications
- Testing progress updates

#### HDHomeRun API

The HDHomeRun emulation API allows integration with third-party applications:

- Device discovery endpoints
- Channel lineup endpoints
- Stream access endpoints

### Presentation Layer

#### Templates

The application uses Jinja2 templates for HTML rendering:

- Base layout templates
- Portal management templates
- Channel management templates
- Category management templates
- EPG display templates
- Stream control templates
- Settings templates

#### Static Assets

- CSS stylesheets (Bootstrap-based)
- JavaScript libraries
- Font files
- Image assets

#### JavaScript Components

- Portal management UI
- Stream status monitoring
- Channel preview player
- WebSocket integrations
- Form validation and dynamic behavior

## Design Patterns

STB-ReStreamer employs several design patterns:

1. **Factory Pattern** - Used in the Flask application factory
2. **Provider Pattern** - Used for portal API implementations
3. **Singleton Pattern** - Used for managers (PortalManager, ConfigManager, etc.)
4. **Observer Pattern** - Used in the WebSocket notification system
5. **Repository Pattern** - Used for data access
6. **Strategy Pattern** - Used for stream handling strategies

## Threading Model

The application uses multiple threads for concurrent operations:

- Main application thread (Flask)
- Portal status monitoring threads
- EPG update threads
- Stream monitoring threads
- Cleanup background threads

Thread safety is ensured through proper synchronization mechanisms.

## Security Considerations

The architecture incorporates several security measures:

- Password hashing using bcrypt
- API key authentication
- Token encryption for provider credentials
- Rate limiting to prevent abuse
- Input validation to prevent injection attacks
- Session management with secure cookies

## Error Handling

The application implements a comprehensive error handling strategy:

- Structured exception hierarchy
- Global exception handlers
- Detailed logging
- User-friendly error messages
- Automatic recovery mechanisms

## Performance Optimization

Performance is optimized through:

- Multi-level caching
- Efficient database queries
- Asynchronous processing of non-critical operations
- Batch processing where applicable
- Resource pooling (connections, threads)

## Configuration Management

The application uses a hierarchical configuration approach:

- Default configuration
- Environment-specific overrides
- User-defined settings
- Runtime configuration changes

## Dependency Management

External dependencies are managed through:

- `requirements.txt` with pinned versions
- Clearly defined dependency boundaries
- Modular design to limit dependency scope
- Compatibility validation during startup

## Extensibility

The architecture is designed for extensibility:

- Plugin system for portal providers
- Modular route structure using Flask blueprints
- Clear component interfaces
- Event-based communication for loose coupling

## Development Workflow

For more information on the development workflow, see the [Contributing Guidelines](contributing.md) and [Development Setup](setup.md) documents. 