# PumaGuard API Reference

This document describes the REST API that the PumaGuard UI communicates with. Use this reference when developing the Flutter UI in the `pumaguard-ui` repository.

## Base URL

The API is served by the PumaGuard Flask backend:
- **Development**: `http://localhost:5000`
- **Production**: `http://<server-ip>:5000`
- **Web UI**: Uses `Uri.base.origin` to automatically detect the current host

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible on the local network.

## CORS

CORS is enabled for all origins to support web UI access from any IP/hostname.

## API Endpoints

### System & Status

#### GET `/api/status`

Get current server status and configuration.

**Response:**
```json
{
  "status": "running",
  "version": "1.0.0",
  "uptime": 3600,
  "monitored_directories": ["/path/to/folder1", "/path/to/folder2"],
  "total_images": 150
}
```

**Status Codes:**
- `200 OK`: Success

---

#### GET `/api/diagnostic`

Get detailed diagnostic information about the server.

**Response:**
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "flutter_dir": "/path/to/pumaguard-ui",
    "build_dir": "/path/to/pumaguard-ui/build/web",
    "build_exists": true,
    "mdns_enabled": true,
    "mdns_name": "pumaguard",
    "mdns_url": "http://pumaguard.local:5000",
    "local_ip": "192.168.1.100",
    "log_file": "/home/user/.cache/pumaguard/pumaguard.log",
    "log_file_exists": true
  },
  "request": {
    "url": "http://localhost:5000/api/diagnostic",
    "base_url": "http://localhost:5000/api/diagnostic",
    "host": "localhost:5000",
    "origin": "http://localhost:3000",
    "referer": "http://localhost:3000/",
    "user_agent": "Mozilla/5.0 ..."
  },
  "expected_behavior": {
    "flutter_app_should_detect": "http://localhost:5000",
    "api_calls_should_go_to": "http://localhost:5000/api/..."
  },
  "troubleshooting": {
    "if_api_calls_go_to_localhost": "Browser is using cached old JavaScript - clear cache",
    "if_page_doesnt_load": "Check that Flutter app is built: make build-ui",
    "if_cors_errors": "Check browser console for details"
  }
}
```

**Response Fields:**
- `server.log_file`: Path to the server log file (follows XDG Base Directory specification)
- `server.log_file_exists`: Whether the log file currently exists on disk
- `server.host`: Server bind address
- `server.port`: Server port number
- `server.local_ip`: Detected local IP address
- `server.mdns_enabled`: Whether mDNS/Zeroconf is enabled
- `server.mdns_name`: mDNS service name (if enabled)
- `server.mdns_url`: Full mDNS URL (if enabled)

**Status Codes:**
- `200 OK`: Success

---

### Settings

#### GET `/api/settings`

Get current PumaGuard settings.

**Response:**
```json
{
  "YOLO-min-size": 0.02,
  "YOLO-conf-thresh": 0.25,
  "YOLO-max-dets": 12,
  "YOLO-model-filename": "yolov8s_101425.pt",
  "classifier-model-filename": "colorbw_111325.h5",
  "sound-path": "/path/to/sounds",
  "deterrent-sound-file": "cougar_call.mp3",
  "play-sound": true
}
```

**Status Codes:**
- `200 OK`: Success

---

#### PUT `/api/settings`

Update PumaGuard settings.

**Request Body:**
```json
{
  "YOLO-min-size": 0.03,
  "YOLO-conf-thresh": 0.30,
  "YOLO-max-dets": 15,
  "play-sound": false
}
```

**Allowed Settings:**
- `YOLO-min-size` (float): Minimum object size (0.0-1.0)
- `YOLO-conf-thresh` (float): Confidence threshold (0.0-1.0)
- `YOLO-max-dets` (int): Maximum detections
- `YOLO-model-filename` (string): YOLO model file
- `classifier-model-filename` (string): Classifier model file
- `sound-path` (string): Path to sound files
- `deterrent-sound-file` (string): Deterrent sound filename
- `play-sound` (boolean): Enable/disable sound playback

**Response:**
```json
{
  "success": true,
  "message": "Settings updated"
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid data

---

#### POST `/api/settings/save`

Save current settings to a YAML file.

**Request Body:**
```json
{
  "filepath": "/path/to/settings.yaml"  // Optional, uses default if not provided
}
```

**Response:**
```json
{
  "success": true,
  "filepath": "/home/user/.config/pumaguard/settings.yaml"
}
```

**Status Codes:**
- `200 OK`: Success
- `500 Internal Server Error`: Save failed

---

#### POST `/api/settings/load`

Load settings from a YAML file.

**Request Body:**
```json
{
  "filepath": "/path/to/settings.yaml"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Settings loaded"
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: No filepath provided
- `404 Not Found`: File not found

---

### Directories

#### GET `/api/directories`

Get list of monitored image directories.

**Response:**
```json
{
  "directories": [
    "/path/to/folder1",
    "/path/to/folder2"
  ]
}
```

**Status Codes:**
- `200 OK`: Success

---

#### POST `/api/directories`

Add a directory to the watch list.

**Request Body:**
```json
{
  "directory": "/path/to/new/folder"
}
```

**Response:**
```json
{
  "success": true,
  "directories": [
    "/path/to/folder1",
    "/path/to/folder2",
    "/path/to/new/folder"
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: No directory provided or directory doesn't exist

---

#### DELETE `/api/directories/{index}`

Remove a directory from the watch list by index.

**Path Parameters:**
- `index` (integer): Zero-based index of directory to remove

**Response:**
```json
{
  "success": true,
  "directories": [
    "/path/to/folder1"
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid index

---

### Camera Management (DHCP)

#### GET `/api/dhcp/cameras`

Get list of all detected cameras from DHCP events.

**Response:**
```json
{
  "cameras": [
    {
      "hostname": "Microseven",
      "ip_address": "192.168.52.100",
      "mac_address": "aa:bb:cc:dd:ee:ff",
      "last_seen": "2024-01-15T14:30:00Z",
      "status": "connected"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success

---

#### GET `/api/dhcp/cameras/{mac_address}`

Get information about a specific camera by MAC address.

**Path Parameters:**
- `mac_address`: Camera MAC address (e.g., `aa:bb:cc:dd:ee:ff`)

**Response:**
```json
{
  "hostname": "Microseven",
  "ip_address": "192.168.52.100",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "last_seen": "2024-01-15T14:30:00Z",
  "status": "connected"
}
```

**Status Codes:**
- `200 OK`: Success
- `404 Not Found`: Camera not found

---

#### POST `/api/dhcp/event`

Receive DHCP event notifications from dnsmasq script. This endpoint is typically called automatically by the DHCP notification script.

**Request Body:**
```json
{
  "action": "add",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "ip_address": "192.168.52.100",
  "hostname": "Microseven",
  "timestamp": "2024-01-15T14:30:00Z"
}
```

**Fields:**
- `action`: DHCP action - `"add"` (new lease), `"old"` (renewal), or `"del"` (expired)
- `mac_address`: Camera MAC address
- `ip_address`: Assigned IP address
- `hostname`: Device hostname
- `timestamp`: ISO8601 timestamp of the event

**Response:**
```json
{
  "status": "success",
  "message": "DHCP event processed",
  "data": {
    "action": "add",
    "hostname": "Microseven",
    "ip_address": "192.168.52.100"
  }
}
```

**Status Codes:**
- `200 OK`: Event processed successfully
- `400 Bad Request`: Invalid or missing data
- `500 Internal Server Error`: Processing failed

---

#### POST `/api/dhcp/cameras`

Manually add or update a camera record.

**Request Body:**
```json
{
  "hostname": "TestCamera",
  "ip_address": "192.168.52.150",
  "mac_address": "aa:bb:cc:dd:ee:99",
  "status": "connected"
}
```

**Fields:**
- `hostname`: Camera hostname (required)
- `ip_address`: Camera IP address (required)
- `mac_address`: Camera MAC address (required)
- `status`: Connection status - `"connected"` or `"disconnected"` (optional, defaults to `"connected"`)

**Response:**
```json
{
  "status": "success",
  "message": "Camera added successfully",
  "camera": {
    "hostname": "TestCamera",
    "ip_address": "192.168.52.150",
    "mac_address": "aa:bb:cc:dd:ee:99",
    "last_seen": "2024-01-15T14:35:00Z",
    "status": "connected"
  }
}
```

**Status Codes:**
- `200 OK`: Camera added/updated successfully
- `400 Bad Request`: Missing required fields

---

#### POST `/api/dhcp/cameras/heartbeat`

Manually trigger a heartbeat check for all cameras. This immediately checks camera availability and updates their status.

**Response:**
```json
{
  "status": "success",
  "message": "Heartbeat check completed",
  "cameras": {
    "aa:bb:cc:dd:ee:ff": {
      "hostname": "Microseven",
      "ip_address": "192.168.52.100",
      "reachable": true,
      "status": "connected",
      "last_seen": "2024-01-15T14:40:00Z"
    },
    "aa:bb:cc:dd:ee:01": {
      "hostname": "Camera2",
      "ip_address": "192.168.52.101",
      "reachable": false,
      "status": "disconnected",
      "last_seen": "2024-01-15T12:00:00Z"
    }
  }
}
```

**Status Codes:**
- `200 OK`: Heartbeat check completed
- `500 Internal Server Error`: Check failed

**Notes:**
- This triggers an immediate check outside the regular heartbeat interval
- Camera status and `last_seen` are updated based on results
- Check method (ICMP/TCP) is determined by server configuration

---

#### DELETE `/api/dhcp/cameras`

Clear all camera records from memory and settings.

**Response:**
```json
{
  "status": "success",
  "message": "Cleared 3 camera record(s)"
}
```

**Status Codes:**
- `200 OK`: Cameras cleared successfully

---

### Photos & Images

#### GET `/api/photos`

Get list of all captured photos across all monitored directories.

**Response:**
```json
{
  "photos": [
    {
      "filename": "image1.jpg",
      "path": "/path/to/folder/image1.jpg",
      "directory": "/path/to/folder",
      "size": 1024000,
      "modified": 1234567890.0,
      "created": 1234567890.0
    }
  ],
  "total": 1
}
```

**Notes:**
- Photos are sorted by modified time (newest first)
- Supported formats: .jpg, .jpeg, .png, .gif, .bmp, .webp

**Status Codes:**
- `200 OK`: Success

---

#### GET `/api/photos/{filepath}`

Get a specific photo file.

**Path Parameters:**
- `filepath` (string): URL-encoded full path to the image

**Example:**
```
GET /api/photos/%2Fpath%2Fto%2Fimage.jpg
```

**Response:**
- Binary image data

**Status Codes:**
- `200 OK`: Success, returns image file
- `403 Forbidden`: File not in allowed directory
- `404 Not Found`: File doesn't exist

**Security:**
- Only files in monitored directories can be accessed
- Path traversal attempts are blocked

---

#### DELETE `/api/photos/{filepath}`

Delete a specific photo.

**Path Parameters:**
- `filepath` (string): URL-encoded full path to the image

**Response:**
```json
{
  "success": true,
  "message": "Photo deleted"
}
```

**Status Codes:**
- `200 OK`: Success
- `403 Forbidden`: File not in allowed directory
- `404 Not Found`: File doesn't exist

---

### Image Browser & Folders

#### GET `/api/folders`

Get list of watched folders with image counts.

**Response:**
```json
{
  "folders": [
    {
      "path": "/path/to/folder1",
      "name": "folder1",
      "image_count": 42
    },
    {
      "path": "/path/to/folder2",
      "name": "folder2",
      "image_count": 15
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success

---

#### GET `/api/folders/{folder_path}/images`

Get list of images in a specific folder.

**Path Parameters:**
- `folder_path` (string): URL-encoded folder path

**Example:**
```
GET /api/folders/%2Fpath%2Fto%2Ffolder1/images
```

**Response:**
```json
{
  "images": [
    {
      "filename": "IMG_001.jpg",
      "path": "/path/to/folder1/IMG_001.jpg",
      "size": 2048000,
      "modified": 1234567890.0,
      "created": 1234567890.0
    }
  ],
  "folder": "/path/to/folder1"
}
```

**Notes:**
- Images sorted by modified time (newest first)
- Only images in allowed directories are returned

**Status Codes:**
- `200 OK`: Success
- `403 Forbidden`: Folder not in allowed directories
- `404 Not Found`: Folder doesn't exist

---

### Smart Sync

#### POST `/api/sync/checksums`

Compare client-side checksums with server-side files to determine what needs to be downloaded.

**Request Body:**
```json
{
  "files": {
    "/path/to/image1.jpg": "abc123def456...",
    "/path/to/image2.jpg": "789ghi012jkl..."
  }
}
```

**Notes:**
- Keys are full file paths on server
- Values are SHA256 checksums (hex string) of local files
- Empty string for checksum means file doesn't exist locally

**Response:**
```json
{
  "files_to_download": [
    {
      "path": "/path/to/image1.jpg",
      "checksum": "xyz789abc123...",
      "size": 2048000,
      "modified": 1234567890.0
    }
  ],
  "total": 1
}
```

**Notes:**
- Returns only files that don't match client checksums
- Files not in allowed directories are silently skipped

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: No files provided

**Use Case:**
This implements rsync-like functionality where only changed or new files are downloaded.

---

#### POST `/api/sync/download`

Download one or more files.

**Request Body:**
```json
{
  "files": [
    "/path/to/image1.jpg",
    "/path/to/image2.jpg"
  ]
}
```

**Response:**
- **Single file**: Binary image data with original filename
- **Multiple files**: ZIP archive containing all files (filename: `pumaguard_images.zip`)

**Headers:**
- Single file: `Content-Type: image/jpeg` (or appropriate type)
- Multiple files: `Content-Type: application/zip`
- `Content-Disposition: attachment; filename="..."`

**Status Codes:**
- `200 OK`: Success, returns file(s)
- `400 Bad Request`: No files provided or no valid files
- `403 Forbidden`: Files not in allowed directories

**Notes:**
- Only files in monitored directories can be downloaded
- Invalid file paths are silently skipped
- ZIP file contains files with their original filenames

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Description of what went wrong"
}
```

Common HTTP status codes:
- `200 OK`: Request succeeded
- `400 Bad Request`: Invalid request data
- `403 Forbidden`: Access denied (path not allowed)
- `404 Not Found`: Resource doesn't exist
- `500 Internal Server Error`: Server-side error

## Data Types

### Timestamp
- Format: Unix timestamp (float)
- Represents seconds since epoch
- Example: `1234567890.0` = 2009-02-13 23:31:30 UTC

### File Size
- Format: Integer (bytes)
- Example: `1024000` = 1000 KB

### File Path
- Format: Absolute path string
- Must be in a monitored directory
- Example: `/home/user/pumaguard/images/photo.jpg`

### Checksum
- Format: SHA256 hex string (64 characters)
- Example: `"abc123def456789..."`

## Security Considerations

### Path Validation
All file paths are validated to ensure they are within monitored directories:
```python
abs_filepath = os.path.abspath(filepath)
allowed = abs_filepath.startswith(allowed_directory)
```

### Path Traversal Prevention
- All paths converted to absolute paths
- Checked against allowed directory list
- `../` and similar patterns are neutralized

### CORS
- Enabled for all origins
- Required for web UI to work from any IP/hostname
- All methods (GET, POST, PUT, DELETE, OPTIONS) allowed

## mDNS Service Discovery

PumaGuard advertises itself via mDNS (Zeroconf):
- Service type: `_pumaguard._tcp.local.`
- Default port: `5000`
- Can be disabled with `--no-mdns` flag

The Flutter UI can discover PumaGuard servers on the local network using the `multicast_dns` package.

## Image File Types

Supported image extensions:
- `.jpg`, `.jpeg`
- `.png`
- `.gif`
- `.bmp`
- `.webp`

Files with other extensions are ignored by the API.

## API Usage Examples

### Flutter/Dart

```dart
// Get status
final response = await http.get(
  Uri.parse('http://localhost:5000/api/status'),
  headers: {'Content-Type': 'application/json'},
);
final data = jsonDecode(response.body);

// Update settings
await http.put(
  Uri.parse('http://localhost:5000/api/settings'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'YOLO-conf-thresh': 0.30,
    'play-sound': false,
  }),
);

// Get folders
final folders = await http.get(
  Uri.parse('http://localhost:5000/api/folders'),
);

// Download files
final files = ['/path/to/image1.jpg', '/path/to/image2.jpg'];
final response = await http.post(
  Uri.parse('http://localhost:5000/api/sync/download'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({'files': files}),
);
final zipBytes = response.bodyBytes;
```

### cURL

```bash
# Get status
curl http://localhost:5000/api/status

# Update settings
curl -X PUT http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"YOLO-conf-thresh": 0.30}'

# Get folders
curl http://localhost:5000/api/folders

# Get diagnostic info including log file path
curl http://localhost:5000/api/diagnostic

# Get just the log file path using jq
curl -s http://localhost:5000/api/diagnostic | jq -r '.server.log_file'

# Download image
curl http://localhost:5000/api/photos/%2Fpath%2Fto%2Fimage.jpg -o image.jpg

# Download multiple as ZIP
curl -X POST http://localhost:5000/api/sync/download \
  -H "Content-Type: application/json" \
  -d '{"files": ["/path/to/image1.jpg", "/path/to/image2.jpg"]}' \
  -o images.zip
```

## Rate Limiting

Currently, there is no rate limiting implemented. Consider implementing rate limiting if exposing the API to untrusted networks.

## Future API Extensions

Planned but not yet implemented:
- Authentication and authorization
- WebSocket support for real-time updates
- Pagination for large image lists
- Image thumbnail generation
- Batch operations (delete multiple files)
- Search and filter endpoints
- Classification result history

## Changelog

### Version 1.0
- Initial API implementation
- Settings management
- Directory monitoring
- Photo listing and access
- Image browser with folders
- Smart sync with checksums
- File download (single and ZIP)

## Support

For API issues or questions:
- GitHub: https://github.com/PEEC-Nature-Youth-Group/pumaguard
- Documentation: http://pumaguard.rtfd.io/