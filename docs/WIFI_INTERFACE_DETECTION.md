# WiFi Interface Auto-Detection

## Overview

PumaGuard's WiFi management system now automatically detects the wireless network interface at startup, rather than hardcoding the interface name as `wlan0`. This makes the system more portable across different hardware configurations and Linux distributions.

## Motivation

Different systems use different naming conventions for wireless interfaces:

- **Traditional naming**: `wlan0`, `wlan1`, etc.
- **Predictable naming (systemd)**: `wlp3s0`, `wlp2s0`, etc.
- **Other variations**: `wlx00c0ca971b7a` (USB adapters with MAC-based names)

Hardcoding `wlan0` would fail on systems using predictable interface names or non-standard naming schemes.

## Implementation

### WiFi Management Tool Detection

The system automatically detects which WiFi management tool is available:

1. **NetworkManager (nmcli)**: Preferred on most modern Linux desktops and laptops
2. **wpa_supplicant (wpa_cli)**: Used on embedded systems and servers without NetworkManager

The `detect_wifi_management_tool()` function checks for these tools in order and uses the first one found. This ensures WiFi functionality works across different system configurations.

### Wireless Interface Detection

The `detect_wireless_interface()` function in `pumaguard/web_routes/wifi.py` performs the following steps:

1. **Check `/sys/class/net`**: Lists all network interfaces on the system
2. **Filter virtual interfaces**: Excludes loopback (`lo`), Docker (`docker*`), virtual Ethernet (`veth*`), and bridge (`br-*`) interfaces
3. **Check for wireless capability**: Tests for the presence of a `wireless` subdirectory, which indicates WiFi capability
4. **Return first match**: If multiple wireless interfaces exist, returns the first one found
5. **Fallback**: Returns `None` if no wireless interface is detected

### Detection Timing

Both the wireless interface and WiFi management tool detection occur **once when the server starts**, specifically when WiFi routes are registered via `register_wifi_routes()`. The detected values are then stored in closure variables and used by all WiFi API endpoints.

### Code Location

- **Tool detection function**: `pumaguard/web_routes/wifi.py::detect_wifi_management_tool()`
- **Interface detection function**: `pumaguard/web_routes/wifi.py::detect_wireless_interface()`
- **Usage**: Called in `register_wifi_routes()` before defining route handlers
- **Tests**: `tests/test_wifi_routes.py::TestWirelessInterfaceDetection`

## Behavior

### WiFi Management Tool Detection

On startup, the system logs which WiFi management tool it will use:

```
[2024-01-15 10:00:00] INFO: Detected NetworkManager (nmcli) for WiFi management
[2024-01-15 10:00:00] INFO: Using wireless interface: wlp0s20f3
```

or

```
[2024-01-15 10:00:00] INFO: Detected wpa_supplicant (wpa_cli) for WiFi management
[2024-01-15 10:00:00] INFO: Using wireless interface: wlan0
```

### Single Wireless Interface

Most common scenario - one wireless adapter:

```
[2024-01-15 10:00:00] INFO: Found wireless interface: wlan0
[2024-01-15 10:00:00] INFO: Using wireless interface: wlan0
```

### Multiple Wireless Interfaces

When multiple wireless adapters are present:

```
[2024-01-15 10:00:00] INFO: Found wireless interface: wlan0
[2024-01-15 10:00:00] INFO: Found wireless interface: wlan1
[2024-01-15 10:00:00] INFO: Multiple wireless interfaces found: wlan0, wlan1. Using first: wlan0
[2024-01-15 10:00:00] INFO: Using wireless interface: wlan0
```

The first interface detected is used. In future versions, this could be made configurable via the UI.

### No Wireless Interface

If no wireless interface is detected:

```
[2024-01-15 10:00:00] WARNING: No wireless interfaces detected
[2024-01-15 10:00:00] WARNING: No wireless interface detected. WiFi functionality will not be available. Falling back to 'wlan0' for compatibility.
```

The system falls back to `wlan0` to maintain compatibility with systems where detection might fail, but WiFi operations will likely fail if the interface doesn't actually exist.

### Non-Standard Interface Names

The system correctly handles predictable interface names:

```
[2024-01-15 10:00:00] INFO: Found wireless interface: wlp3s0
[2024-01-15 10:00:00] INFO: Using wireless interface: wlp3s0
```

## Advantages

1. **Portability**: Works across different Linux distributions and hardware
2. **Automatic Tool Selection**: Uses NetworkManager when available, falls back to wpa_supplicant
3. **Raspberry Pi Support**: Handles both `wlan0` (older models) and predictable names (newer systems)
4. **USB Adapters**: Automatically works with USB WiFi adapters that may use different names
5. **Multiple Adapters**: Gracefully handles systems with multiple wireless interfaces
6. **Zero Configuration**: No need to configure the interface name or WiFi tool

## Limitations

1. **First Interface Only**: When multiple wireless interfaces exist, only the first one is used
2. **No Runtime Detection**: Interface is detected at startup only; requires server restart if hardware changes
3. **No Manual Override**: Cannot manually specify which interface to use (could be added in future)

## Future Enhancements

### UI Configuration for Multiple Interfaces

For systems with multiple wireless adapters, a configuration option could be added to the WiFi settings UI:

```
Wireless Interface: [wlan0 ▼]  (Detected: wlan0, wlan1)
```

This would allow users to choose which adapter to use for WiFi operations.

### Runtime Detection

The system could periodically re-check for wireless interfaces, allowing hot-pluggable USB adapters to be detected without restarting the server.

### Manual Override

An environment variable or configuration setting could allow administrators to override the auto-detected interface:

```bash
PUMAGUARD_WIFI_INTERFACE=wlan1 pumaguard-webui
```

## Testing

### Automated Tests

The `tests/test_wifi_routes.py` file includes comprehensive tests for interface detection:

- `test_detect_single_wireless_interface`: Standard single-adapter scenario
- `test_detect_multiple_wireless_interfaces`: Multiple adapters present
- `test_detect_no_wireless_interface`: No adapters present
- `test_detect_non_standard_interface_name`: Predictable naming schemes
- `test_detect_missing_sys_directory`: `/sys` not available
- `test_detect_filters_virtual_interfaces`: Virtual interfaces excluded

Run tests with:

```bash
uv run python -m pytest tests/test_wifi_routes.py::TestWirelessInterfaceDetection -v
```

### Manual Testing

1. **Check detected interface**:
   ```bash
   # Start the server and check logs
   uv run pumaguard-webui
   # Look for: "Using wireless interface: XXX"
   ```

2. **Verify interface exists**:
   ```bash
   # List all network interfaces
   ip link show
   
   # Check specifically for wireless
   ls /sys/class/net/*/wireless
   ```

3. **Test with different hardware**:
   - Test on Raspberry Pi (various models)
   - Test on Ubuntu/Debian with predictable names
   - Test with USB WiFi adapters
   - Test with multiple adapters plugged in

## Troubleshooting

### WiFi Features Not Working

**Symptoms**: WiFi scan or mode changes fail with interface errors

**Check**:
1. Look at server startup logs for "Detected ... for WiFi management"
2. Look at server startup logs for "Using wireless interface: XXX"
3. Verify the interface exists: `ip link show <interface>`
4. Check if interface has wireless capability: `ls /sys/class/net/<interface>/wireless`
5. Verify WiFi management tool is available: `which nmcli` or `which wpa_cli`

**Solutions**:
- If no WiFi tool detected, install NetworkManager: `sudo apt install network-manager`
- If detection failed, check `rfkill list` to ensure wireless isn't blocked
- Verify wireless drivers are loaded: `lsmod | grep wifi`
- Check dmesg for hardware errors: `dmesg | grep -i wifi`
- For wpa_cli, ensure wpa_supplicant is running: `systemctl status wpa_supplicant`

### Wrong Interface Detected

**Symptoms**: Multiple wireless interfaces present but wrong one is used

**Workaround**: Currently, the first interface is always used. To prioritize a different interface:
1. Temporarily rename or disable the unwanted interface
2. Restart the server

**Future**: This will be addressed by adding manual interface selection in the UI.

## References

- Linux wireless interface detection: `/sys/class/net/*/wireless`
- Predictable Network Interface Names: https://www.freedesktop.org/wiki/Software/systemd/PredictableNetworkInterfaceNames/
- Related code: `pumaguard/web_routes/wifi.py`
- Tests: `tests/test_wifi_routes.py`
