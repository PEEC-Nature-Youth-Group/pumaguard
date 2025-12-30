# Camera Testing Scripts

This directory contains scripts for testing the camera detection feature in PumaGuard's web UI.

## Overview

When PumaGuard runs as a WiFi access point with dnsmasq, it can automatically detect cameras that connect to the network via DHCP events. These scripts allow you to manually add fake cameras for UI testing without needing actual hardware.

## Scripts

### `add_fake_cameras.py` (Recommended)

Cross-platform Python script for managing fake cameras.

**Requirements:**

```bash
pip install requests
```

**Usage:**

```bash
# Add 3 default fake cameras
python3 scripts/add_fake_cameras.py

# List all cameras
python3 scripts/add_fake_cameras.py list

# Clear all cameras
python3 scripts/add_fake_cameras.py clear

# Add a specific camera
python3 scripts/add_fake_cameras.py add MyCam 192.168.52.200 aa:bb:cc:dd:ee:ff

# Add a disconnected camera
python3 scripts/add_fake_cameras.py add OfflineCam 192.168.52.201 aa:bb:cc:dd:ee:01 --status disconnected

# Use custom API URL
python3 scripts/add_fake_cameras.py --api-url http://192.168.52.1:5000/api/dhcp/cameras

# Or set via environment variable
export PUMAGUARD_API=http://192.168.52.1:5000/api/dhcp/cameras
python3 scripts/add_fake_cameras.py
```

### `add_fake_cameras.sh`

Bash script version (Linux/macOS/WSL only).

**Usage:**

```bash
# Add 3 default fake cameras
./scripts/add_fake_cameras.sh

# List all cameras
./scripts/add_fake_cameras.sh list

# Clear all cameras
./scripts/add_fake_cameras.sh clear

# Add a specific camera
./scripts/add_fake_cameras.sh add MyCam 192.168.52.200 aa:bb:cc:dd:ee:ff connected

# Use custom API URL
PUMAGUARD_API=http://192.168.52.1:5000/api/dhcp/cameras ./scripts/add_fake_cameras.sh
```

## Testing Workflow

1. **Start the PumaGuard server:**

   ```bash
   uv run pumaguard-webui --host 0.0.0.0
   ```

2. **Add fake cameras:**

   ```bash
   # From a separate terminal
   python3 scripts/add_fake_cameras.py
   ```

3. **Check the UI:**
   - Open http://localhost:5000 in your browser
   - Scroll down to the "Detected Cameras" section in the Quick Actions card
   - You should see 3 cameras listed:
     - Microseven-Cam1 (192.168.52.101) - connected
     - Microseven-Cam2 (192.168.52.102) - connected
     - Microseven-Cam3 (192.168.52.103) - disconnected

4. **Click on a camera** to open its web interface (opens in a new tab)

5. **Clear cameras when done:**
   ```bash
   python3 scripts/add_fake_cameras.py clear
   ```

## API Endpoints

The scripts use the following REST API endpoints:

### `POST /api/dhcp/cameras`

Add a camera manually.

**Request:**

```json
{
  "hostname": "Microseven-Cam1",
  "ip_address": "192.168.52.101",
  "mac_address": "aa:bb:cc:dd:ee:01",
  "status": "connected"
}
```

**Response (201):**

```json
{
  "status": "success",
  "message": "Camera added successfully",
  "camera": {
    "hostname": "Microseven-Cam1",
    "ip_address": "192.168.52.101",
    "mac_address": "aa:bb:cc:dd:ee:01",
    "last_seen": "2024-01-15T10:30:00Z",
    "status": "connected"
  }
}
```

### `GET /api/dhcp/cameras`

Get all cameras.

**Response (200):**

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

### `GET /api/dhcp/cameras/<mac_address>`

Get a specific camera by MAC address.

**Response (200):**

```json
{
  "hostname": "Microseven-Cam1",
  "ip_address": "192.168.52.101",
  "mac_address": "aa:bb:cc:dd:ee:01",
  "last_seen": "2024-01-15T10:30:00Z",
  "status": "connected"
}
```

### `DELETE /api/dhcp/cameras`

Clear all cameras.

**Response (200):**

```json
{
  "status": "success",
  "message": "Cleared 3 camera record(s)"
}
```

## Camera Persistence

Cameras added via these scripts are persisted to the PumaGuard settings file:

- Location: `~/.config/pumaguard/pumaguard-settings.yaml`
- Field: `cameras` (list)

This means cameras will survive server restarts. Use the `clear` command to remove them.

## Real DHCP Integration

In production, cameras are automatically detected via the `pumaguard-dhcp-notify.sh` script, which is called by dnsmasq when DHCP lease events occur. See:

- `scripts/templates/dnsmasq-wlan0.conf.j2` - dnsmasq configuration
- `scripts/templates/pumaguard-dhcp-notify.sh.j2` - DHCP event handler
- `pumaguard/web_routes/dhcp.py` - API endpoints

The DHCP script sends the same POST request to `/api/dhcp/event` that contains:

```json
{
  "action": "add",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "ip_address": "192.168.52.100",
  "hostname": "Microseven",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Troubleshooting

### Connection Refused

- Make sure the PumaGuard server is running
- Check the API URL (default: http://localhost:5000)
- If running on a different host, update the URL:
  ```bash
  python3 scripts/add_fake_cameras.py --api-url http://192.168.52.1:5000/api/dhcp/cameras
  ```

### Cameras Not Appearing in UI

- Refresh the browser (F5)
- Check browser console for errors
- Verify cameras were added: `python3 scripts/add_fake_cameras.py list`
- Check server logs for errors

### Cameras Persist After Clearing

- The UI may be cached - hard refresh (Ctrl+F5 or Cmd+Shift+R)
- Verify they're cleared on the backend: `python3 scripts/add_fake_cameras.py list`
- Check the settings file: `cat ~/.config/pumaguard/pumaguard-settings.yaml`

## Development Notes

### UI Implementation

The camera list is displayed in the Home Screen's Quick Actions card:

- File: `pumaguard-ui/lib/screens/home_screen.dart`
- Component: `_buildQuickActionsCard()` method
- The UI polls the API on load and refresh

### Backend Implementation

- Routes: `pumaguard/web_routes/dhcp.py`
- Storage: `WebUI.cameras` dict (indexed by MAC address)
- Persistence: `Preset.cameras` list in settings YAML
- Model: `CameraInfo` TypedDict in `web_ui.py`

### Flutter Model

- File: `pumaguard-ui/lib/models/camera.dart`
- Class: `Camera`
- Properties: `hostname`, `ipAddress`, `macAddress`, `lastSeen`, `status`
