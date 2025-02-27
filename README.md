# STB-Restreamer

A powerful IPTV streaming proxy server that manages and restreams channels from multiple portals with advanced features and a user-friendly web interface.

## Features

- **Multi-Portal Support**: Manage multiple IPTV portals simultaneously
- **Channel Management**:
  - Enable/disable specific channels
  - Customize channel names, numbers, and genres
  - Group channels for better organization
  - Custom EPG IDs for each channel
- **Advanced Streaming**:
  - FFmpeg-based streaming with configurable parameters
  - Direct stream option without transcoding
  - Automatic stream testing and fallback
  - Link caching for improved performance
  - Rate limiting to prevent overload
- **Web Interface**:
  - User-friendly channel editor
  - Advanced search and filtering
  - Channel preview functionality
  - Real-time streaming dashboard
  - Alert system for monitoring issues
- **HDHR Emulation**: Compatible with HDHomeRun devices
- **Playlist Generation**: 
  - M3U playlist generation with customizable sorting
  - Channel group playlists
  - EPG ID mapping

## Requirements

- Python 3.7 or higher
- FFmpeg (required for transcoding and stream testing)
- Required Python packages (install via pip):
  - flask
  - waitress
  - werkzeug

## Installation

1. Clone the repository or download the source code
2. Install FFmpeg:
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and either:
     - Add to system PATH
     - Place ffmpeg.exe in the application directory
     - Place in C:\ffmpeg\bin
   - Linux: `sudo apt-get install ffmpeg` (Ubuntu/Debian)
3. Install Python dependencies:
   ```bash
   pip install flask waitress werkzeug
   ```

## Configuration

1. First run will create a default `config.json` with basic settings
2. Access the web interface at `http://localhost:8001`
3. Default login (if security enabled):
   - Username: admin
   - Password: 12345

### Portal Setup

1. Go to the Portals page
2. Click "Add Portal"
3. Enter portal details:
   - Name: Unique identifier for the portal
   - URL: Portal URL
   - MACs: Comma-separated list of MAC addresses
   - Streams per MAC: Number of simultaneous streams per MAC
   - Proxy: Optional proxy URL

### Channel Configuration

1. Access the Channel Editor
2. Enable desired channels
3. Customize:
   - Channel names
   - Channel numbers
   - Genres
   - EPG IDs
4. Create and manage channel groups

## Usage

### Accessing Streams

- Direct stream: `http://localhost:8001/play/<portalId>/<channelId>`
- Web preview: Add `?web=true` to the URL
- M3U playlist: `http://localhost:8001/playlist`
- Group playlist: `http://localhost:8001/groups_playlist`

### HDHR Emulation

1. Enable HDHR in settings
2. Configure:
   - Device name
   - Number of tuners
3. Access via HDHR-compatible apps using:
   - Discovery URL: `http://localhost:8001/discover.json`
   - Lineup URL: `http://localhost:8001/lineup.json`

## Security

- Enable authentication in settings
- Change default username and password
- Use HTTPS reverse proxy for remote access
- Implement appropriate firewall rules

## Troubleshooting

1. Check the logs at `STB-Proxy.log`
2. Verify FFmpeg installation and PATH
3. Monitor alerts in the web interface
4. Ensure portal URLs and MACs are valid
5. Check proxy settings if using a proxy

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## License

This project is open source and available under the [MIT License](LICENSE). 