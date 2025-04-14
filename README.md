# STB-ReStreamer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.0+-green.svg)](https://flask.palletsprojects.com/)

A comprehensive IPTV management platform that provides advanced proxy capabilities, content organization, and streaming optimization for Stalker Portal-based services.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

STB-ReStreamer is an enterprise-grade solution designed for efficient management of IPTV content from Stalker Portal providers. The application serves as an intermediary proxy server that aggregates channels, VOD content, and series from multiple sources, providing unified access through an intuitive web interface and standardized streaming endpoints.

## Key Features

### Portal Management
- **Multi-Portal Integration**: Consolidate content from unlimited IPTV portals
- **MAC Address Orchestration**: Intelligent rotation and management of MAC addresses
- **Session Management**: Automatic token authentication and renewal
- **Proxy Support**: Configurable connection routing through HTTP/HTTPS proxies

### Content Organization
- **Channel Management**:
  - Granular enable/disable controls for individual channels
  - Custom metadata including names, numbers, and genres
  - Hierarchical grouping with visual organization tools
  - EPG mapping for accurate program guide integration
- **Media Library**:
  - Unified access to VOD and series content across portals
  - Category-based browsing with rich metadata
  - Content prefetching for improved performance
  - Customizable naming and organization

### Streaming Technology
- **Adaptive Delivery Methods**:
  - Direct stream passthrough for maximum efficiency
  - FFmpeg-based transcoding with configurable parameters
  - Automatic stream health monitoring and failover
  - Bandwidth optimization through intelligent caching
- **Playlist Generation**:
  - Dynamic M3U playlist creation with configurable attributes
  - Category-specific playlist endpoints
  - Multiple sorting algorithms (alphabetical, numerical, genre-based)
  - Industry-standard format compatibility (including XUI)

### Network Integration
- **HDHR Protocol Emulation**:
  - Native compatibility with HDHomeRun clients
  - Configurable tuner allocation
  - Standard-compliant discovery and lineup APIs

### Administrative Interface
- **Monitoring Dashboard**:
  - Real-time stream analytics
  - System resource utilization metrics
  - Comprehensive alerting system
  - Historical performance data
- **Security**:
  - Role-based authentication system
  - Configurable access controls
  - Integration with reverse proxies for HTTPS

## System Requirements

### Minimum Requirements
- **Processor**: Dual-core CPU, 2.0 GHz
- **Memory**: 2 GB RAM
- **Storage**: 1 GB available space
- **Operating System**: Windows 10/11, Ubuntu 18.04+, Debian 10+, macOS 10.15+
- **Python Runtime**: 3.7 or newer
- **Network**: Broadband internet connection

### Recommended Requirements
- **Processor**: Quad-core CPU, 3.0+ GHz
- **Memory**: 4+ GB RAM
- **Storage**: SSD with 5+ GB available space
- **Network**: 100+ Mbps internet connection

### Dependencies
- **Core Requirements**:
  - Flask 2.0+ (web framework)
  - Waitress 2.0+ (production WSGI server)
  - Werkzeug 2.0+ (WSGI utilities)
- **External Dependencies**:
  - FFmpeg 4.0+ (media processing)

## Installation

### Windows

1. Install Python 3.7+ from [python.org](https://www.python.org/downloads/)

2. Install FFmpeg:
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Either:
     - Add to system PATH
     - Place ffmpeg.exe in the application directory
     - Install to C:\ffmpeg\bin

3. Install STB-ReStreamer:
   ```bash
   git clone https://github.com/VodenoFF/STB-ReStreamer.git
   cd STB-ReStreamer
   pip install flask waitress werkzeug
   ```

### Linux (Debian/Ubuntu)

1. Install system dependencies:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip ffmpeg
   ```

2. Install STB-ReStreamer:
   ```bash
   git clone https://github.com/VodenoFF/STB-ReStreamer.git
   cd STB-ReStreamer
   pip3 install flask waitress werkzeug
   ```

### macOS

1. Install Homebrew if not already installed:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install dependencies:
   ```bash
   brew install python ffmpeg
   ```

3. Install STB-ReStreamer:
   ```bash
   git clone https://github.com/VodenoFF/STB-ReStreamer.git
   cd STB-ReStreamer
   pip3 install flask waitress werkzeug
   ```

### Docker (Optional)

```bash
docker pull vodenoff/stb-restreamer:latest
docker run -d -p 8001:8001 -v /path/to/config:/app/config vodenoff/stb-restreamer:latest
```

## Getting Started

1. Launch the application:
   ```bash
   python app.py
   ```

2. Access the administrative interface at:
   ```
   http://localhost:8001
   ```

3. Default authentication (if security enabled):
   - Username: `admin`
   - Password: `12345`

## Configuration

### Initial Portal Setup

1. Navigate to the Portals management section
2. Select "Add Portal" and provide:
   - **Name**: Descriptive identifier
   - **URL**: Stalker Portal endpoint (full URL with path)
   - **MAC Addresses**: Comma-delimited list of authorized MACs
   - **Stream Limit**: Maximum concurrent streams per MAC (0 = unlimited)
   - **Proxy**: Optional HTTP/HTTPS proxy URL

### Content Management

1. **Channel Configuration**:
   - Access the Channel Editor
   - Enable desired channels
   - Configure metadata:
     - Display names
     - Channel numbers
     - Genre categories
     - EPG mappings

2. **Channel Groups**:
   - Create logical content groups
   - Assign channels with drag-and-drop interface
   - Set group logos and priority order
   - Configure group-specific sorting

### System Configuration

Access the Settings panel to configure:

- **Streaming Parameters**:
  - Delivery method (Direct/FFmpeg)
  - Transcoding parameters
  - Buffer settings
  - Connection timeout values

- **Playlist Options**:
  - Default sorting algorithms
  - Metadata inclusion rules
  - Group handling preferences
  - Format compatibility settings

- **Security Settings**:
  - Authentication requirements
  - Credential management
  - Access control configuration

- **HDHR Emulation**:
  - Device identification
  - Tuner allocation
  - Network discovery settings

## Usage

### Content Access

#### Live Television
- **Direct Stream**: `http://localhost:8001/play/{portalId}/{channelId}`
- **Web Player**: `http://localhost:8001/player/{portalId}/{channelId}`
- **Group Player**: `http://localhost:8001/chplay/{groupId}`

#### Video-on-Demand
- **Movies Interface**: `http://localhost:8001/movies`
- **Series Browser**: `http://localhost:8001/series`
- **Direct VOD**: `http://localhost:8001/play/vod/{portalId}/{movieId}`
- **Episode Access**: `http://localhost:8001/play/series/{portalId}/{seriesId}/{seasonId}/{episodeId}`

#### Playlist Access
- **Complete Playlist**: `http://localhost:8001/playlist`
- **Group Playlists**: `http://localhost:8001/groups_playlist`
- **Custom Playlists**: Generated through web interface

### HDHR Integration

When HDHR emulation is active:

1. STB-ReStreamer broadcasts as an HDHomeRun device on the local network
2. Compatible clients can discover the service automatically
3. Manual configuration endpoints:
   - **Discovery**: `http://localhost:8001/discover.json`
   - **Lineup**: `http://localhost:8001/lineup.json`
   - **Status**: `http://localhost:8001/lineup_status.json`

### Administrative Tools

- **Stream Monitor**: `http://localhost:8001/streaming`
- **System Dashboard**: `http://localhost:8001/dashboard`
- **Alert Management**: `http://localhost:8001/alerts`
- **Application Logs**: `http://localhost:8001/log`

## Advanced Topics

### Performance Optimization

- **FFmpeg Parameters**:
  ```
  ffmpeg -re -http_proxy <proxy> -timeout <timeout> -i <url> -map 0 -codec copy -f mpegts pipe:
  ```
  - `-re`: Read input at native frame rate
  - `-timeout`: Set connection timeout threshold
  - `-map 0`: Map all streams from input
  - `-codec copy`: Stream copy without re-encoding
  - `-f mpegts`: Output format as MPEG-TS

- **Caching Strategy**:
  - Link caching with configurable TTL
  - Rate limiting with intelligent cooldown
  - MAC rotation to prevent portal session limits

### High Availability Configuration

- **Fault Tolerance**:
  - Automatic MAC switching on stream failure
  - Portal prioritization and failover
  - Stream health monitoring and reporting

### Enterprise Security Implementation

- **Secure Deployment**:
  - HTTPS termination through reverse proxy
  - Authentication enforcement
  - IP-based access restrictions
  - VPN integration for remote access

## Troubleshooting

### Diagnostic Procedures

1. **Stream Issues**:
   - Verify portal connectivity (`/portal/{portalId}/channels`)
   - Confirm MAC authorization status
   - Check proxy configuration if applicable
   - Review FFmpeg installation and path configuration
   - Examine application logs for specific error codes

2. **Interface Access Problems**:
   - Confirm service is running (`ps aux | grep app.py`)
   - Verify port availability (`netstat -tuln | grep 8001`)
   - Check network firewall settings
   - Review browser console for JavaScript errors

3. **Resource Utilization**:
   - Monitor CPU/memory usage during peak load
   - Adjust concurrent stream limits
   - Optimize FFmpeg parameters for efficiency
   - Consider hardware scaling for production environments

### Logging

- **Log Location**: `STB-Proxy.log`
- **Log Level**: Configurable (INFO/DEBUG/ERROR)
- **Web Interface**: Accessible via `/log` endpoint
- **Log Rotation**: Automatic based on file size

## Contributing

We welcome contributions to enhance STB-ReStreamer. Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/enhancement-name`
3. Implement your changes with appropriate tests
4. Ensure all tests pass and code meets quality standards
5. Submit a pull request with comprehensive description

For major changes, please open an issue first to discuss proposed modifications.

## License

This project is distributed under the [MIT License](LICENSE).

Copyright © 2025 Contributors to the STB-ReStreamer project. 