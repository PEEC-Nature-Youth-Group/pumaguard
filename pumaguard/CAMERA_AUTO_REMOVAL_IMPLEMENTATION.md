# Camera Auto-Removal Feature - Implementation Summary

## Overview

This document summarizes the implementation of the camera auto-removal feature, which automatically removes inactive cameras from the device list after a configurable number of hours.

**Status**: ✅ **IMPLEMENTED AND TESTED**  
**PR/Commit**: [To be filled in]  
**Implementation Date**: 2024-01-16

## What Was Implemented

### Core Functionality

1. **Automatic Removal Logic** (`pumaguard/camera_heartbeat.py`)
   - New method `_check_and_remove_stale_cameras()` checks camera timestamps
   - Integrated into heartbeat monitoring loop
   - Removes cameras whose `last_seen` exceeds configured hours
   - Sends SSE notifications for removed cameras
   - Comprehensive error handling for edge cases

2. **Configuration Settings** (`pumaguard/presets.py`)
   - `camera_auto_remove_enabled` (bool, default: `false`)
   - `camera_auto_remove_hours` (int, default: `24`)
   - Settings load/save support
   - Serialization in `__iter__` method

3. **API Integration** (`pumaguard/web_routes/settings.py`)
   - Added auto-removal settings to `allowed_settings` list
   - Enables runtime configuration via REST API

4. **WebUI Integration** (`pumaguard/web_ui.py`)
   - Passes auto-removal settings to `CameraHeartbeat` constructor
   - Settings loaded from presets on startup

### Testing

Comprehensive test suite added to `tests/test_camera_heartbeat.py`:

- ✅ Initialization with auto-removal settings
- ✅ Removal of cameras exceeding timeout
- ✅ Preservation of recent cameras
- ✅ Disabled auto-removal behavior
- ✅ Handling missing `last_seen` timestamps
- ✅ Handling invalid timestamps
- ✅ Multiple camera removal
- ✅ Callback error handling
- ✅ Integration with monitor loop

**Test Results**: 40 tests pass (including 10 new auto-removal tests)

### Documentation

Three comprehensive documentation files created:

1. **`docs/CAMERA_AUTO_REMOVAL.md`** (438 lines)
   - Complete feature documentation
   - Configuration examples
   - Troubleshooting guide
   - API reference
   - Use cases and scenarios

2. **`docs/CAMERA_HEARTBEAT.md`** (updated)
   - Added auto-removal section
   - Updated settings table
   - Integration notes

3. **`CAMERA_AUTO_REMOVAL_QUICKSTART.md`** (233 lines)
   - Quick start guide
   - Common configurations
   - Troubleshooting steps
   - Testing instructions

## Files Modified

### Core Implementation

- `pumaguard/camera_heartbeat.py` - Added auto-removal logic (+87 lines)
- `pumaguard/presets.py` - Added settings support (+36 lines)
- `pumaguard/web_ui.py` - Pass settings to heartbeat (+2 lines)
- `pumaguard/web_routes/settings.py` - Added to allowed settings (+8 lines)

### Tests

- `tests/test_camera_heartbeat.py` - Added comprehensive tests (+246 lines)

### Documentation

- `docs/CAMERA_AUTO_REMOVAL.md` - New comprehensive guide (438 lines)
- `docs/CAMERA_HEARTBEAT.md` - Updated with auto-removal section (+24 lines)
- `CAMERA_AUTO_REMOVAL_QUICKSTART.md` - New quick start guide (233 lines)
- `CAMERA_AUTO_REMOVAL_IMPLEMENTATION.md` - This file

## Technical Details

### Architecture

The auto-removal feature is integrated into the existing camera heartbeat monitoring system:

```
CameraHeartbeat Thread
  ↓
  Monitor Loop (every N seconds)
    ↓
    1. Check each camera status (ICMP/TCP)
    2. Update camera status & last_seen
    3. Call _check_and_remove_stale_cameras()
       ↓
       - Calculate: now - last_seen
       - If > configured hours → Remove camera
       - Log removal
       - Send SSE notification
       - Persist to settings
```

### Key Implementation Details

1. **Timestamp Parsing**
   - Uses `datetime.fromisoformat()` for ISO8601 timestamps
   - Handles both "Z" and "+00:00" timezone formats
   - Gracefully handles invalid timestamps (logs warning, skips removal)

2. **Safety Features**
   - Disabled by default (`camera_auto_remove_enabled: false`)
   - Cameras without `last_seen` are never removed
   - Invalid timestamps don't cause removal
   - Removal happens outside iteration loop (safe dict modification)

3. **Error Handling**
   - Broad exception catching to prevent thread crashes
   - Callback errors don't prevent removal
   - Persistence errors are logged but don't stop monitoring

4. **SSE Notifications**
   - Uses existing `status_change_callback` mechanism
   - Event type: `"camera_removed"`
   - Includes full camera data in notification

### Configuration Flow

```
Settings File (YAML)
  ↓
Settings.load() - Reads camera-auto-remove-* settings
  ↓
WebUI.__init__() - Creates CameraHeartbeat with settings
  ↓
CameraHeartbeat.__init__() - Stores auto_remove_enabled/hours
  ↓
_monitor_loop() - Calls _check_and_remove_stale_cameras()
  ↓
_check_and_remove_stale_cameras() - Enforces removal policy
```

### Settings API Integration

The feature can be configured via REST API:

```bash
POST /api/settings
{
  "camera-auto-remove-enabled": true,
  "camera-auto-remove-hours": 24
}
```

Settings are validated, saved to disk, and take effect on next heartbeat cycle.

## Testing Coverage

### Unit Tests (10 new tests)

1. `test_auto_removal_initialization` - Verifies settings initialization
2. `test_auto_removal_disabled_by_default` - Confirms safe defaults
3. `test_check_and_remove_stale_cameras_removes_old_camera` - Basic removal
4. `test_check_and_remove_stale_cameras_keeps_recent_camera` - No premature removal
5. `test_check_and_remove_stale_cameras_disabled` - Respects disabled flag
6. `test_check_and_remove_stale_cameras_handles_missing_last_seen` - Edge case
7. `test_check_and_remove_stale_cameras_handles_invalid_timestamp` - Error handling
8. `test_check_and_remove_stale_cameras_removes_multiple` - Batch removal
9. `test_check_and_remove_stale_cameras_handles_callback_exception` - Robustness
10. `test_monitor_loop_calls_auto_removal` - Integration test

### Test Execution

```bash
# All camera heartbeat tests (40 total)
uv run pytest tests/test_camera_heartbeat.py -v

# Auto-removal tests only (10 tests)
uv run pytest tests/test_camera_heartbeat.py -k "auto_removal or stale" -v
```

**Result**: ✅ 40/40 tests pass (100% success rate)

### Code Quality

- ✅ Black formatting: All files pass
- ✅ Pylint: 10.00/10 rating
- ✅ Type hints: Comprehensive type annotations
- ✅ Documentation: Docstrings for all new methods
- ✅ Error handling: Comprehensive exception handling

## Usage Examples

### Enable with 24-hour timeout

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 24
```

### Enable via API

```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "camera-auto-remove-enabled": true,
    "camera-auto-remove-hours": 24
  }'
```

### Monitor removal events

```bash
journalctl -u pumaguard -f | grep "Auto-removed camera"
```

## Performance Impact

- **CPU**: Negligible - simple timestamp arithmetic during heartbeat cycle
- **Memory**: ~100 bytes (2 configuration values)
- **Network**: Zero - no additional network calls
- **Disk I/O**: Minimal - settings update on removal (same as manual removal)
- **Threading**: Zero - runs in existing heartbeat thread

## Security Considerations

- ✅ No sensitive data in settings
- ✅ No external network access
- ✅ No credential handling
- ✅ Path traversal not applicable (no file operations)
- ✅ Settings validated before use
- ✅ XDG-compliant file locations

## Backwards Compatibility

- ✅ **100% backwards compatible**
- ✅ Feature disabled by default (no behavior change)
- ✅ Existing settings files work unchanged
- ✅ No database migrations required
- ✅ Cameras without `last_seen` are ignored (not removed)
- ✅ API additions only (no breaking changes)

## Known Limitations

1. **Global timeout only**: All cameras use the same timeout (no per-camera settings)
2. **Requires heartbeat**: Auto-removal requires heartbeat monitoring to be enabled
3. **Time-based only**: Removal based solely on `last_seen` timestamp
4. **No grace period**: Clock immediately starts from first detection
5. **No undo**: Removed cameras must reconnect to be re-added

These limitations are documented and may be addressed in future versions.

## Future Enhancements

Potential improvements for consideration:

- [ ] Per-camera auto-removal timeout
- [ ] Grace period after first detection
- [ ] Removal history/audit log
- [ ] Restore/undo removed cameras
- [ ] Notification webhooks
- [ ] Auto-removal statistics dashboard
- [ ] Whitelist/blacklist by MAC address
- [ ] Integration with alert system
- [ ] Configurable removal criteria (beyond time)

## Migration Guide

### For Existing Installations

No migration required. The feature is disabled by default.

**To enable:**

1. Update settings file or use API
2. Restart server (if using file method)
3. Monitor logs for first removal event

### For New Installations

Default behavior: Auto-removal disabled. Users must opt-in.

## Rollback Procedure

If issues arise, disable the feature:

**Method 1: Settings file**

```yaml
camera-auto-remove-enabled: false
```

**Method 2: API**

```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"camera-auto-remove-enabled": false}'
```

No code changes or reinstallation required.

## Related Issues

This implementation addresses the user question:

> "Inactive plugs or cameras should be automatically removed from the list of devices. How long does this take? Is this behavior tied into dnsmasq?"

**Answer:**

- ✅ Cameras can now be automatically removed (plugs: future work)
- ✅ Timeout is configurable (default: 24 hours)
- ✅ Not tied to dnsmasq - uses heartbeat monitoring system
- ✅ DHCP events update `last_seen` but don't trigger removal
- ✅ Removal happens during heartbeat checks (default: every 60 seconds)

## Verification Steps

To verify the implementation:

1. **Check settings exist:**

   ```bash
   grep -E "camera-auto-remove" ~/.config/pumaguard/pumaguard-settings.yaml
   ```

2. **Run tests:**

   ```bash
   uv run pytest tests/test_camera_heartbeat.py -v
   ```

3. **Test manually:**
   - Enable auto-removal with 1-hour timeout
   - Add test camera with old timestamp
   - Wait 60 seconds for heartbeat cycle
   - Verify camera removed from list

4. **Check logs:**
   ```bash
   journalctl -u pumaguard | grep -i "auto-remove"
   ```

## Summary

The camera auto-removal feature is **fully implemented, tested, and documented**. It provides:

- ✅ Automatic cleanup of inactive cameras
- ✅ Configurable timeout (hours)
- ✅ Safe by default (disabled)
- ✅ Full logging and notifications
- ✅ Comprehensive test coverage
- ✅ Extensive documentation
- ✅ Zero breaking changes

The feature integrates seamlessly with existing heartbeat monitoring and requires no database changes or migrations. It's production-ready and can be enabled immediately for deployments requiring automated camera list maintenance.

## References

- [Full Documentation](docs/CAMERA_AUTO_REMOVAL.md)
- [Quick Start Guide](CAMERA_AUTO_REMOVAL_QUICKSTART.md)
- [Camera Heartbeat Docs](docs/CAMERA_HEARTBEAT.md)
- [Test Suite](tests/test_camera_heartbeat.py)
- [Implementation Code](pumaguard/camera_heartbeat.py)
