# Device Removal Feature

## Overview

This document describes the manual device removal functionality for cameras and plugs in PumaGuard. Users can now remove devices that are no longer needed or available from the system.

## Features

- **Manual Removal**: Remove individual cameras or plugs via the web UI
- **Confirmation Dialog**: Prevents accidental deletion with a confirmation prompt
- **Automatic Cleanup**: Removes device from memory and persists changes to settings
- **Real-time Updates**: UI automatically refreshes after device removal
- **Automatic Re-detection**: Removed devices can be automatically re-added when they reconnect to the network

## User Interface

### Removing a Camera

1. Navigate to **Settings** screen
2. Scroll to the **Detected Cameras** section
3. Find the camera you want to remove
4. Click the **red delete icon** on the right side of the camera card
5. Confirm the removal in the dialog that appears
6. The camera will be removed and a success message will appear

### Removing a Plug

1. Navigate to **Settings** screen
2. Scroll to the **Detected Plugs** section
3. Find the plug you want to remove
4. Click the **red delete icon** on the right side of the plug card
5. Confirm the removal in the dialog that appears
6. The plug will be removed and a success message will appear

## Device Re-detection After Removal

### How It Works

When a device is removed via the UI, PumaGuard:

1. **Removes the device from the active list** - The device is deleted from memory and settings
2. **Maintains device history** - The MAC address and original hostname are preserved in an internal history
3. **Monitors DHCP events** - The system continues to receive DHCP lease notifications from dnsmasq
4. **Recognizes returning devices** - When a removed device renews its DHCP lease, it's automatically re-added

### Why This Happens

DHCP lease renewals don't always include the device hostname (especially during RENEW requests). Without device history, PumaGuard wouldn't be able to recognize a device by its MAC address alone when the hostname is "unknown".

The device history mechanism solves this by:
- Tracking all devices ever seen by MAC address
- Preserving the original hostname from when the device first connected
- Using this information to identify devices even when hostname is missing

### Example Scenario

1. Camera "Microseven-Cam1" connects → detected and added to list
2. User removes camera via UI → camera disappears from list
3. Camera remains connected and renews DHCP lease
4. DHCP server sends renewal notification with MAC but no hostname ("unknown")
5. PumaGuard recognizes MAC from device history → camera re-appears with original name

### Preventing Re-detection

If you want to permanently remove a device and prevent automatic re-detection:

1. **Disconnect the device from the network** - Power it off or disconnect from WiFi
2. **Remove it via the UI** - This clears it from the active list
3. **Optional**: Configure hostname filtering in the DHCP script to ignore specific device types

### Device History Persistence

Device history is:
- **Persisted to settings file** (`~/.config/pumaguard/pumaguard-settings.yaml`)
- **Loaded automatically** on server startup
- **Updated automatically** when devices connect with valid hostnames
- **Survives server restarts** (persists across removals and restarts)
- **Never explicitly cleared** (accumulates all devices ever seen)

The settings file includes a `device-history` section:
```yaml
device-history:
  "aa:bb:cc:dd:ee:ff":
    type: "camera"
    hostname: "Microseven-Cam1"
  "bb:cc:dd:ee:ff:00":
    type: "plug"
    hostname: "shellyplug-office"
```

## API Endpoints

### Remove Camera

**Endpoint:** `DELETE /api/dhcp/cameras/<mac_address>`

Removes a specific camera by MAC address. The device can be automatically re-detected if it reconnects.

**Parameters:**

- `mac_address` (path): MAC address of the camera (e.g., `aa:bb:cc:dd:ee:ff`)

**Response (200 OK):**

```json
{
  "status": "success",
  "message": "Camera 'camera-name' removed",
  "camera": {
    "hostname": "camera-name",
    "ip_address": "192.168.1.100",
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "last_seen": "2024-01-15T10:00:00Z",
    "status": "disconnected"
  }
}
```

**Response (404 Not Found):**

```json
{
  "error": "Camera not found",
  "mac_address": "aa:bb:cc:dd:ee:ff"
}
```

### Remove Plug

**Endpoint:** `DELETE /api/dhcp/plugs/<mac_address>`

Removes a specific plug by MAC address.

**Parameters:**

- `mac_address` (path): MAC address of the plug (e.g., `11:22:33:44:55:66`)

**Response (200 OK):**

```json
{
  "status": "success",
  "message": "Plug 'plug-name' removed",
  "plug": {
    "hostname": "plug-name",
    "ip_address": "192.168.1.200",
    "mac_address": "11:22:33:44:55:66",
    "last_seen": "2024-01-15T10:00:00Z",
    "status": "disconnected",
    "mode": "off"
  }
}
```

**Response (404 Not Found):**

```json
{
  "error": "Plug not found",
  "mac_address": "11:22:33:44:55:66"
}
```

## Backend Implementation

### Camera Removal

The backend implementation in `pumaguard/web_routes/dhcp.py` handles:

1. **Validation**: Checks if the camera exists
2. **Memory Cleanup**: Removes camera from `webui.cameras` dictionary
3. **Settings Persistence**: Updates and saves the camera list to settings file
4. **SSE Notification**: Broadcasts `camera_removed` event to all connected clients
5. **Logging**: Records the removal in the server logs

### Plug Removal

Similar to camera removal, the plug removal endpoint:

1. **Validation**: Checks if the plug exists
2. **Memory Cleanup**: Removes plug from `webui.plugs` dictionary
3. **Settings Persistence**: Updates and saves the plug list to settings file
4. **SSE Notification**: Broadcasts `plug_removed` event to all connected clients
5. **Logging**: Records the removal in the server logs

## Frontend Implementation

### API Service Methods

Two new methods were added to `pumaguard-ui/lib/services/api_service.dart`:

```dart
/// Delete a camera by MAC address
Future<void> deleteCamera(String macAddress) async

/// Delete a plug by MAC address
Future<void> deletePlug(String macAddress) async
```

### Settings Screen Updates

The settings screen (`pumaguard-ui/lib/screens/settings_screen.dart`) was updated to:

- Add delete icon button to each camera card
- Add delete icon button to each plug card
- Show confirmation dialog before deletion
- Display success/error messages
- Automatically refresh the device list after removal
- Refresh Shelly status after plug removal

## Testing

### Unit Tests

Tests were added to `tests/test_dhcp_routes.py`:

- `test_remove_camera`: Tests successful camera removal
- `test_remove_camera_not_found`: Tests removing non-existent camera
- `test_remove_plug`: Tests successful plug removal
- `test_remove_plug_not_found`: Tests removing non-existent plug

All tests pass with 100% success rate.

### Manual Testing

To manually test device removal:

1. Start the PumaGuard server
2. Add a test camera or plug via API or DHCP
3. Open the web UI and navigate to Settings
4. Try removing the device using the delete button
5. Verify the device is removed from the list
6. Check server logs for removal confirmation
7. Restart the server and verify the device doesn't reappear

## Use Cases

### When to Remove Devices

- **Decommissioned Hardware**: Camera or plug is no longer in use
- **Replaced Devices**: Old device replaced with a new one (different MAC address)
- **Test Devices**: Removing devices added for testing purposes
- **Network Changes**: Device moved to different network or location
- **Offline Devices**: Device has been offline for extended period and won't return

### What Happens After Removal

1. Device is immediately removed from the UI
2. Device is removed from in-memory cache
3. Device is removed from settings file (`~/.config/pumaguard/pumaguard-settings.yaml`)
4. Heartbeat monitoring stops checking the device
5. All connected UI clients receive a removal notification via SSE

### Re-adding Removed Devices

If a removed device reconnects to the network:

- **Camera**: Will be automatically re-detected via DHCP events
- **Plug**: Will be automatically re-detected via DHCP events

The device will appear as a "new" device with a fresh `last_seen` timestamp.

## Future Enhancements

Potential improvements to device removal:

- **Bulk Removal**: Select and remove multiple devices at once
- **Removal History**: Log of removed devices with timestamps
- **Soft Delete**: Mark devices as "archived" instead of permanent removal
- **Auto-removal**: Automatically remove devices offline for X days
- **Export/Import**: Export device list before bulk removal
- **Undo Function**: Restore recently removed devices

## Related Files

### Backend

- `pumaguard/web_routes/dhcp.py` - Device removal endpoints
- `pumaguard/camera_heartbeat.py` - Camera heartbeat monitoring
- `pumaguard/plug_heartbeat.py` - Plug heartbeat monitoring

### Frontend

- `pumaguard-ui/lib/services/api_service.dart` - API methods
- `pumaguard-ui/lib/screens/settings_screen.dart` - UI implementation
- `pumaguard-ui/lib/models/camera.dart` - Camera model
- `pumaguard-ui/lib/models/plug.dart` - Plug model

### Tests

- `pumaguard/tests/test_dhcp_routes.py` - Unit tests for removal endpoints

## References

- [Camera Status Refresh](CAMERA_STATUS_REFRESH.md) - Related SSE notification system
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [DHCP Integration](../README.md#dhcp-integration) - Device discovery system
