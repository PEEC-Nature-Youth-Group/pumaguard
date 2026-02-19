# Camera Auto-Removal Feature

## Overview

PumaGuard includes an automatic camera removal feature that removes cameras from the device list after a configurable period of inactivity. This helps keep the camera list clean and relevant by automatically removing cameras that are no longer in use or have been offline for an extended period.

## Features

- **Configurable timeout**: Set the number of hours a camera must be inactive before removal
- **Enable/disable control**: Turn auto-removal on or off as needed
- **Integration with heartbeat monitoring**: Works seamlessly with the existing camera heartbeat system
- **SSE notifications**: Broadcasts removal events to all connected web UI clients
- **Persistent settings**: Configuration is saved and survives server restarts
- **Safe by default**: Auto-removal is **disabled by default** to prevent accidental data loss

## Configuration

All auto-removal settings are stored in `~/.config/pumaguard/pumaguard-settings.yaml` and can be configured via the settings API or by editing the file directly.

### Settings

| Setting                      | Default | Description                             |
| ---------------------------- | ------- | --------------------------------------- |
| `camera-auto-remove-enabled` | `false` | Enable/disable automatic camera removal |
| `camera-auto-remove-hours`   | `24`    | Hours of inactivity before auto-removal |

### Example Configuration

```yaml
# Enable auto-removal after 48 hours of inactivity
camera-auto-remove-enabled: true
camera-auto-remove-hours: 48

# Camera heartbeat settings (must be enabled for auto-removal to work)
camera-heartbeat-enabled: true
camera-heartbeat-interval: 60
```

## How It Works

### Detection Logic

1. **Heartbeat monitoring** runs in the background and tracks camera status
2. Each heartbeat cycle updates the `last_seen` timestamp for reachable cameras
3. **Auto-removal check** runs during each heartbeat cycle (if enabled)
4. Cameras with `last_seen` timestamp older than configured hours are removed
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

The easiest way to configure camera auto-removal is through the web interface:

1. Navigate to **Settings** page in the PumaGuard web UI
2. Scroll to the **System Settings** section
3. Find the **Camera Auto-Removal** subsection
4. Toggle **Enable Auto-Removal** switch to turn the feature on/off
5. When enabled, adjust the **Inactivity Threshold (hours)** field to set the timeout
6. Settings are automatically saved when changed

The UI will show:
- A toggle switch to enable/disable the feature
- An input field for the inactivity threshold (only visible when enabled)
- Helper text explaining each setting

### Enable Auto-Removal via API

```bash
# Enable auto-removal with 24-hour timeout
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "camera-auto-remove-enabled": true,
    "camera-auto-remove-hours": 24
  }'
```

### Disable Auto-Removal via API

```bash
# Disable auto-removal
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "camera-auto-remove-enabled": false
  }'
```

### Configure via Settings File

Edit `~/.config/pumaguard/pumaguard-settings.yaml`:

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 48 # Remove after 48 hours
```

Then restart the PumaGuard server for changes to take effect.

### Monitor Removal Events

The server logs all auto-removal events:

```bash
# Watch server logs for removal events
journalctl -u pumaguard -f | grep "Auto-removed camera"
```

Example log output:

```
INFO: Camera 'Microseven-Cam1' (aa:bb:cc:dd:ee:01) not seen for 25.3 hours, scheduling for auto-removal
INFO: Auto-removed camera 'Microseven-Cam1' (aa:bb:cc:dd:ee:01) at 192.168.52.101
```

## Use Cases

### Scenario 1: Temporary Test Cameras

**Problem**: Test cameras added during development clutter the production device list.

**Solution**: Enable auto-removal with a short timeout (e.g., 1-2 hours):

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 2
```

Test cameras will be automatically removed 2 hours after they go offline.

### Scenario 2: Seasonal Camera Deployment

**Problem**: Wildlife cameras are deployed seasonally but remain in the system when removed.

**Solution**: Enable auto-removal with a longer timeout (e.g., 7 days):

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 168 # 7 days = 7 * 24 hours
```

Cameras removed from the field will be automatically cleaned up after a week.

### Scenario 3: Permanent Camera Installation

**Problem**: Cameras are permanently installed and should never be auto-removed.

**Solution**: Keep auto-removal disabled (default):

```yaml
camera-auto-remove-enabled: false
```

Cameras will remain in the list indefinitely, even if offline.

### Scenario 4: Mixed Environment

**Problem**: Some cameras are permanent, others are temporary.

**Solution**: Use a moderate timeout (e.g., 30 days) and manually manage permanent cameras:

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 720 # 30 days
```

Temporary cameras are cleaned up automatically, while permanent cameras remain due to regular heartbeat checks.

## Configuration Examples

### Conservative (Long Timeout)

Suitable for permanent installations with occasional outages:

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 720 # 30 days
camera-heartbeat-enabled: true
camera-heartbeat-interval: 300 # Check every 5 minutes
```

### Moderate (Default-ish)

Balanced approach for typical deployments:

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 168 # 7 days
camera-heartbeat-enabled: true
camera-heartbeat-interval: 60 # Check every minute
```

### Aggressive (Short Timeout)

Suitable for development/testing environments:

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 1 # 1 hour
camera-heartbeat-enabled: true
camera-heartbeat-interval: 30 # Check every 30 seconds
```

### Disabled (No Auto-Removal)

Preserves all cameras indefinitely:

```yaml
camera-auto-remove-enabled: false
camera-heartbeat-enabled: true # Still monitor status
camera-heartbeat-interval: 60
```

## Integration with Heartbeat Monitoring

Auto-removal **requires** camera heartbeat monitoring to be enabled. The heartbeat monitor:

1. Updates camera status (connected/disconnected)
2. Updates `last_seen` timestamp when cameras are reachable
3. Runs auto-removal check during each monitoring cycle

**Important**: If heartbeat monitoring is disabled, auto-removal will not function.

### Recommended Configuration

```yaml
# Enable heartbeat monitoring (required for auto-removal)
camera-heartbeat-enabled: true
camera-heartbeat-interval: 60 # seconds
camera-heartbeat-method: "tcp" # or "icmp" or "both"

# Enable auto-removal
camera-auto-remove-enabled: true
camera-auto-remove-hours: 24 # hours
```

## Troubleshooting

### Cameras Not Being Removed

**Problem**: Cameras remain in the list despite being inactive for longer than configured timeout.

**Possible Causes**:

1. Auto-removal is disabled
2. Heartbeat monitoring is disabled
3. Camera has no `last_seen` timestamp
4. Camera `last_seen` is being updated (camera is reachable)

**Solutions**:

```bash
# Check configuration
cat ~/.config/pumaguard/pumaguard-settings.yaml | grep -A 2 "camera-auto-remove"

# Verify auto-removal is enabled
grep "camera-auto-remove-enabled: true" ~/.config/pumaguard/pumaguard-settings.yaml

# Verify heartbeat is enabled
grep "camera-heartbeat-enabled: true" ~/.config/pumaguard/pumaguard-settings.yaml

# Check camera last_seen timestamp
curl http://localhost:5000/api/dhcp/cameras | jq '.cameras[] | {hostname, last_seen}'

# Check server logs
journalctl -u pumaguard -n 100 | grep -i "auto-remove"
```

### Cameras Removed Too Quickly

**Problem**: Cameras are being removed sooner than expected.

**Solution**: Increase the `camera-auto-remove-hours` setting:

```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "camera-auto-remove-hours": 168
  }'
```

### Cameras Removed During Network Outage

**Problem**: Cameras are removed during temporary network outages.

**Solutions**:

1. Increase timeout to account for expected outages:

   ```yaml
   camera-auto-remove-hours: 72 # 3 days
   ```

2. Disable auto-removal if outages are frequent:

   ```yaml
   camera-auto-remove-enabled: false
   ```

3. Improve network reliability to reduce heartbeat check failures

### Camera Re-appears After Removal

**Problem**: Camera is auto-removed but immediately re-appears.

**Cause**: Camera is still connected to network and responds to DHCP/heartbeat checks.

**Solution**: This is expected behavior. The camera will be re-detected via:

- DHCP lease events (if connected to PumaGuard hotspot)
- Manual addition via API

To permanently remove a camera, disconnect it from the network or use manual removal.

## API Reference

### Camera Removal Event (SSE)

When a camera is auto-removed, an SSE event is broadcast to all connected clients:

**Event Type**: `camera_removed`

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
