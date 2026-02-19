# Device Auto-Removal Feature

## Overview

PumaGuard includes an automatic device removal feature that removes cameras and plugs from the device list after a configurable period of inactivity. This helps keep the device lists clean and relevant by automatically removing devices that are no longer in use or have been offline for an extended period.

## Features

- **Configurable timeout**: Set the number of hours a device (camera or plug) must be inactive before removal
- **Enable/disable control**: Turn auto-removal on or off as needed
- **Integration with heartbeat monitoring**: Works seamlessly with both camera and plug heartbeat systems
- **SSE notifications**: Broadcasts removal events to all connected web UI clients
- **Persistent settings**: Configuration is saved and survives server restarts
- **Safe by default**: Auto-removal is **disabled by default** to prevent accidental data loss
- **Unified configuration**: One setting applies to both cameras and plugs

## Configuration

All auto-removal settings are stored in `~/.config/pumaguard/pumaguard-settings.yaml` and can be configured via the settings API or by editing the file directly.

### Settings

| Setting                      | Default | Description                                       |
| ---------------------------- | ------- | ------------------------------------------------- |
| `device-auto-remove-enabled` | `false` | Enable/disable automatic device removal           |
| `device-auto-remove-hours`   | `24`    | Hours of inactivity before auto-removal           |

**Note**: For backward compatibility, the old `camera-auto-remove-enabled` and `camera-auto-remove-hours` settings are still supported but will be deprecated. The new `device-auto-remove-*` settings apply to both cameras and plugs.

### Example Configuration

```yaml
# Enable auto-removal after 48 hours of inactivity (applies to both cameras and plugs)
device-auto-remove-enabled: true
device-auto-remove-hours: 48

# Heartbeat settings (must be enabled for auto-removal to work)
camera-heartbeat-enabled: true
camera-heartbeat-interval: 60
plug-heartbeat-enabled: true
plug-heartbeat-interval: 60
```

## How It Works

### Detection Logic

1. **Heartbeat monitoring** runs in the background and tracks camera and plug status
2. Each heartbeat cycle updates the `last_seen` timestamp for reachable devices
3. **Auto-removal check** runs during each heartbeat cycle (if enabled)
4. Devices (cameras or plugs) with `last_seen` timestamp older than configured hours are removed
5. **Removal notification** is sent via Server-Sent Events (SSE) to all UI clients

### Workflow

```
Heartbeat Check → Camera unreachable → Status = "disconnected"
                                      → last_seen NOT updated
                                      → Time passes...
                                      ↓
Auto-removal Check → Calculate: now - last_seen
                  → If > configured hours → Remove camera
                                         → Save settings
                                         → Notify UI clients
```

### Safety Features

- **Disabled by default**: Must be explicitly enabled to prevent accidental removal
- **Timestamp-based**: Only removes cameras with valid `last_seen` timestamps
- **Error handling**: Invalid timestamps or missing data prevent removal
- **Logging**: All removals are logged with camera details and timestamps
- **Graceful degradation**: Errors in callback or persistence don't crash the monitor

## Usage

### Enable Auto-Removal via Web UI

The easiest way to configure device auto-removal is through the web interface:

1. Navigate to **Settings** page in the PumaGuard web UI
2. Scroll to the **System Settings** section
3. Find the **Device Auto-Removal** subsection
4. Toggle **Enable Auto-Removal** switch to turn the feature on/off
5. When enabled, adjust the **Inactivity Threshold (hours)** field to set the timeout
6. Settings are automatically saved when changed

The UI will show:
- A toggle switch to enable/disable the feature (applies to both cameras and plugs)
- An input field for the inactivity threshold (only visible when enabled)
- Helper text explaining that the setting applies to both cameras and plugs

### Enable Auto-Removal via API

```bash
# Enable auto-removal with 24-hour timeout (applies to both cameras and plugs)
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "device-auto-remove-enabled": true,
    "device-auto-remove-hours": 24
  }'
```

### Disable Auto-Removal via API

```bash
# Disable auto-removal
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "device-auto-remove-enabled": false
  }'
```

### Configure via Settings File

Edit `~/.config/pumaguard/pumaguard-settings.yaml`:

```yaml
device-auto-remove-enabled: true
device-auto-remove-hours: 48 # Remove after 48 hours (both cameras and plugs)
```

Then restart the PumaGuard server for changes to take effect.

### Monitor Removal Events

The server logs all auto-removal events and periodic status updates:

```bash
# Watch server logs for removal events (cameras and plugs)
journalctl -u pumaguard -f | grep "Auto-removed"

# Watch debug logs for offline device status (debugging)
journalctl -u pumaguard -f | grep "offline"
```

Example log output:

```
# Debug logs (periodic updates during each heartbeat check)
DEBUG: Camera 'Microseven-Cam1' (aa:bb:cc:dd:ee:01) at 192.168.52.101 has been offline for 12.5 hours, will be auto-removed in 11.5 hours
DEBUG: Plug 'KasaPlug-1' (bb:cc:dd:ee:ff:01) at 192.168.52.201 has been offline for 5.2 hours, will be auto-removed in 18.8 hours

# Info logs (when device is scheduled for removal)
INFO: Camera 'Microseven-Cam1' (aa:bb:cc:dd:ee:01) not seen for 25.3 hours, scheduling for auto-removal
INFO: Auto-removed camera 'Microseven-Cam1' (aa:bb:cc:dd:ee:01) at 192.168.52.101
INFO: Plug 'KasaPlug-1' (bb:cc:dd:ee:ff:01) not seen for 24.5 hours, scheduling for auto-removal
INFO: Auto-removed plug 'KasaPlug-1' (bb:cc:dd:ee:ff:01) at 192.168.52.201
```

**Debug Logging**: When auto-removal is enabled and devices are offline (disconnected), the heartbeat monitors log periodic status updates showing:
- How long each device (camera or plug) has been offline
- How much time remains until the device will be auto-removed
- This helps with debugging and monitoring device health

When auto-removal is disabled, offline devices are still logged but with a note that auto-removal is disabled.

## Use Cases

### Scenario 1: Temporary Test Devices

**Problem**: Test cameras and plugs added during development clutter the production device lists.

**Solution**: Enable auto-removal with a short timeout (e.g., 1-2 hours):

```yaml
device-auto-remove-enabled: true
device-auto-remove-hours: 2
```

Test cameras will be automatically removed 2 hours after they go offline.

### Scenario 2: Seasonal Device Deployment

**Problem**: Cameras and plugs are deployed seasonally and should be automatically cleaned up when not in use.

**Solution**: Enable auto-removal with a longer timeout (e.g., 7 days):

```yaml
device-auto-remove-enabled: true
device-auto-remove-hours: 168 # 7 days = 7 * 24 hours
```

Cameras removed from the field will be automatically cleaned up after a week.

### Scenario 3: Permanent Device Installation

**Problem**: Cameras and plugs are permanently installed and should never be auto-removed.

**Solution**: Disable auto-removal entirely:

```yaml
device-auto-remove-enabled: false
```

Cameras will remain in the list indefinitely, even if offline.

### Scenario 4: Mixed Environment

**Problem**: Some devices may go offline temporarily (network issues, power outages) but should not be removed immediately.

**Solution**: Enable auto-removal with a very long timeout (e.g., 30 days):

```yaml
device-auto-remove-enabled: true
device-auto-remove-hours: 720 # 30 days
```

Temporary cameras are cleaned up automatically, while permanent cameras remain due to regular heartbeat checks.

## Configuration Examples

### Conservative (Long Timeout)

```yaml
device-auto-remove-enabled: true
device-auto-remove-hours: 720 # 30 days
camera-heartbeat-enabled: true
camera-heartbeat-interval: 300 # Check every 5 minutes
plug-heartbeat-enabled: true
plug-heartbeat-interval: 300
```

### Moderate (Default-ish)

```yaml
device-auto-remove-enabled: true
device-auto-remove-hours: 168 # 7 days
camera-heartbeat-enabled: true
camera-heartbeat-interval: 60 # Check every minute
plug-heartbeat-enabled: true
plug-heartbeat-interval: 60
```

### Aggressive (Short Timeout)

```yaml
device-auto-remove-enabled: true
device-auto-remove-hours: 1 # 1 hour
camera-heartbeat-enabled: true
camera-heartbeat-interval: 30 # Check every 30 seconds
plug-heartbeat-enabled: true
plug-heartbeat-interval: 30
```

### Disabled (No Auto-Removal)

Preserves all cameras indefinitely:

```yaml
device-auto-remove-enabled: false
camera-heartbeat-enabled: true # Still monitor status
camera-heartbeat-interval: 60
plug-heartbeat-enabled: true
plug-heartbeat-interval: 60
```

## Integration with Heartbeat Monitoring

Auto-removal **requires** camera heartbeat monitoring to be enabled. The heartbeat monitor:

1. Updates camera status (connected/disconnected)
2. Updates `last_seen` timestamp when cameras are reachable
3. Runs auto-removal check during each monitoring cycle

**Important**: If heartbeat monitoring is disabled, auto-removal will not function.

### Recommended Configuration

```yaml
# Enable heartbeat monitoring for cameras
camera-heartbeat-enabled: true
camera-heartbeat-interval: 60 # seconds
camera-heartbeat-method: "tcp" # or "icmp" or "both"

# Enable heartbeat monitoring for plugs
plug-heartbeat-enabled: true
plug-heartbeat-interval: 60 # seconds

# Enable auto-removal for both cameras and plugs
device-auto-remove-enabled: true
device-auto-remove-hours: 24 # hours
```

## Troubleshooting

### Devices Not Being Removed

**Problem**: Cameras or plugs remain in the list despite being inactive for longer than configured timeout.

**Possible Causes**:

1. Auto-removal is disabled
2. Heartbeat monitoring is disabled for cameras/plugs
3. Device has no `last_seen` timestamp
4. Device `last_seen` is being updated (device is still reachable)

**Solutions**:

```bash
# Check configuration
cat ~/.config/pumaguard/pumaguard-settings.yaml | grep -A 2 "device-auto-remove"

# Verify auto-removal is enabled
grep "device-auto-remove-enabled: true" ~/.config/pumaguard/pumaguard-settings.yaml

# Verify heartbeat is enabled for cameras and plugs
grep "camera-heartbeat-enabled: true" ~/.config/pumaguard/pumaguard-settings.yaml
grep "plug-heartbeat-enabled: true" ~/.config/pumaguard/pumaguard-settings.yaml

# Check device last_seen timestamps
curl http://localhost:5000/api/dhcp/cameras | jq '.cameras[] | {hostname, last_seen}'
curl http://localhost:5000/api/dhcp/plugs | jq '.plugs[] | {hostname, last_seen}'

# Check server logs
journalctl -u pumaguard -n 100 | grep -i "auto-remove"
```

### Devices Removed Too Quickly

**Problem**: Devices are being removed sooner than expected.

**Solution**: Increase the `device-auto-remove-hours` setting:

```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "device-auto-remove-hours": 168
  }'
```

### Devices Removed During Network Outage

**Problem**: Devices are removed during temporary network outages.

**Solutions**:

1. Increase timeout to account for expected outages:

   ```yaml
   device-auto-remove-hours: 72 # 3 days
   ```

2. Disable auto-removal if outages are frequent:

   ```yaml
   device-auto-remove-enabled: false
   ```

3. Improve network reliability to reduce heartbeat check failures

### Device Re-appears After Removal

**Problem**: A device is auto-removed but immediately re-appears.

**Cause**: Device is still connected to network and responds to DHCP/heartbeat checks.

**Solution**: This is expected behavior. The device will be re-detected via:

- DHCP lease events (if connected to PumaGuard hotspot)
- Manual addition via API

To permanently remove a camera, disconnect it from the network or use manual removal.

## API Reference

### Device Removal Events (SSE)

When a camera or plug is auto-removed, an SSE event is broadcast to all connected clients:

**Event Types**: `camera_removed`, `plug_removed`

**Event Data**:

```json
{
  "type": "camera_removed",
  "data": {
    "hostname": "Microseven-Cam1",
    "ip_address": "192.168.52.101",
    "mac_address": "aa:bb:cc:dd:ee:01",
    "last_seen": "2024-01-15T10:00:00Z",
    "status": "disconnected"
  },
  "timestamp": "2024-01-16T11:00:00Z"
}
```

### Update Settings

See [Settings API](API_REFERENCE.md#settings-management) for details on updating auto-removal configuration.

## Performance Considerations

- **Minimal overhead**: Auto-removal check runs during heartbeat cycle (no additional threads)
- **Timestamp comparison**: Simple arithmetic operation, very fast
- **Batch removal**: Multiple cameras can be removed in a single check cycle
- **Memory impact**: Negligible - only stores two configuration values
- **CPU impact**: Negligible - check runs at heartbeat interval (default 60 seconds)

## Security Considerations

- Auto-removal does not delete any image files or classification data
- Only removes camera metadata from device list
- Cameras can be re-added via DHCP or manual API calls
- Settings file uses standard YAML format with no sensitive data
- No external network access required

## Comparison with Manual Removal

| Feature              | Auto-Removal           | Manual Removal       |
| -------------------- | ---------------------- | -------------------- |
| **Trigger**          | Automatic (time-based) | Manual (user action) |
| **Configuration**    | Settings file or API   | N/A                  |
| **Granularity**      | Global (all cameras)   | Per-camera           |
| **Use case**         | Ongoing maintenance    | One-off cleanup      |
| **Reversible**       | Camera can reconnect   | Camera can reconnect |
| **SSE notification** | Yes                    | Yes                  |
| **Logging**          | Yes (automatic)        | Yes (on request)     |

Both removal methods:

- Remove camera from in-memory dictionary
- Persist changes to settings file
- Send SSE notifications to UI clients
- Allow camera re-detection via DHCP

## Future Enhancements

Potential improvements for future versions:

- [ ] Per-camera auto-removal timeout
- [ ] Grace period after first detection
- [ ] Removal history/audit log
- [ ] Restore/undo removed cameras
- [ ] Notification webhooks for removal events
- [ ] Auto-removal statistics dashboard
- [ ] Whitelist/blacklist for specific MACs
- [ ] Integration with alert system
- [ ] Configurable removal criteria (beyond time)

## Related Documentation

- [Camera Heartbeat Monitoring](CAMERA_HEARTBEAT.md) - Background monitoring system
- [Device Removal Feature](DEVICE_REMOVAL.md) - Manual removal via UI/API
- [Camera Tracking via DHCP](CAMERA_TRACKING.md) - Camera detection system
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Settings Management](../README.md#settings) - Configuration file format

## Testing

Comprehensive tests are available in `tests/test_camera_heartbeat.py`:

```bash
# Run all auto-removal tests
uv run pytest tests/test_camera_heartbeat.py -k "auto_removal" -v

# Run stale camera removal tests
uv run pytest tests/test_camera_heartbeat.py -k "stale" -v

# Run all camera heartbeat tests
uv run pytest tests/test_camera_heartbeat.py -v
```

Test coverage includes:

- ✅ Initialization with auto-removal settings
- ✅ Removal of cameras exceeding timeout
- ✅ Preservation of recent cameras
- ✅ Handling of missing timestamps
- ✅ Handling of invalid timestamps
- ✅ Multiple camera removal
- ✅ Callback error handling
- ✅ Integration with monitor loop
- ✅ Disabled auto-removal behavior

## Summary

The camera auto-removal feature provides automated cleanup of inactive cameras based on configurable timeout periods. It integrates seamlessly with the existing heartbeat monitoring system and maintains safety through:

- **Opt-in design**: Disabled by default
- **Flexible configuration**: Adjustable timeout from hours to months
- **Safe operation**: Handles edge cases gracefully
- **Full visibility**: Comprehensive logging and SSE notifications

This feature is ideal for deployments where camera availability changes over time and manual list maintenance is impractical.
