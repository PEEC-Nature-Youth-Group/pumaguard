# Automatic Plug Control During Puma Detection

## Overview

When the PumaGuard server detects a puma in an image (prediction > 0.5), it now automatically controls Shelly smart plugs that are configured in "automatic" mode. This feature allows lights, sirens, or other deterrents connected to smart plugs to activate automatically during puma detection.

## How It Works

### Detection Flow

1. **Image Classification**: When a new image is detected and classified with >50% puma probability
2. **Plug Activation**: All plugs in "automatic" mode are turned ON
3. **Sound Playback**: Deterrent sound plays (if enabled)
4. **Plug Deactivation**: All automatic plugs are turned OFF after sound finishes

### Key Characteristics

- **Automatic Mode Only**: Only plugs set to `mode: "automatic"` are controlled
- **Connected Plugs Only**: Disconnected plugs are skipped (status must be "connected")
- **Blocking Operation**: Plugs remain ON during the entire sound playback duration
- **No Effect on Manual Plugs**: Plugs set to "on" or "off" mode are not affected

## Implementation Details

### Code Location

The automatic plug control is implemented in `pumaguard/server.py`:

- `FolderObserver._handle_new_file()` - Main detection handler (line ~278-295)
- `FolderObserver._turn_on_automatic_plugs()` - Activates automatic plugs (line ~316-333)
- `FolderObserver._turn_off_automatic_plugs()` - Deactivates automatic plugs (line ~335-352)
- `FolderObserver._control_plug_switch()` - Low-level Shelly API control (line ~354-404)

### Plug Selection Logic

```python
automatic_plugs = [
    plug
    for plug in self.webui.plugs.values()
    if plug.get("mode") == "automatic"
    and plug.get("status") == "connected"
]
```

Plugs must meet both criteria:
1. `mode == "automatic"` (not "on" or "off")
2. `status == "connected"` (currently reachable)

### Shelly API Communication

Uses the Shelly Gen2 HTTP REST API:

```
GET http://{ip_address}/rpc/Switch.Set?id=0&on={true|false}
```

- **Timeout**: 5 seconds per plug
- **Error Handling**: Logs errors but continues with remaining plugs
- **Non-blocking**: Uses `requests.get()` with timeout

## Configuration

### Setting Plug Mode

Plugs can be configured via the Web UI or REST API:

**Web UI**: Navigate to DHCP → Plugs → Select plug → Set mode to "Automatic"

**REST API**:
```bash
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "automatic"}'
```

### Available Modes

- **`automatic`**: Controlled during puma detection
- **`on`**: Manually kept on (not controlled by detection)
- **`off`**: Manually kept off (not controlled by detection)

## Example Scenarios

### Scenario 1: Automatic Light Activation

**Setup**:
- 2 outdoor lights connected to Shelly plugs
- Both plugs set to "automatic" mode
- Deterrent sound configured and enabled

**Behavior**:
1. Puma detected in camera trap image
2. Both lights turn ON simultaneously
3. Deterrent sound plays (e.g., 30 seconds)
4. Both lights turn OFF after sound finishes

### Scenario 2: Mixed Manual and Automatic Plugs

**Setup**:
- Plug 1: `mode: "automatic"` - Motion-activated spotlight
- Plug 2: `mode: "on"` - Always-on security light
- Plug 3: `mode: "automatic"` - Siren

**Behavior**:
1. Puma detected
2. Plug 1 (spotlight) turns ON
3. Plug 2 (security light) unchanged (already on, not controlled)
4. Plug 3 (siren) turns ON
5. Sound plays
6. Plug 1 and 3 turn OFF
7. Plug 2 remains ON

### Scenario 3: Disconnected Automatic Plug

**Setup**:
- Plug 1: `mode: "automatic"`, `status: "connected"`
- Plug 2: `mode: "automatic"`, `status: "disconnected"`

**Behavior**:
1. Puma detected
2. Only Plug 1 is controlled (Plug 2 is skipped)
3. Sound plays
4. Plug 1 turns OFF

## Testing

### Unit Tests

Comprehensive tests are in `tests/test_server.py`:

```bash
# Test automatic plug control
uv run pytest tests/test_server.py::TestFolderObserver::test_handle_new_file_automatic_plugs_on_off -xvs

# Test no control when no puma detected
uv run pytest tests/test_server.py::TestFolderObserver::test_handle_new_file_no_puma_no_plug_control -xvs

# Test disconnected plugs are not controlled
uv run pytest tests/test_server.py::TestFolderObserver::test_handle_new_file_disconnected_plugs_not_controlled -xvs
```

### Manual Testing

1. Add test plugs via API:
```bash
curl -X POST http://localhost:5000/api/dhcp/plugs \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "test-plug",
    "ip_address": "192.168.52.100",
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "status": "connected"
  }'
```

2. Set plug to automatic mode:
```bash
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "automatic"}'
```

3. Place puma image in watched folder
4. Observe plug turning on/off with sound playback

## Logging

The feature provides detailed logging:

```
INFO: Puma detected in /path/to/image.jpg
DEBUG: Turning on 2 automatic plug(s)
INFO: Setting plug 'outdoor-light-1' switch to ON at 192.168.52.101
INFO: Successfully set plug 'outdoor-light-1' switch to ON
INFO: Setting plug 'outdoor-light-2' switch to ON at 192.168.52.102
INFO: Successfully set plug 'outdoor-light-2' switch to ON
INFO: Playing sound: deterrent-sound.mp3
INFO: Turning off 2 automatic plug(s)
INFO: Setting plug 'outdoor-light-1' switch to OFF at 192.168.52.101
INFO: Successfully set plug 'outdoor-light-1' switch to OFF
INFO: Setting plug 'outdoor-light-2' switch to OFF at 192.168.52.102
INFO: Successfully set plug 'outdoor-light-2' switch to OFF
```

### Error Logging

```
WARNING: Timeout connecting to plug 'outdoor-light-1' at 192.168.52.101
ERROR: Error setting plug 'outdoor-light-2' switch at 192.168.52.102: Connection refused
```

## Troubleshooting

### Plugs Not Activating

1. **Check plug mode**: Ensure mode is set to "automatic"
   ```bash
   curl http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/mode
   ```

2. **Check plug status**: Ensure status is "connected"
   ```bash
   curl http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff
   ```

3. **Check network connectivity**: Ping the plug's IP address
   ```bash
   ping 192.168.52.100
   ```

4. **Check Shelly API**: Manually test the Shelly endpoint
   ```bash
   curl "http://192.168.52.100/rpc/Switch.Set?id=0&on=true"
   ```

### Plug Stays On After Detection

- Check server logs for OFF command errors
- Verify sound playback completes (not interrupted)
- Manually turn off via API if needed:
  ```bash
  curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch \
    -H "Content-Type: application/json" \
    -d '{"on": false}'
  ```

### Partial Plug Control

If some plugs activate but others don't:
- Check individual plug status and connectivity
- Review logs for timeout or connection errors
- Each plug is controlled independently; one failure doesn't affect others

## Security Considerations

- **Network Access**: Server must have network access to plug IP addresses
- **No Authentication**: Shelly Gen2 local API has no authentication by default
- **Timeout Protection**: 5-second timeout prevents hanging on unreachable plugs
- **Error Isolation**: Plug control errors don't interrupt puma detection or classification

## Future Enhancements

Potential improvements for consideration:

1. **Configurable Duration**: Allow plugs to stay on for custom duration (not tied to sound)
2. **Activation Patterns**: Support blinking or pulsing patterns
3. **Conditional Activation**: Enable/disable based on time of day
4. **Group Control**: Define plug groups with different behaviors
5. **Delayed Deactivation**: Keep lights on for period after sound finishes
6. **Retry Logic**: Attempt to control failed plugs multiple times
7. **State Persistence**: Remember plug state before activation and restore it

## Related Documentation

- [Shelly Plug Switch Control API](docs/SHELLY_PLUG_SWITCH_API.md)
- [API Reference - DHCP Plug Management](docs/API_REFERENCE.md#dhcp-plug-management)
- [Plug Heartbeat Monitoring](docs/PLUG_HEARTBEAT.md)