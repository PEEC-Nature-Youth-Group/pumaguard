# Camera Detection Feature - Implementation Summary

## Overview

The PumaGuard system now includes full support for automatic camera detection and management. When deployed as a WiFi access point, cameras connecting via DHCP are automatically detected, tracked, and displayed in the web UI.

## Architecture

### Backend Components

1. **DHCP Integration** (`scripts/templates/pumaguard-dhcp-notify.sh.j2`)
   - Called by dnsmasq when DHCP lease events occur
   - Filters for cameras by hostname (default: "Microseven")
   - Sends POST requests to `/api/dhcp/event` endpoint

2. **REST API** (`pumaguard/web_routes/dhcp.py`)
   - `POST /api/dhcp/event` - Receives DHCP notifications from dnsmasq script
   - `GET /api/dhcp/cameras` - Returns list of all detected cameras
   - `GET /api/dhcp/cameras/<mac>` - Returns specific camera by MAC address
   - `POST /api/dhcp/cameras` - Manually add camera (for testing)
   - `DELETE /api/dhcp/cameras` - Clear all camera records

3. **Storage** (`pumaguard/web_ui.py`)
   - In-memory: `WebUI.cameras` dict (indexed by MAC address)
   - Persistent: `Preset.cameras` list in `~/.config/pumaguard/pumaguard-settings.yaml`
   - Cameras survive server restarts

4. **Data Model** (`pumaguard/web_ui.py`)
   ```python
   class CameraInfo(TypedDict):
       hostname: str
       ip_address: str
       mac_address: str
       last_seen: str  # ISO8601 timestamp
       status: str     # "connected" or "disconnected"
   ```

### Frontend Components

1. **Flutter Model** (`pumaguard-ui/lib/models/camera.dart`)
   - `Camera` class with JSON serialization
   - Helper methods: `isConnected`, `displayName`, `cameraUrl`

2. **API Service** (`pumaguard-ui/lib/services/api_service.dart`)
   - `getCameras()` - Fetches camera list from backend

3. **Home Screen UI** (`pumaguard-ui/lib/screens/home_screen.dart`)
   - Displays "Detected Cameras" section in Quick Actions card
   - Lists all cameras with hostname, IP, and status
   - Clicking a camera opens its web interface in a new tab
   - Auto-refreshes on page load and manual refresh

## Testing Tools

### Quick Start (Easiest Method)

```bash
# Terminal 1: Start server
uv run pumaguard-webui --host 0.0.0.0

# Terminal 2: Add fake cameras
python3 scripts/add_fake_cameras.py
```

Then open http://localhost:5000 and scroll to "Detected Cameras" section.

### Python Script (`scripts/add_fake_cameras.py`)

**Features:**
- Cross-platform (Windows/Linux/macOS)
- Uses `requests` library
- Colored output for easy debugging
- Comprehensive help text

**Commands:**
```bash
# Add 3 default fake cameras
python3 scripts/add_fake_cameras.py

# List all cameras
python3 scripts/add_fake_cameras.py list

# Clear all cameras
python3 scripts/add_fake_cameras.py clear

# Add specific camera
python3 scripts/add_fake_cameras.py add TestCam 192.168.52.200 aa:bb:cc:dd:ee:ff

# Custom API URL
python3 scripts/add_fake_cameras.py --api-url http://192.168.52.1:5000/api/dhcp/cameras
```

### Bash Script (`scripts/add_fake_cameras.sh`)

**Features:**
- Linux/macOS/WSL compatible
- No dependencies (uses curl)
- Same functionality as Python version

**Commands:**
```bash
# Add 3 default fake cameras
./scripts/add_fake_cameras.sh

# List cameras
./scripts/add_fake_cameras.sh list

# Clear cameras
./scripts/add_fake_cameras.sh clear

# Add specific camera
./scripts/add_fake_cameras.sh add TestCam 192.168.52.200 aa:bb:cc:dd:ee:ff connected
```

## Default Test Cameras

The scripts add these 3 cameras by default:

1. **Microseven-Cam1**
   - IP: 192.168.52.101
   - MAC: aa:bb:cc:dd:ee:01
   - Status: connected

2. **Microseven-Cam2**
   - IP: 192.168.52.102
   - MAC: aa:bb:cc:dd:ee:02
   - Status: connected

3. **Microseven-Cam3**
   - IP: 192.168.52.103
   - MAC: aa:bb:cc:dd:ee:03
   - Status: disconnected

## Data Flow

### Production (Real DHCP Events)

```
Camera connects → dnsmasq assigns IP → pumaguard-dhcp-notify.sh called
    ↓
Script sends POST /api/dhcp/event with camera info
    ↓
Backend updates WebUI.cameras dict and saves to settings.yaml
    ↓
Flutter UI fetches cameras via GET /api/dhcp/cameras
    ↓
Cameras displayed in Home Screen
```

### Testing (Manual Addition)

```
Script sends POST /api/dhcp/cameras with camera info
    ↓
Backend updates WebUI.cameras dict and saves to settings.yaml
    ↓
Flutter UI fetches cameras via GET /api/dhcp/cameras
    ↓
Cameras displayed in Home Screen
```

## API Examples

### Add Camera (Manual)
```bash
curl -X POST http://localhost:5000/api/dhcp/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "TestCamera",
    "ip_address": "192.168.52.200",
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "status": "connected"
  }'
```

### List Cameras
```bash
curl http://localhost:5000/api/dhcp/cameras
```

Response:
```json
{
  "cameras": [
    {
      "hostname": "Microseven-Cam1",
      "ip_address": "192.168.52.101",
      "mac_address": "aa:bb:cc:dd:ee:01",
      "last_seen": "2024-01-15T10:30:00Z",
      "status": "connected"
    }
  ],
  "count": 1
}
```

### Clear All Cameras
```bash
curl -X DELETE http://localhost:5000/api/dhcp/cameras
```

## UI Behavior

### Camera List Display
- Shown in Home Screen's "Quick Actions" card
- Only appears if at least one camera is detected
- Each camera shows:
  - Hostname (or IP if hostname is empty)
  - IP address
  - Status (connected/disconnected)

### Camera Actions
- Click camera → Opens camera web interface in new browser tab
- Uses `http://` by default (configurable per camera)
- Only works on web platform (not mobile/desktop currently)

### Refresh Behavior
- Cameras loaded on page load
- Manual refresh button reloads camera list
- Pull-to-refresh on mobile

## Configuration

### DHCP Script Filtering

Edit `scripts/templates/pumaguard-dhcp-notify.sh.j2`:

```bash
# Change this to match your camera's hostname
CAMERA_HOSTNAME="Microseven"
```

### API Endpoint

Configured in dnsmasq notification script:

```bash
PUMAGUARD_API="http://{{ dnsmasq_gateway }}:5000/api"
```

### Settings File Location

Cameras persisted to:
```
~/.config/pumaguard/pumaguard-settings.yaml
```

Field: `cameras` (list of camera dicts)

## Testing Coverage

Comprehensive unit tests in `tests/test_dhcp_routes.py`:

- ✅ DHCP event handling (add/old/del actions)
- ✅ Camera listing (all and by MAC)
- ✅ Manual camera addition
- ✅ Camera deletion (clear all)
- ✅ Error handling (missing data, not found)
- ✅ Settings persistence

Run tests:
```bash
uv run pytest tests/test_dhcp_routes.py -v
```

## Documentation

- **Quick Start**: `QUICKSTART_CAMERA_UI.md` - Get started in 5 minutes
- **Testing Guide**: `scripts/README_CAMERA_TESTING.md` - Comprehensive testing documentation
- **API Reference**: `docs/API_REFERENCE.md` - Full REST API documentation
- **This Document**: `CAMERA_DETECTION_SUMMARY.md` - Implementation overview

## Future Enhancements

Potential improvements:

1. **UI Enhancements**
   - Dedicated cameras screen (not just in Quick Actions)
   - Camera thumbnails/snapshots
   - Network status indicators
   - Last seen timestamps in human-readable format

2. **Camera Management**
   - Edit camera names
   - Delete individual cameras (not just clear all)
   - Set custom camera URLs per device
   - Camera groups/tags

3. **Mobile Support**
   - Open camera URLs on mobile/desktop platforms
   - Use url_launcher package

4. **Monitoring**
   - Camera uptime tracking
   - Connection history
   - DHCP lease expiration warnings

5. **Security**
   - Camera authentication credentials storage
   - HTTPS support for camera URLs
   - MAC address validation

## Troubleshooting

### Cameras not appearing in UI

1. Check server logs for errors
2. Verify API is accessible: `curl http://localhost:5000/api/dhcp/cameras`
3. Hard refresh browser (Ctrl+F5)
4. Check network connectivity

### DHCP script not triggering

1. Verify dnsmasq is running: `systemctl status dnsmasq`
2. Check dnsmasq config: `/etc/dnsmasq.d/dnsmasq-wlan0.conf`
3. Verify script is executable: `ls -la /usr/local/bin/pumaguard-dhcp-notify.sh`
4. Check script logs: `journalctl -f -t pumaguard-dhcp-notify`

### Camera URLs not opening

1. Verify camera is on same network
2. Check camera web interface is enabled
3. Try accessing camera IP directly in browser
4. Check browser console for errors

## Related Files

### Backend
- `pumaguard/web_ui.py` - WebUI class with camera storage
- `pumaguard/web_routes/dhcp.py` - DHCP API endpoints
- `pumaguard/presets.py` - Settings persistence
- `tests/test_dhcp_routes.py` - Unit tests

### Frontend (Git Submodule)
- `pumaguard-ui/lib/models/camera.dart` - Camera model
- `pumaguard-ui/lib/services/api_service.dart` - API client
- `pumaguard-ui/lib/screens/home_screen.dart` - UI display

### Scripts
- `scripts/templates/dnsmasq-wlan0.conf.j2` - dnsmasq configuration
- `scripts/templates/pumaguard-dhcp-notify.sh.j2` - DHCP event handler
- `scripts/add_fake_cameras.py` - Python testing tool
- `scripts/add_fake_cameras.sh` - Bash testing tool

### Documentation
- `QUICKSTART_CAMERA_UI.md` - Quick start guide
- `scripts/README_CAMERA_TESTING.md` - Testing documentation
- `CAMERA_DETECTION_SUMMARY.md` - This document