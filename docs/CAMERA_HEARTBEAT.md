# Camera Heartbeat Monitoring

PumaGuard includes a background heartbeat monitor that continuously checks camera availability to provide real-time status updates beyond DHCP lease events.

## Overview

The camera heartbeat monitor runs as a background thread and periodically checks if cameras are reachable using either ICMP ping, TCP connection tests, or both. This provides more accurate camera status tracking than relying solely on DHCP lease events.

### Why Heartbeat Monitoring?

DHCP lease events only update camera status when:
- A camera requests a new IP (lease creation)
- A camera renews its lease (typically every ~6 hours for a 12-hour lease)
- A lease expires (camera goes offline)

Between these events, a camera could become unreachable without the server knowing. Heartbeat monitoring fills this gap by actively checking camera availability at regular intervals.

## Features

- **Multiple check methods**: ICMP ping, TCP connection, or both
- **Configurable intervals**: Set how often cameras are checked
- **Automatic status updates**: Camera status and `last_seen` timestamp are automatically updated
- **Non-blocking**: Runs in a background thread without affecting server performance
- **Manual checks**: API endpoint to force immediate check of all cameras
- **Persistent settings**: All heartbeat configuration is saved to settings file

## Configuration

All heartbeat settings are stored in `~/.config/pumaguard/pumaguard-settings.yaml` and can be configured via the settings API or by editing the file directly.

### Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `camera_heartbeat_enabled` | `true` | Enable/disable heartbeat monitoring |
| `camera_heartbeat_interval` | `60` | Check interval in seconds |
| `camera_heartbeat_method` | `"tcp"` | Check method: `"icmp"`, `"tcp"`, or `"both"` |
| `camera_heartbeat_tcp_port` | `80` | TCP port to check (HTTP by default) |
| `camera_heartbeat_tcp_timeout` | `3` | TCP connection timeout in seconds |
| `camera_heartbeat_icmp_timeout` | `2` | ICMP ping timeout in seconds |

### Check Methods

#### TCP (Default)

Attempts to establish a TCP connection to the camera's IP address on the specified port. This is the most reliable method since most cameras have a web interface listening on port 80.

```yaml
camera_heartbeat_method: "tcp"
camera_heartbeat_tcp_port: 80
camera_heartbeat_tcp_timeout: 3
```

**Advantages**:
- Works through most firewalls
- Verifies the camera's web service is responding
- Not blocked by ICMP filtering

**Disadvantages**:
- Slower than ICMP
- Requires knowing which port the camera uses

#### ICMP

Sends an ICMP echo request (ping) to the camera's IP address.

```yaml
camera_heartbeat_method: "icmp"
camera_heartbeat_icmp_timeout: 2
```

**Advantages**:
- Fast (typically < 1 second)
- Low network overhead
- Standard connectivity test

**Disadvantages**:
- May be blocked by firewalls
- Some cameras may not respond to ping
- Requires `ping` command on system

#### Both

Tries ICMP first (fast path), then falls back to TCP if ICMP fails.

```yaml
camera_heartbeat_method: "both"
```

**Advantages**:
- Best of both worlds
- Fast when ICMP works
- Reliable fallback to TCP

**Disadvantages**:
- Slower on ICMP failures
- More complex

## Usage

### Automatic Monitoring

Heartbeat monitoring starts automatically when the WebUI server starts (if enabled):

```bash
pumaguard-webui --host 0.0.0.0
```

The monitor will run in the background, checking cameras at the configured interval.

### Manual Check via API

Force an immediate check of all cameras:

```bash
curl -X POST http://localhost:5000/api/dhcp/cameras/heartbeat
```

Response:

```json
{
  "status": "success",
  "message": "Heartbeat check completed",
  "cameras": {
    "aa:bb:cc:dd:ee:ff": {
      "hostname": "Microseven",
      "ip_address": "192.168.52.100",
      "reachable": true,
      "status": "connected",
      "last_seen": "2024-01-15T14:32:15Z"
    }
  }
}
```

### Viewing Camera Status

Get current status of all cameras:

```bash
curl http://localhost:5000/api/dhcp/cameras
```

The `status` field will show:
- `"connected"` - Camera is currently reachable
- `"disconnected"` - Camera is not reachable

The `last_seen` timestamp shows when the camera was last confirmed reachable (either by heartbeat or DHCP event).

## How It Works

### Status Updates

When a heartbeat check runs:

1. **Camera reachable**: 
   - `status` is set to `"connected"`
   - `last_seen` is updated to current timestamp
   - Changes are persisted to settings

2. **Camera unreachable**:
   - `status` is set to `"disconnected"`
   - `last_seen` is NOT updated (preserves last successful contact time)
   - Changes are persisted to settings

### Integration with DHCP Events

Heartbeat monitoring works alongside DHCP event tracking:

- **DHCP events** (from dnsmasq) update status when leases are created, renewed, or expire
- **Heartbeat checks** provide ongoing status verification between DHCP events
- Both mechanisms update the same camera records, providing comprehensive tracking

### Threading Model

The heartbeat monitor runs in a daemon thread that:
- Starts when `WebUI.start()` is called
- Stops gracefully when `WebUI.stop()` is called
- Sleeps between check intervals to minimize CPU usage
- Handles exceptions without crashing
- Can be interrupted immediately via stop event

## Example Configurations

### Aggressive Monitoring (IP Cameras)

For critical monitoring where you want to know immediately if a camera goes offline:

```yaml
camera_heartbeat_enabled: true
camera_heartbeat_interval: 30  # Check every 30 seconds
camera_heartbeat_method: "both"
camera_heartbeat_tcp_port: 80
```

### Conservative Monitoring (Battery Cameras)

For battery-powered cameras where you want to minimize network traffic:

```yaml
camera_heartbeat_enabled: true
camera_heartbeat_interval: 300  # Check every 5 minutes
camera_heartbeat_method: "tcp"
camera_heartbeat_tcp_port: 80
```

### RTSP Camera Monitoring

For cameras that primarily expose RTSP streams:

```yaml
camera_heartbeat_enabled: true
camera_heartbeat_interval: 60
camera_heartbeat_method: "tcp"
camera_heartbeat_tcp_port: 554  # RTSP port
camera_heartbeat_tcp_timeout: 5
```

### Disabled Monitoring

If you want to rely only on DHCP events:

```yaml
camera_heartbeat_enabled: false
```

## Troubleshooting

### Cameras Always Show as Disconnected

**Problem**: Heartbeat checks always fail even though cameras are online.

**Solutions**:
1. Check if camera has firewall blocking connections
2. Verify correct TCP port (some cameras use 8080, 443, etc.)
3. Try `"both"` method instead of just TCP or ICMP
4. Increase timeout values for slow networks
5. Verify camera IP address is correct

### High CPU Usage

**Problem**: Heartbeat monitoring is using too much CPU.

**Solutions**:
1. Increase `camera_heartbeat_interval` (e.g., 300 seconds)
2. Use `"icmp"` method instead of TCP (faster)
3. Reduce number of monitored cameras
4. Disable heartbeat monitoring if not needed

### Cameras Not Updating Status

**Problem**: Camera status doesn't change even when cameras go offline.

**Solutions**:
1. Verify heartbeat monitoring is enabled
2. Check logs for heartbeat errors
3. Ensure cameras have valid IP addresses
4. Try manual heartbeat check via API
5. Verify settings are being saved correctly

### ICMP Ping Fails But TCP Works

**Problem**: ICMP checks always fail but TCP succeeds.

**Solutions**:
- Camera or network may be blocking ICMP
- Use `"tcp"` method instead
- Or use `"both"` method (will fall back to TCP automatically)

## API Reference

### POST `/api/dhcp/cameras/heartbeat`

Manually trigger heartbeat check for all cameras.

**Response**: 200 OK
```json
{
  "status": "success",
  "message": "Heartbeat check completed",
  "cameras": {
    "<mac_address>": {
      "hostname": "<string>",
      "ip_address": "<string>",
      "reachable": <boolean>,
      "status": "<connected|disconnected>",
      "last_seen": "<ISO8601 timestamp>"
    }
  }
}
```

**Response**: 500 Internal Server Error
```json
{
  "error": "Failed to perform heartbeat check"
}
```

## Implementation Details

### Code Structure

- **`pumaguard/camera_heartbeat.py`**: Core heartbeat monitoring logic
- **`pumaguard/web_ui.py`**: Integration with WebUI server lifecycle
- **`pumaguard/web_routes/dhcp.py`**: Manual check API endpoint
- **`pumaguard/presets.py`**: Configuration settings

### Key Classes

- `CameraHeartbeat`: Main monitoring class that runs background checks
  - `start()`: Start background monitoring thread
  - `stop()`: Stop monitoring thread gracefully
  - `check_now()`: Perform immediate check of all cameras
  - `check_camera(ip)`: Check single camera with configured method

### Testing

Comprehensive tests are available in `tests/test_camera_heartbeat.py`:

```bash
# Run heartbeat tests
uv run pytest tests/test_camera_heartbeat.py -v

# Run all tests
make test
```

Tests cover:
- ICMP ping (success, failure, timeout)
- TCP connection (success, failure, exceptions)
- Status updates (reachable, unreachable)
- Threading (start, stop, graceful shutdown)
- API endpoint (success, errors)

## Performance Considerations

- **Memory**: Minimal - single thread with small state
- **CPU**: Low - sleeps between checks, only active during checks
- **Network**: Depends on interval and method
  - ICMP: ~100 bytes per check
  - TCP: ~200 bytes per check (SYN/ACK/RST handshake)
  - For 5 cameras at 60s interval: < 1 KB/min

## Security Considerations

- Heartbeat checks do not transmit credentials
- TCP checks only establish connection, don't send data
- ICMP pings are standard network diagnostics
- All network activity stays within local network
- No external connections are made

## Future Enhancements

Potential improvements for future versions:

- [ ] Per-camera check intervals
- [ ] Per-camera check methods
- [ ] Webhooks for status change notifications
- [ ] Historical uptime tracking
- [ ] Dashboard with availability graphs
- [ ] Email/SMS alerts on camera offline
- [ ] HTTP/HTTPS health check endpoints
- [ ] ONVIF device discovery integration