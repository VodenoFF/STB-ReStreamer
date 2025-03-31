# Portal Management

The Portal Management feature in STB-ReStreamer allows you to manage connections to various IPTV portals and services. This document covers all aspects of adding, editing, testing, and managing portals.

## Supported Portal Types

STB-ReStreamer supports multiple types of IPTV portals:

1. **Stalker Portal** - Traditional Stalker middleware portals
2. **Xtream Codes** - Standard Xtream Codes API
3. **M3U Playlist** - M3U and M3U8 playlists (both local files and remote URLs)
4. **Ministra** - Newer Ministra middleware portals (evolution of Stalker)
5. **XC Updates** - Enhanced Xtream Codes with additional features

Each portal type has specific settings and capabilities. For detailed information about each type, see the specific portal documentation in the `/portals` directory.

## Portal List

The portal list page shows all configured portals in the system. For each portal, you can see:

- **Status**: Whether the portal is UP, DOWN, or DISABLED
- **Name**: The descriptive name you gave to the portal
- **Type**: The portal implementation type
- **URL**: The base URL of the portal
- **MAC**: The MAC address used for authentication (if applicable)
- **Connections**: Current active connections / maximum allowed connections

### Portal Actions

For each portal, you can perform the following actions:

- **Edit Portal**: Modify portal settings
- **Test Connection**: Verify that the portal is reachable
- **Enable/Disable**: Toggle the portal's enabled status

You can also use the "Test All" button to test all portals at once.

## Adding a Portal

To add a new portal:

1. Click the "Add Portal" button on the portal list page
2. Fill in the required information:
   - **Portal Name**: A descriptive name (required)
   - **Portal Type**: Select the appropriate portal type (required)
   - **Portal URL**: The base URL for the portal API or the M3U playlist URL (required)

3. Configure additional settings based on the portal type:
   - **MAC Address**: Required for Stalker and Ministra portals
   - **Username/Password**: Required for most portal types except M3U
   - **Max Connections**: Maximum number of simultaneous connections allowed (defaults to 1)

4. Configure portal-specific options:
   - **M3U Specific**:
     - EPG URL: URL to XMLTV data (optional)
     - Refresh Interval: How often to refresh the playlist (in hours)
   
   - **XC Updates Specific**:
     - Enable Catchup: Enable TV catchup/timeshift if supported
     - Enable DVR: Enable DVR functionality if supported

5. Additional options:
   - **HTTP Proxy**: Specify a proxy server for all requests to this portal (optional)
   - **Enable Portal**: Toggle to enable or disable the portal (enabled by default)

6. Click "Save Portal" to add the portal

## Editing a Portal

To edit an existing portal:

1. Click the "Edit" button (pencil icon) next to the portal in the list
2. Modify any settings as needed
3. Click "Save Changes" to update the portal

## Testing Portal Connections

You can test a portal's connection to verify that it's working properly:

1. Click the "Test" button (plug icon) next to the portal in the list
2. The system will attempt to:
   - Authenticate with the portal
   - Retrieve user profile information
   - Get a list of available channels

3. A success or failure message will be displayed with details

You can test all portals at once by clicking the "Test All" button at the top of the portal list.

## Deleting a Portal

To delete a portal:

1. Go to the Edit page for the portal
2. Click the "Delete Portal" button in the top right
3. Confirm the deletion in the popup dialog

**Note**: Deleting a portal cannot be undone and will remove all configurations for that portal.

## Portal Status

Portal status is indicated by colored badges:

- **Green (UP)**: Portal is enabled and accessible
- **Red (DOWN)**: Portal is enabled but cannot be accessed
- **Gray (DISABLED)**: Portal is disabled

Status is automatically updated in real-time when changes occur.

## Troubleshooting

If you encounter issues with a portal:

1. **Cannot connect to portal**:
   - Verify the URL is correct and includes the protocol (http:// or https://)
   - Check that the portal server is online
   - Confirm your authentication details are correct

2. **Authentication failures**:
   - Verify the MAC address is in the correct format (XX:XX:XX:XX:XX:XX)
   - Confirm username and password are correct
   - Check if the portal has a limit on concurrent connections

3. **No channels available**:
   - Verify your subscription status with the provider
   - Check if you need to add a correct MAC address

For more detailed troubleshooting, see the specific portal type documentation and the general [Troubleshooting](troubleshooting.md) guide. 