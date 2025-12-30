# Quick Start: Testing Camera UI

This guide shows you how to quickly add fake cameras to test the PumaGuard camera detection UI.

## Prerequisites

- PumaGuard server installed and running
- Python 3.8+ with `requests` library

## Quick Steps

### 1. Start the PumaGuard Server

```bash
cd pumaguard
uv run pumaguard-webui --host 0.0.0.0
```

The server will start at http://localhost:5000

### 2. Add Fake Cameras

In a **new terminal window**, run:

```bash
cd pumaguard
python3 scripts/add_fake_cameras.py
```

This will add 3 fake cameras:
- **Microseven-Cam1** (192.168.52.101) - connected
- **Microseven-Cam2** (192.168.52.102) - connected  
- **Microseven-Cam3** (192.168.52.103) - disconnected

### 3. View the UI

1. Open your browser to http://localhost:5000
2. Scroll down to the **"Detected Cameras"** section in the Quick Actions card
3. You should see all 3 cameras listed with their status

### 4. Test Camera Actions

Click on any camera to open its web interface in a new tab (you'll see a connection error since these are fake IPs).

## Management Commands

### List all cameras
```bash
python3 scripts/add_fake_cameras.py list
```

### Clear all cameras
```bash
python3 scripts/add_fake_cameras.py clear
```

### Add a specific camera
```bash
python3 scripts/add_fake_cameras.py add \
  "TestCamera" \
  "192.168.52.200" \
  "aa:bb:cc:dd:ee:ff" \
  --status connected
```

## Using the Bash Script (Linux/macOS/WSL)

If you prefer bash:

```bash
# Add 3 fake cameras
./scripts/add_fake_cameras.sh

# List cameras
./scripts/add_fake_cameras.sh list

# Clear all cameras
./scripts/add_fake_cameras.sh clear

# Add specific camera
./scripts/add_fake_cameras.sh add TestCam 192.168.52.200 aa:bb:cc:dd:ee:ff connected
```

## Custom API URL

If your server is running on a different host/port:

```bash
# Python
python3 scripts/add_fake_cameras.py --api-url http://192.168.52.1:5000/api/dhcp/cameras

# Bash
PUMAGUARD_API=http://192.168.52.1:5000/api/dhcp/cameras ./scripts/add_fake_cameras.sh
```

## Camera Persistence

Cameras are saved to `~/.config/pumaguard/pumaguard-settings.yaml` and will persist across server restarts. Use the `clear` command to remove them.

## What's Happening Behind the Scenes

1. The script sends POST requests to `/api/dhcp/cameras` endpoint
2. The WebUI stores camera info in memory (`webui.cameras` dict)
3. The camera list is persisted to the settings YAML file
4. The Flutter UI fetches cameras via GET `/api/dhcp/cameras` on page load
5. Cameras are displayed in the Home Screen's Quick Actions section

## Real Camera Detection

In production deployments where PumaGuard runs as a WiFi access point:

1. dnsmasq handles DHCP for connected devices
2. When a camera gets an IP, dnsmasq calls `pumaguard-dhcp-notify.sh`
3. The script sends the same POST request to `/api/dhcp/event`
4. The camera appears automatically in the UI

See `scripts/templates/pumaguard-dhcp-notify.sh.j2` for the DHCP notification script.

## Troubleshooting

### "Connection refused" error
- Make sure the PumaGuard server is running
- Check the API URL (default: http://localhost:5000)

### Cameras not appearing in UI
- Hard refresh the browser (Ctrl+F5 or Cmd+Shift+R)
- Verify cameras were added: `python3 scripts/add_fake_cameras.py list`
- Check server logs for errors

### "requests library not found"
```bash
pip install requests
# or
uv pip install requests
```

## API Reference

For detailed API documentation, see:
- `scripts/README_CAMERA_TESTING.md` - Comprehensive testing guide
- `docs/API_REFERENCE.md` - Full REST API reference
- `pumaguard/web_routes/dhcp.py` - Backend implementation