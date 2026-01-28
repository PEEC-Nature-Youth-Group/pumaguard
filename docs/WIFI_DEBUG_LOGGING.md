# WiFi Debug Logging Reference

## Overview

The WiFi management system includes comprehensive debug logging to help troubleshoot interface detection, tool selection, and network scanning issues. This guide explains how to enable debug logging and interpret the output.

## Enabling Debug Logging

### Method 1: Environment Variable

Set the log level to DEBUG before starting the server:

```bash
export PUMAGUARD_LOG_LEVEL=DEBUG
uv run pumaguard-webui
```

### Method 2: Command Line (if supported)

```bash
uv run pumaguard-webui --log-level DEBUG
```

### Method 3: Python Code

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Debug Output During Startup

### 1. Wireless Interface Detection

When the server starts, you'll see detailed logging of the interface detection process:

```
DEBUG - pumaguard.web_routes.wifi - Checking for wireless interfaces in /sys/class/net
DEBUG - pumaguard.web_routes.wifi - Found network interfaces: lo, eth0, wlp0s20f3, docker0
DEBUG - pumaguard.web_routes.wifi - Skipping virtual interface: lo
DEBUG - pumaguard.web_routes.wifi - Checking if eth0 is wireless: /sys/class/net/eth0/wireless
DEBUG - pumaguard.web_routes.wifi - eth0 is not a wireless interface
DEBUG - pumaguard.web_routes.wifi - Checking if wlp0s20f3 is wireless: /sys/class/net/wlp0s20f3/wireless
INFO  - pumaguard.web_routes.wifi - Found wireless interface: wlp0s20f3
DEBUG - pumaguard.web_routes.wifi - Skipping virtual interface: docker0
INFO  - pumaguard.web_routes.wifi - Using wireless interface: wlp0s20f3
```

**What to look for:**
- ✅ "Found wireless interface: X" means detection succeeded
- ⚠️ "No wireless interfaces detected" means no WiFi adapter found
- 🔍 Check which interfaces are being checked and why they're skipped

### 2. WiFi Management Tool Detection

Next, the system detects which WiFi management tool is available:

```
DEBUG - pumaguard.web_routes.wifi - Detecting WiFi management tool...
DEBUG - pumaguard.web_routes.wifi - Checking for nmcli (NetworkManager)...
INFO  - pumaguard.web_routes.wifi - Detected NetworkManager (nmcli) for WiFi management
DEBUG - pumaguard.web_routes.wifi - nmcli version: nmcli tool, version 1.42.4
```

**OR** if NetworkManager isn't available:

```
DEBUG - pumaguard.web_routes.wifi - Detecting WiFi management tool...
DEBUG - pumaguard.web_routes.wifi - Checking for nmcli (NetworkManager)...
DEBUG - pumaguard.web_routes.wifi - nmcli not found in PATH
DEBUG - pumaguard.web_routes.wifi - Checking for wpa_cli (wpa_supplicant)...
INFO  - pumaguard.web_routes.wifi - Detected wpa_supplicant (wpa_cli) for WiFi management
DEBUG - pumaguard.web_routes.wifi - wpa_cli version: wpa_cli v2.10
```

**What to look for:**
- ✅ "Detected NetworkManager" or "Detected wpa_supplicant" means success
- ⚠️ "No WiFi management tool detected" means both nmcli and wpa_cli are missing
- 🔍 Check which tool was found first (nmcli is preferred)

## Debug Output During WiFi Scan

### Using NetworkManager (nmcli)

When you trigger a WiFi scan through the UI or API:

```
DEBUG - pumaguard.web_routes.wifi - Using NetworkManager (nmcli) to scan for WiFi networks
DEBUG - pumaguard.web_routes.wifi - Triggering WiFi rescan with nmcli...
DEBUG - pumaguard.web_routes.wifi - Rescan result: exit code 0
DEBUG - pumaguard.web_routes.wifi - Waiting 2 seconds for scan to complete...
DEBUG - pumaguard.web_routes.wifi - Retrieving WiFi scan results from nmcli...
DEBUG - pumaguard.web_routes.wifi - Got 245 bytes of scan results
DEBUG - pumaguard.web_routes.wifi - Parsing network: SSID='MyHomeNetwork', Signal=85, Security='WPA2', Active=yes
DEBUG - pumaguard.web_routes.wifi - Parsing network: SSID='NeighborWiFi', Signal=45, Security='WPA2', Active=no
DEBUG - pumaguard.web_routes.wifi - Parsing network: SSID='CoffeeShop_Guest', Signal=30, Security='', Active=no
DEBUG - pumaguard.web_routes.wifi - Parsing network: SSID='MyHomeNetwork', Signal=82, Security='WPA2', Active=yes
DEBUG - pumaguard.web_routes.wifi - Skipping duplicate SSID: MyHomeNetwork
DEBUG - pumaguard.web_routes.wifi - Parsed 4 networks from nmcli output
INFO  - pumaguard.web_routes.wifi - WiFi scan completed successfully: found 3 networks
DEBUG - pumaguard.web_routes.wifi - Network 1: MyHomeNetwork (signal: 85%, security: WPA2, connected: True)
DEBUG - pumaguard.web_routes.wifi - Network 2: NeighborWiFi (signal: 45%, security: WPA2, connected: False)
DEBUG - pumaguard.web_routes.wifi - Network 3: CoffeeShop_Guest (signal: 30%, security: Open, connected: False)
```

**What to look for:**
- ✅ "Rescan result: exit code 0" means scan was triggered successfully
- ✅ "WiFi scan completed successfully" means networks were found and parsed
- ⚠️ "Rescan result: exit code N" (non-zero) may indicate permission issues
- 🔍 Each network being parsed shows SSID, signal strength, and security
- 🔍 Duplicate SSIDs are filtered (keeps first occurrence, usually strongest signal)

### Using wpa_supplicant (wpa_cli)

```
DEBUG - pumaguard.web_routes.wifi - Using wpa_cli to scan for WiFi networks on interface wlan0
DEBUG - pumaguard.web_routes.wifi - Triggering WiFi scan with wpa_cli...
DEBUG - pumaguard.web_routes.wifi - Scan trigger result: OK (exit code 0)
DEBUG - pumaguard.web_routes.wifi - Waiting for scan to complete (max 20 attempts)...
DEBUG - pumaguard.web_routes.wifi - Attempt 1: Found 0 networks
DEBUG - pumaguard.web_routes.wifi - Attempt 2: Found 0 networks
DEBUG - pumaguard.web_routes.wifi - Attempt 3: Found 2 networks
DEBUG - pumaguard.web_routes.wifi - Attempt 4: Found 3 networks
DEBUG - pumaguard.web_routes.wifi - Attempt 5: Found 3 networks
DEBUG - pumaguard.web_routes.wifi - Scan completed with 3 networks after 5 attempts
DEBUG - pumaguard.web_routes.wifi - Retrieving final scan results from wpa_cli...
DEBUG - pumaguard.web_routes.wifi - Got 312 bytes of scan results
DEBUG - pumaguard.web_routes.wifi - Parsing 4 lines of wpa_cli scan results
DEBUG - pumaguard.web_routes.wifi - Skipping header line
DEBUG - pumaguard.web_routes.wifi - Parsing network: SSID='MyNetwork', Signal=-55 dBm, Flags='[WPA2-PSK-CCMP][ESS]'
DEBUG - pumaguard.web_routes.wifi - Parsing network: SSID='OpenWiFi', Signal=-70 dBm, Flags='[ESS]'
INFO  - pumaguard.web_routes.wifi - WiFi scan completed successfully: found 2 networks
DEBUG - pumaguard.web_routes.wifi - Network 1: MyNetwork (signal: 90%, security: WPA2, connected: False)
DEBUG - pumaguard.web_routes.wifi - Network 2: OpenWiFi (signal: 60%, security: Open, connected: False)
```

**What to look for:**
- ✅ "Scan trigger result: OK" means wpa_supplicant accepted the scan request
- ✅ Network count stabilizing indicates scan completion
- ⚠️ "Scan trigger result: FAIL" means wpa_supplicant couldn't scan (may be in AP mode)
- 🔍 Signal strength shown in dBm (e.g., -55 dBm = good, -90 dBm = weak)
- 🔍 Flags indicate security type (WPA2-PSK, WPA, WEP, or empty for open)

## Common Debug Patterns

### Success Pattern (NetworkManager)

```
INFO  - Found wireless interface: wlp0s20f3
INFO  - Detected NetworkManager (nmcli) for WiFi management
INFO  - Using wireless interface: wlp0s20f3
[...user triggers scan...]
DEBUG - Using NetworkManager (nmcli) to scan for WiFi networks
DEBUG - Rescan result: exit code 0
INFO  - WiFi scan completed successfully: found 5 networks
```

### Success Pattern (wpa_supplicant)

```
INFO  - Found wireless interface: wlan0
INFO  - Detected wpa_supplicant (wpa_cli) for WiFi management
INFO  - Using wireless interface: wlan0
[...user triggers scan...]
DEBUG - Using wpa_cli to scan for WiFi networks on interface wlan0
DEBUG - Scan trigger result: OK (exit code 0)
DEBUG - Scan completed with 3 networks after 5 attempts
INFO  - WiFi scan completed successfully: found 3 networks
```

### No Wireless Interface

```
DEBUG - Checking for wireless interfaces in /sys/class/net
DEBUG - Found network interfaces: lo, eth0, docker0
DEBUG - Skipping virtual interface: lo
DEBUG - eth0 is not a wireless interface
DEBUG - Skipping virtual interface: docker0
WARNING - No wireless interfaces detected
WARNING - No wireless interface detected. WiFi functionality will not be available. Falling back to 'wlan0' for compatibility.
```

**Action:** Check if WiFi adapter is connected and drivers are loaded.

### No WiFi Management Tool

```
INFO  - Found wireless interface: wlan0
DEBUG - Detecting WiFi management tool...
DEBUG - Checking for nmcli (NetworkManager)...
DEBUG - nmcli not found in PATH
DEBUG - Checking for wpa_cli (wpa_supplicant)...
DEBUG - wpa_cli not found in PATH
WARNING - No WiFi management tool detected (nmcli or wpa_cli)
```

**Action:** Install NetworkManager (`sudo apt install network-manager`) or wpa_supplicant.

### Scan Failed (Permission Issue)

```
DEBUG - Using NetworkManager (nmcli) to scan for WiFi networks
DEBUG - Triggering WiFi rescan with nmcli...
DEBUG - Rescan result: exit code 1
DEBUG - Rescan stderr: Error: Connection activation failed: Not authorized to control networking.
ERROR - Error scanning WiFi networks
```

**Action:** Check user permissions or run server with appropriate privileges.

### Scan Failed (wpa_supplicant not running)

```
DEBUG - Using wpa_cli to scan for WiFi networks on interface wlan0
DEBUG - Triggering WiFi scan with wpa_cli...
DEBUG - Scan trigger result: Failed to connect to wpa_supplicant (exit code 255)
ERROR - Error scanning WiFi networks
```

**Action:** Start wpa_supplicant service: `sudo systemctl start wpa_supplicant@wlan0`

## Troubleshooting Guide

### Problem: No networks found in scan

**Check debug logs for:**
1. "Rescan result: exit code 0" - If non-zero, scan may have failed
2. "Got N bytes of scan results" - If N is very small (< 50), scan may be empty
3. "Parsed X networks from nmcli output" - Should match number found
4. "Skipping empty SSID" or "Skipping duplicate SSID" - Networks being filtered

**Solutions:**
- Ensure WiFi adapter is not blocked: `rfkill list`
- Wait longer for scan to complete (especially on wpa_cli)
- Check if adapter supports scanning while connected
- Verify networks are actually in range

### Problem: Wrong interface detected

**Check debug logs for:**
1. "Found network interfaces: ..." - Shows all interfaces
2. "Found wireless interface: X" - Shows which was selected
3. Multiple "Found wireless interface" messages - System picks first one

**Solutions:**
- Temporarily disable unwanted wireless interfaces
- Note: Manual interface selection not yet implemented (future feature)

### Problem: Wrong WiFi tool being used

**Check debug logs for:**
1. "Checking for nmcli (NetworkManager)..." - Was it found?
2. "Checking for wpa_cli (wpa_supplicant)..." - Was it found?
3. Tool version output - Confirms which is being used

**Note:** System prefers NetworkManager over wpa_supplicant. To force wpa_cli, uninstall or disable NetworkManager (not recommended for desktop systems).

## Test Script

A test script is provided to exercise WiFi detection with full debug output:

```bash
cd pumaguard
python test_wifi_debug.py
```

This will:
1. Detect wireless interface (with detailed logging)
2. Detect WiFi management tool (with detailed logging)
3. Register WiFi routes
4. Attempt a WiFi scan (if tools available)
5. Display results in a readable format

## Log Levels

The WiFi system uses these log levels:

- **DEBUG**: Detailed step-by-step information (interface checks, command output, parsing)
- **INFO**: Important milestones (interface found, tool detected, scan completed)
- **WARNING**: Non-fatal issues (no interface found, scan timeout, falling back to defaults)
- **ERROR**: Failures (scan errors, command failures, exceptions)

## Performance Considerations

Debug logging adds overhead but is generally negligible:

- Interface detection: ~5-10ms extra per interface checked
- Tool detection: ~10-20ms extra per tool checked
- Scan logging: ~1-2ms extra per network parsed

For production deployments, use INFO level logging instead of DEBUG.

## Related Documentation

- [WiFi Configuration](WIFI_CONFIGURATION.md) - User-facing WiFi features
- [WiFi Interface Detection](WIFI_INTERFACE_DETECTION.md) - Technical implementation details
- [WiFi Implementation Complete](WIFI_IMPLEMENTATION_COMPLETE.md) - Development history