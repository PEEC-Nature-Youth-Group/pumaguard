# Camera Tracking via DHCP

PumaGuard includes a camera tracking system that automatically detects when cameras connect to the WiFi hotspot and tracks their connection status.

## Overview

When a camera (or any device) connects to the PumaGuard hotspot, the DHCP server (dnsmasq) triggers a notification script that:
1. Identifies the device by hostname
2. Captures connection details (IP, MAC, timestamp)
3. Notifies the PumaGuard API
4. Stores the camera information in memory

## Architecture

```
Camera connects → dnsmasq assigns IP → dhcp-script called →
pumaguard-dhcp-notify.sh → POST to /api/dhcp/event →
WebUI stores in cameras dict → Available via API
```

## Components

### 1. dnsmasq Configuration
**File:** `/etc/dnsmasq.d/10-pumaguard.conf`

```conf
dhcp-script=/usr/local/bin/pumaguard-dhcp-notify.sh
```

This tells dnsmasq to call the notification script on every DHCP event.

### 2. DHCP Notification Script
**File:** `/usr/local/bin/pumaguard-dhcp-notify.sh`

Bash script that:
- Receives DHCP events (add, old, del) from dnsmasq
- Filters for devices with hostname matching `CAMERA_HOSTNAME` variable
- POSTs JSON payload to PumaGuard API
- Logs all events to journald (systemd journal)

**Default tracked hostname:** `Microseven`

### 3. WebUI Camera Storage
**File:** `pumaguard/web_ui.py`

The `WebUI` class includes:
```python
self.cameras: dict[str, CameraInfo] = {}
```

**CameraInfo structure:**
```python
{
    "hostname": str,        # Device hostname
    "ip_address": str,      # Assigned IP address
    "mac_address": str,     # MAC address (used as key)
    "last_seen": str,       # ISO8601 timestamp
    "status": str          # "connected" or "disconnected"
}
```

### 4. DHCP API Routes
**File:** `pumaguard/web_routes/dhcp.py`

Provides REST endpoints for camera tracking.

## API Endpoints

### POST `/api/dhcp/event`
Receives DHCP event notifications from the notification script.

**Request body:**
```json
{
  "action": "add",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "ip_address": "192.168.52.123",
  "hostname": "Microseven",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "DHCP event processed",
  "data": {
    "action": "add",
    "hostname": "Microseven",
    "ip_address": "192.168.52.123"
  }
}
```

### GET `/api/dhcp/cameras`
Get list of all detected cameras.

**Response:**
```json
{
  "cameras": [
    {
      "hostname": "Microseven",
      "ip_address": "192.168.52.123",
      "mac_address": "aa:bb:cc:dd:ee:ff",
      "last_seen": "2024-01-15T10:30:00Z",
      "status": "connected"
    }
  ],
  "count": 1
}
```

### GET `/api/dhcp/cameras/<mac_address>`
Get specific camera by MAC address.

**Example:** `GET /api/dhcp/cameras/aa:bb:cc:dd:ee:ff`

**Response:**
```json
{
  "hostname": "Microseven",
  "ip_address": "192.168.52.123",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "last_seen": "2024-01-15T10:30:00Z",
  "status": "connected"
}
```

### DELETE `/api/dhcp/cameras`
Clear all camera records from memory.

**Response:**
```json
{
  "status": "success",
  "message": "Cleared 3 camera record(s)"
}
```

## DHCP Event Actions

- **`add`** - New device connected, first time seeing this MAC
- **`old`** - Known device renewed its DHCP lease
- **`del`** - Device disconnected or lease expired

When a device disconnects (`del`), the camera record is **not deleted** but marked as `"status": "disconnected"` to maintain history.

## Configuration

### Tracking Different Cameras

To track cameras with different hostnames, edit the notification script after deployment:

```bash
sudo nano /usr/local/bin/pumaguard-dhcp-notify.sh
```

Change the `CAMERA_HOSTNAME` variable:
```bash
CAMERA_HOSTNAME="YourCameraHostname"
```

Or add to playbook variables (recommended):
```yaml
# In configure-device.yaml vars:
camera_hostname: YourCameraHostname
```

Then update the template to use `{{ camera_hostname }}`.

### Tracking Multiple Camera Types

Modify the script to check multiple hostnames:
```bash
if [[ "$HOSTNAME" == "Microseven" ]] || [[ "$HOSTNAME" == "Reolink" ]]; then
    # Process camera
fi
```

### Pattern Matching

Use bash pattern matching for flexible detection:
```bash
if [[ "$HOSTNAME" =~ ^(Microseven|Camera|CAM) ]]; then
    # Matches any hostname starting with these patterns
fi
```

## Logging

### DHCP Event Log
**Location:** systemd journal (journald)

**View logs:**
```bash
journalctl -f -t pumaguard-dhcp-notify
```

**View recent logs:**
```bash
journalctl -t pumaguard-dhcp-notify -n 50
```

**Example log entries:**
```
Jan 15 10:30:00 pumaguard pumaguard-dhcp-notify[1234]: DHCP add: hostname=Microseven, mac=aa:bb:cc:dd:ee:ff, ip=192.168.52.123
Jan 15 10:30:01 pumaguard pumaguard-dhcp-notify[1234]: Camera detected: Microseven at 192.168.52.123
```

### PumaGuard Application Log
Camera tracking events are also logged to the PumaGuard application log with logger name `pumaguard.web_routes.dhcp`.

## Testing

### Manual Testing

1. **Trigger a test event:**
```bash
sudo /usr/local/bin/pumaguard-dhcp-notify.sh add aa:bb:cc:dd:ee:ff 192.168.52.100 Microseven
```

2. **Check if camera was registered:**
```bash
curl http://192.168.52.1:5000/api/dhcp/cameras
```

3. **View logs:**
```bash
journalctl -t pumaguard-dhcp-notify -n 20
```

### Monitor dnsmasq Events

Watch dnsmasq DHCP activity:
```bash
sudo journalctl -u dnsmasq -f
```

## Troubleshooting

### Script Not Being Called

**Check dnsmasq configuration:**
```bash
grep dhcp-script /etc/dnsmasq.d/10-pumaguard.conf
```

**Verify script exists and is executable:**
```bash
ls -la /usr/local/bin/pumaguard-dhcp-notify.sh
```

**Restart dnsmasq:**
```bash
sudo systemctl restart dnsmasq
```

### Camera Not Detected

**Check hostname sent by camera:**
```bash
# View recent DHCP requests
journalctl -t pumaguard-dhcp-notify -n 50 | grep DHCP
```

**Verify camera hostname matches script:**
```bash
grep CAMERA_HOSTNAME /usr/local/bin/pumaguard-dhcp-notify.sh
```

### API Not Responding

**Check PumaGuard is running:**
```bash
sudo systemctl status pumaguard
curl http://192.168.52.1:5000/api/status
```

**Check firewall:**
```bash
sudo ufw status | grep 5000
```

### Permissions Issues

**Script must be executable:**
```bash
sudo chmod +x /usr/local/bin/pumaguard-dhcp-notify.sh
```

**Verify systemd-cat is available:**
```bash
which systemd-cat
```

## Security Considerations

- The DHCP notification script runs as **root** (required by dnsmasq)
- API endpoint accepts connections from localhost only by default
- No authentication required (assumes trusted local network)
- Camera data stored in memory only (lost on restart)

## Future Enhancements

- **Persistent storage:** Save camera history to database/file
- **WebSocket notifications:** Real-time UI updates when cameras connect
- **Camera metadata:** Store additional info (model, firmware, etc.)
- **Connection statistics:** Track uptime, disconnection frequency
- **Multiple camera support:** Auto-detect camera patterns without hardcoding
- **Camera configuration:** Push settings to cameras via API
- **Health monitoring:** Track camera responsiveness, image quality

## Related Files

- `scripts/templates/dnsmasq-wlan0.conf.j2` - dnsmasq configuration template
- `scripts/templates/pumaguard-dhcp-notify.sh.j2` - Notification script template
- `scripts/configure-device.yaml` - Ansible playbook with installation tasks
- `pumaguard/web_ui.py` - WebUI class with cameras dictionary
- `pumaguard/web_routes/dhcp.py` - DHCP API route handlers

## See Also

- [API_REFERENCE.md](API_REFERENCE.md) - Complete API documentation
- [MDNS_SETUP.md](MDNS_SETUP.md) - Network discovery configuration
- [BUILD_REFERENCE.md](BUILD_REFERENCE.md) - Building and deployment