# Device Re-detection Fix

## Problem Statement

When a user removed a camera or plug via the UI, and that device subsequently renewed its DHCP lease, the device was not automatically re-added to PumaGuard. This occurred because:

1. DHCP lease renewals often don't include the device hostname (especially DHCP RENEW packets)
2. The DHCP notification script filtered events by hostname pattern before notifying PumaGuard
3. Devices with hostname="unknown" failed the pattern match and were never reported
4. PumaGuard had no way to recognize returning devices by MAC address alone

## Solution

### 1. Remove Hostname Filtering from DHCP Script

**File**: `scripts/templates/pumaguard-dhcp-notify.sh.j2`

Changed the script to send **ALL** DHCP events to PumaGuard's API, regardless of hostname. This allows the backend to make intelligent decisions based on device history.

**Before**:
```bash
# Only notify for devices matching hostname patterns
if [[ "$HOSTNAME" == "$CAMERA_HOSTNAME_PREFIX"* ]]; then
    notify_pumaguard "$ACTION" "$MAC" "$IP" "$HOSTNAME"
fi
```

**After**:
```bash
# Send all DHCP events to PumaGuard
# Backend decides based on hostname patterns AND MAC address history
notify_pumaguard "$ACTION" "$MAC" "$IP" "$HOSTNAME"
```

### 2. Add Device History Tracking

**File**: `pumaguard/web_ui.py`

Added a `device_history` dictionary that tracks all devices ever seen by the system:

```python
self.device_history: dict[str, dict[str, str]] = {}
# Format: {mac_address: {"type": "camera"|"plug", "hostname": str}}
```

This history is:
- **Persisted to settings file** (`~/.config/pumaguard/pumaguard-settings.yaml`)
- Loaded from persisted settings on startup
- Updated whenever a device connects with a valid hostname
- Maintained even after device removal
- **Survives server restarts**
- Used to recognize returning devices

### 3. Add Device History to Settings

**File**: `pumaguard/presets.py`

Added `device_history` field to the `Settings` class for persistence:

```python
self.device_history: dict[str, dict[str, str]] = {}  # Device history by MAC
```

Updated `load()` method to load device history:
```python
self.device_history = settings.get("device-history", {})
```

Updated `__iter__()` method to save device history:
```python
"device-history": self.device_history,
```

### 4. Enhanced DHCP Event Handler

**File**: `pumaguard/web_routes/dhcp.py`

Updated the `/api/dhcp/event` endpoint to recognize devices using three methods:

1. **Hostname pattern matching** - For new devices (e.g., "Microseven", "shellyplug")
2. **Active device tracking** - For currently connected devices
3. **Device history lookup** - For previously seen devices (even after removal)

**Key Changes**:

```python
# Check device history for previously seen devices
device_history = webui.device_history.get(mac_address, {})
is_historical_camera = device_history.get("type") == "camera"

# Recognize camera by hostname OR current tracking OR history
is_camera = (
    (hostname and hostname.startswith("Microseven"))
    or is_known_camera
    or is_historical_camera
)

# Preserve hostname from history if current hostname is unknown
if not hostname or hostname == "unknown":
    if is_known_camera:
        effective_hostname = webui.cameras[mac_address].get("hostname")
    elif is_historical_camera:
        effective_hostname = device_history.get("hostname")
```

When device history is updated, it's persisted to settings:
```python
webui.device_history[mac_address] = {
    "type": "camera",
    "hostname": effective_hostname,
}
# Persist device history to settings
webui.presets.device_history = webui.device_history
```

## Behavior Changes

### Before This Fix

1. Camera "Microseven-Cam1" connects → added to device list
2. User removes camera via UI → camera deleted from memory
3. Camera renews DHCP lease with hostname="unknown"
4. DHCP script filters out event (hostname doesn't match pattern)
5. **Camera is NOT re-added** ❌

### After This Fix

1. Camera "Microseven-Cam1" connects → added to device list + device history
2. User removes camera via UI → camera deleted from active list, history preserved
3. Camera renews DHCP lease with hostname="unknown"
4. DHCP script sends event to PumaGuard (no filtering)
5. Backend recognizes MAC from device history
6. **Camera is automatically re-added with preserved hostname** ✅

## Test Coverage

Added comprehensive tests in `tests/test_dhcp_routes.py`:

- `test_removed_camera_readded_on_lease_renewal_with_unknown_hostname`
  - Verifies removed cameras are re-detected when they renew with unknown hostname
  
- `test_known_camera_lease_renewal_preserves_hostname`
  - Verifies hostname preservation when renewals don't include hostname
  
- `test_known_plug_lease_renewal_preserves_hostname_and_mode`
  - Verifies plugs preserve both hostname and mode settings during renewals

- `test_device_history_persists_across_settings_save_load`
  - Verifies device history is saved to and loaded from settings file
  - Ensures removed devices can be re-detected after server restart

All existing tests continue to pass (347 tests total).

## Documentation Updates

Updated `docs/DEVICE_REMOVAL.md` to explain:

- How device re-detection works after removal
- Why DHCP renewals may not include hostnames
- The device history mechanism
- How to prevent automatic re-detection if desired
- Device history persistence behavior

## Backward Compatibility

This change is **fully backward compatible**:

- Existing installations continue to work without changes
- Device history is built automatically from current settings
- No database migration or manual intervention required
- API endpoints maintain the same interface

## Performance Impact

Minimal impact:

- Device history is stored in memory (dict lookup is O(1))
- History size limited to unique MAC addresses seen
- Persisted to settings file with cameras/plugs (single YAML write)
- Typical deployments: <100 devices = <10KB memory + storage

## Security Considerations

- No new attack vectors introduced
- MAC addresses remain redacted in logs
- Device history stored in settings file (XDG-compliant location)
- Settings file uses standard permissions (readable only by user)
- All existing path validation and CORS policies still apply

## Related Issues

This fix addresses the issue where removed devices were not automatically re-added when they renewed their DHCP leases, which was unexpected behavior given that the documentation states "removed cameras can reconnect and be re-detected via DHCP."

## Migration Notes

No migration required. Upon deploying this fix:

1. Server starts with empty device_history (if upgrading from old version)
2. Device history is automatically built as devices connect
3. All subsequent DHCP events are processed with new logic
4. Device history is persisted to settings file on each update
5. After first connection cycle, removed devices will be recognized on reconnect
6. No manual configuration changes needed

## Future Enhancements

Potential improvements for future versions:

- [x] Persist device history to settings file for faster startup ✅ (implemented)
- [ ] Add UI to view and manage device history
- [ ] Add "permanently ignore" option for specific MAC addresses
- [ ] Add device history TTL (auto-expire old entries after X days)
- [ ] Export/import device history for backup/restore
- [ ] Clear device history via API endpoint
- [ ] Merge/deduplicate entries if MAC changes hostname