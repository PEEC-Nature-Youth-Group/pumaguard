# Camera Auto-Removal - Quick Start Guide

## What is Camera Auto-Removal?

Automatically removes cameras from your device list after they've been inactive (offline) for a configurable number of hours.

**Status**: ✅ Implemented and tested  
**Default**: ❌ Disabled (must be explicitly enabled)

## Quick Enable

### Method 1: Via API (Recommended)

```bash
# Enable with 24-hour timeout
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "camera-auto-remove-enabled": true,
    "camera-auto-remove-hours": 24
  }'
```

### Method 2: Via Settings File

Edit `~/.config/pumaguard/pumaguard-settings.yaml`:

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 24
```

Then restart the PumaGuard server.

## Common Configurations

### Development/Testing (Aggressive)

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 1 # Remove after 1 hour
```

### Production (Moderate)

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 168 # Remove after 7 days
```

### Long-term Deployment (Conservative)

```yaml
camera-auto-remove-enabled: true
camera-auto-remove-hours: 720 # Remove after 30 days
```

### Permanent Installation (Disabled)

```yaml
camera-auto-remove-enabled: false # Never auto-remove
```

## How to Check If It's Working

### 1. Verify Configuration

```bash
# Check settings
cat ~/.config/pumaguard/pumaguard-settings.yaml | grep camera-auto-remove
```

Expected output:

```
camera-auto-remove-enabled: true
camera-auto-remove-hours: 24
```

### 2. Monitor Server Logs

```bash
# Watch for auto-removal events
journalctl -u pumaguard -f | grep -i "auto-remove"
```

You'll see messages like:

```
INFO: Camera 'Microseven-Cam1' (aa:bb:cc:dd:ee:01) not seen for 25.3 hours, scheduling for auto-removal
INFO: Auto-removed camera 'Microseven-Cam1' (aa:bb:cc:dd:ee:01) at 192.168.52.101
```

### 3. Check Camera List

```bash
# List all cameras with last_seen timestamps
curl -s http://localhost:5000/api/dhcp/cameras | \
  jq '.cameras[] | {hostname, last_seen, status}'
```

## Requirements

⚠️ **Camera heartbeat monitoring must be enabled** for auto-removal to work.

Minimal required configuration:

```yaml
# Required: Enable heartbeat monitoring
camera-heartbeat-enabled: true
camera-heartbeat-interval: 60 # Check every 60 seconds

# Enable auto-removal
camera-auto-remove-enabled: true
camera-auto-remove-hours: 24
```

## Troubleshooting

### Cameras Not Being Removed?

**Check 1**: Is auto-removal enabled?

```bash
grep "camera-auto-remove-enabled: true" ~/.config/pumaguard/pumaguard-settings.yaml
```

**Check 2**: Is heartbeat monitoring enabled?

```bash
grep "camera-heartbeat-enabled: true" ~/.config/pumaguard/pumaguard-settings.yaml
```

**Check 3**: Are cameras actually offline long enough?

```bash
curl -s http://localhost:5000/api/dhcp/cameras | jq '.cameras[] | {hostname, last_seen}'
```

### Cameras Removed Too Fast?

Increase the timeout:

```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"camera-auto-remove-hours": 168}'  # 7 days
```

### Want to Disable Auto-Removal?

```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"camera-auto-remove-enabled": false}'
```

## Important Notes

✅ **Safe**: Disabled by default - won't remove cameras unless explicitly enabled  
✅ **Reversible**: Cameras can reconnect and be re-detected via DHCP  
✅ **Non-destructive**: Only removes camera metadata, not image files  
✅ **Logged**: All removals are logged with full camera details  
✅ **Notified**: UI clients receive real-time removal notifications via SSE

❌ **Does NOT delete**: Classification images, detection results, or other data  
❌ **Does NOT prevent**: Cameras from reconnecting and being re-added

## Example Use Cases

### 1. Clean Up Test Cameras

Enable with 2-hour timeout during development:

```yaml
camera-auto-remove-hours: 2
```

### 2. Seasonal Wildlife Monitoring

Enable with 30-day timeout for cameras deployed seasonally:

```yaml
camera-auto-remove-hours: 720
```

### 3. Temporary Event Coverage

Enable with 24-hour timeout for short-term monitoring:

```yaml
camera-auto-remove-hours: 24
```

## Testing the Feature

### Manual Test

1. Add a fake camera with old timestamp
2. Enable auto-removal with short timeout
3. Wait for heartbeat cycle
4. Verify camera is removed

```bash
# Add test camera (last seen 48 hours ago)
curl -X POST http://localhost:5000/api/dhcp/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "TestCam",
    "ip_address": "192.168.52.99",
    "mac_address": "aa:bb:cc:dd:ee:99",
    "last_seen": "2024-01-14T00:00:00Z"
  }'

# Enable auto-removal with 24-hour timeout
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "camera-auto-remove-enabled": true,
    "camera-auto-remove-hours": 24
  }'

# Wait 60 seconds (for heartbeat cycle)
sleep 60

# Check if camera was removed
curl -s http://localhost:5000/api/dhcp/cameras | jq '.cameras'
```

## Related Documentation

- [Camera Auto-Removal (Full Documentation)](../docs/CAMERA_AUTO_REMOVAL.md)
- [Camera Heartbeat Monitoring](../docs/CAMERA_HEARTBEAT.md)
- [Device Removal Feature](../docs/DEVICE_REMOVAL.md)
- [API Reference](../docs/API_REFERENCE.md)

## Quick Reference Table

| Setting                      | Purpose                | Default | Recommended Range   |
| ---------------------------- | ---------------------- | ------- | ------------------- |
| `camera-auto-remove-enabled` | Enable/disable feature | `false` | `true` or `false`   |
| `camera-auto-remove-hours`   | Inactivity timeout     | `24`    | `1` to `720+` hours |

## Summary

Camera auto-removal is a **maintenance feature** that keeps your device list clean by automatically removing cameras that have been offline for too long. It's:

- 🔒 **Safe by default** (disabled)
- ⚙️ **Highly configurable** (1 hour to months)
- 🔄 **Fully reversible** (cameras can reconnect)
- 📊 **Well-monitored** (logs + SSE events)

Enable it when you want automated cleanup, leave it disabled when you want complete manual control.
