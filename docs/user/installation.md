# Installation Guide

This guide will walk you through the process of installing and setting up STB-ReStreamer on your system.

## System Requirements

STB-ReStreamer has the following system requirements:

- **Operating System**: Windows, macOS, or Linux
- **Python**: Python 3.7+ (3.9+ recommended)
- **RAM**: Minimum 2GB, 4GB+ recommended
- **Storage**: At least 1GB of free disk space
- **Network**: Stable internet connection

The resource requirements will vary based on the number of concurrent streams and users.

## Installation Methods

There are several ways to install STB-ReStreamer:

1. [Standard Python Installation](#standard-python-installation) (recommended for most users)
2. [Docker Installation](#docker-installation) (recommended for advanced users and servers)
3. [Windows Executable](#windows-executable) (simplest method for Windows users)

Choose the installation method that best suits your needs and technical expertise.

## Standard Python Installation

### Prerequisites

1. Install Python 3.7+ from [python.org](https://www.python.org/downloads/)
2. Ensure pip is installed and up to date

### Installation Steps

1. **Clone or download the repository**:

   ```bash
   git clone https://github.com/yourusername/STB-ReStreamer.git
   cd STB-ReStreamer
   ```

   Alternatively, download and extract the ZIP file from the GitHub releases page.

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the initial setup**:

   ```bash
   python app_new.py --setup
   ```

   This will create the necessary configuration files and data directories.

4. **Start the application**:

   ```bash
   python app_new.py
   ```

   The application will start and be available at `http://localhost:8001` by default.

### Installation on Windows

1. Install Python 3.9+ from [python.org](https://www.python.org/downloads/)
   - Ensure you check "Add Python to PATH" during installation

2. Open Command Prompt as Administrator and run:

   ```cmd
   pip install --upgrade pip
   ```

3. Download and extract the STB-ReStreamer ZIP file

4. Navigate to the extracted directory:

   ```cmd
   cd path\to\STB-ReStreamer
   ```

5. Install dependencies:

   ```cmd
   pip install -r requirements.txt
   ```

6. Run the application:

   ```cmd
   python app_new.py
   ```

### Installation on macOS/Linux

1. Install Python if not already installed:

   **macOS**:
   ```bash
   brew install python
   ```

   **Ubuntu/Debian**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   ```

2. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/STB-ReStreamer.git
   cd STB-ReStreamer
   ```

3. Create a virtual environment (recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Run the application:

   ```bash
   python app_new.py
   ```

## Docker Installation

Docker provides an easy way to run STB-ReStreamer in an isolated container.

### Prerequisites

- Docker installed on your system
- Basic knowledge of Docker commands

### Installation Steps

1. Pull the Docker image:

   ```bash
   docker pull yourusername/stb-restreamer:latest
   ```

2. Create a directory for persistent data:

   ```bash
   mkdir -p /path/to/stb-data
   ```

3. Run the container:

   ```bash
   docker run -d \
     --name stb-restreamer \
     -p 8001:8001 \
     -v /path/to/stb-data:/app/data \
     yourusername/stb-restreamer:latest
   ```

4. Access the application at `http://localhost:8001`

### Docker Compose

Alternatively, you can use Docker Compose:

1. Create a `docker-compose.yml` file:

   ```yaml
   version: '3'
   services:
     stb-restreamer:
       image: yourusername/stb-restreamer:latest
       container_name: stb-restreamer
       ports:
         - "8001:8001"
       volumes:
         - ./data:/app/data
       restart: unless-stopped
   ```

2. Start the container:

   ```bash
   docker-compose up -d
   ```

## Windows Executable

For Windows users who prefer not to install Python, we provide a standalone executable.

1. Download the latest `STB-ReStreamer-windows.zip` from the releases page
2. Extract the ZIP file to a location of your choice
3. Run `STB-ReStreamer.exe`
4. Access the application at `http://localhost:8001`

## Post-Installation

After installing STB-ReStreamer, you should:

1. **Configure security settings**:
   - Change the default admin password
   - Configure authentication settings

2. **Add your IPTV portals**:
   - Add your Stalker, Xtream, or M3U portals
   - Test the connections

3. **Configure other settings**:
   - Set up category management
   - Configure EPG sources if needed
   - Adjust stream quality settings

For more information, see the [Configuration](configuration.md) and [Quick Start](quick-start.md) guides.

## Running as a Service

### Windows Service

To run STB-ReStreamer as a Windows service:

1. Install NSSM (Non-Sucking Service Manager):
   - Download from [nssm.cc](https://nssm.cc/download)
   - Extract to a location on your system

2. Open Command Prompt as Administrator and navigate to the NSSM directory:
   ```cmd
   cd path\to\nssm\win64
   ```

3. Install the service:
   ```cmd
   nssm install STB-ReStreamer
   ```

4. In the dialog that appears:
   - Set the path to your `python.exe`
   - Set Arguments to the full path to `app_new.py`
   - Set Startup directory to your STB-ReStreamer directory
   - Configure other settings as needed

5. Start the service:
   ```cmd
   nssm start STB-ReStreamer
   ```

### Linux Systemd Service

To run STB-ReStreamer as a systemd service on Linux:

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/stb-restreamer.service
   ```

2. Add the following content (adjust paths as needed):
   ```
   [Unit]
   Description=STB-ReStreamer Service
   After=network.target

   [Service]
   User=yourusername
   WorkingDirectory=/path/to/STB-ReStreamer
   ExecStart=/path/to/python /path/to/STB-ReStreamer/app_new.py
   Restart=always
   RestartSec=5
   StandardOutput=syslog
   StandardError=syslog
   SyslogIdentifier=stb-restreamer

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable stb-restreamer
   sudo systemctl start stb-restreamer
   ```

4. Check the status:
   ```bash
   sudo systemctl status stb-restreamer
   ```

## Troubleshooting Installation

If you encounter issues during installation:

1. **Dependencies fail to install**:
   - Ensure you have the latest pip: `pip install --upgrade pip`
   - On Linux, you may need additional system packages: `sudo apt install python3-dev build-essential`

2. **Application fails to start**:
   - Check the log file in the STB-ReStreamer directory
   - Ensure all dependencies are installed correctly
   - Verify Python version is compatible (3.7+)

3. **Port conflicts**:
   - If port 8001 is in use, change the port in the configuration
   - Use `netstat -tuln` to check for port conflicts

4. **Permission issues**:
   - Ensure you have write permissions to the data directory
   - On Linux/macOS, you may need to run with elevated privileges temporarily

For more help, see the [Troubleshooting](troubleshooting.md) guide or create an issue on the GitHub repository. 