# M3U Playlist Portal Type

The M3U Playlist provider allows you to add channels from standard M3U/M3U8 playlists to STB-ReStreamer. This provider supports both local and remote playlist files.

## What is an M3U Playlist?

M3U is a file format that stores multimedia playlists. M3U files are plain text files that specify the locations of media files, with each file path on a new line. M3U8 is a UTF-8 encoded version of the same format.

IPTV providers often distribute channel lists as M3U playlists, which can contain hundreds or thousands of channels with their stream URLs.

## Adding an M3U Playlist Portal

To add an M3U playlist portal:

1. Go to the Portal Management page and click "Add Portal"
2. Fill in the required information:
   - **Portal Name**: A descriptive name for this playlist
   - **Portal Type**: Select "M3U Playlist" from the dropdown
   - **Portal URL**: Enter the URL to the M3U file or a local file path

3. Configure M3U-specific options:
   - **EPG URL**: (Optional) URL to an XMLTV EPG data source
   - **Refresh Interval**: How often to refresh the playlist (in hours)

4. Set additional options as needed:
   - **HTTP Proxy**: If you need to access the playlist through a proxy
   - **Enable Portal**: Should be checked to enable the portal

5. Click "Save Portal" to add the M3U playlist

## Supported URL Formats

The M3U provider supports the following URL formats:

- **Remote HTTP/HTTPS URLs**: `http://example.com/playlist.m3u` or `https://example.com/playlist.m3u8`
- **Local File Paths**: `file:///path/to/playlist.m3u` (Use `file:///C:/path/on/windows.m3u` for Windows)

## Supported Playlist Features

The M3U provider supports the following features in M3U playlists:

- Standard M3U/M3U8 format
- Extended M3U with the `#EXTINF` tag
- Channel groups using the `group-title` attribute
- Channel logos using the `tvg-logo` attribute
- Channel IDs using the `tvg-id` attribute (useful for EPG matching)
- Channel names using the `tvg-name` attribute or display name

Example of a supported M3U entry:

```
#EXTINF:-1 tvg-id="channel1" tvg-name="Channel 1" tvg-logo="http://example.com/logo.png" group-title="News",Channel 1
http://example.com/stream/channel1.m3u8
```

## EPG Integration

To provide program guide data for your M3U playlist:

1. Obtain an XMLTV-format EPG URL from your provider or a third-party service
2. Add this URL to the "EPG URL" field when configuring the portal
3. Set an appropriate refresh interval (usually 24 hours is sufficient)

STB-ReStreamer will automatically:
- Download and parse the XMLTV data
- Match channels in the playlist with EPG data using the `tvg-id` attribute
- Display program information in the interface and stream metadata

## Refresh Behavior

The M3U provider will refresh the playlist according to the configured refresh interval:

- Channels will be updated if they change in the playlist
- New channels will be added
- Removed channels will be marked as unavailable
- Channel order will match the playlist order

## Troubleshooting M3U Playlists

Common issues with M3U playlists:

1. **Playlist not loading**:
   - Verify the URL is correct and accessible
   - Check if the file exists (for local files)
   - Ensure the playlist is properly formatted M3U/M3U8

2. **Missing channels**:
   - Check that the playlist contains valid stream URLs
   - Verify that stream formats are supported (HLS, MPEG-TS, etc.)

3. **EPG not matching**:
   - Ensure channels have proper `tvg-id` attributes that match the EPG data
   - Verify the EPG URL is accessible and contains data for your channels

4. **Slow loading**:
   - Large playlists with thousands of channels may take longer to load
   - Consider splitting into multiple playlist portals by category

## Best Practices

For optimal performance with M3U playlists:

1. Use playlists with fewer than 5,000 channels for best performance
2. Ensure channels have proper `tvg-id` attributes for EPG matching
3. Use direct stream URLs rather than URLs that redirect multiple times
4. Set an appropriate refresh interval (more frequent for regularly updated playlists)
5. Use a local file for very large playlists to reduce network overhead

## Example Playlist

Here's a minimal example of a valid M3U playlist:

```
#EXTM3U
#EXTINF:-1 tvg-id="cnn" tvg-name="CNN" group-title="News",CNN
http://example.com/stream/cnn.m3u8
#EXTINF:-1 tvg-id="bbc" tvg-name="BBC" group-title="News",BBC World News
http://example.com/stream/bbc.m3u8
#EXTINF:-1 tvg-id="espn" tvg-name="ESPN" group-title="Sports",ESPN
http://example.com/stream/espn.m3u8
``` 