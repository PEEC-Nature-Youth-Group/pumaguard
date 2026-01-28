# WiFi Configuration Feature

## Overview

The WiFi configuration feature allows users to switch between two WiFi modes through the PumaGuard web interface:

1. **Access Point (AP) Mode** - Creates a local hotspot that other devices can connect to
2. **Client Mode** - Connects to an existing WiFi network

This feature is particularly useful for field deployments where the device may need to operate in different network environments.

## Architecture

### Backend (Python/Flask)

The WiFi management functionality is implemented in `pumaguard/pumaguard/web_routes/wifi.py` and provides the following REST API endpoints.

**Note:** The system automatically detects the wireless network interface at startup (e.g., `wlan0`, `wlp3s0`, etc.) rather than hardcoding the interface name. If multiple wireless interfaces are present, the first one detected is used. If no wireless interface is detected, the system falls back to `wlan0` for compatibility.

#### `GET /api/wifi/scan`
Scans for available WiFi networks in the area.

**Important:** If the device is currently in AP mode (hostapd running), the scan will temporarily:
1. Stop hostapd and dnsmasq services
2. Let NetworkManager manage wlan0
3. Perform the scan
4. Restore AP mode automatically

This brief interruption (2-3 seconds) is necessary because hostapd cannot scan while managing the interface.

**Response:**
```json
{
  "networks": [
    {
      "ssid": "NetworkName",
      "signal": 85,
      "security": "WPA2",
      "secured": true,
      "connected": false
    }
  ]
}
```

#### `GET /api/wifi/mode`
Returns the current WiFi mode and connection status.

**Response:**
```json
{
  "mode": "ap|client",
  "ssid": "current-network-name",
  "connected": true
}
```

#### `PUT /api/wifi/mode`
Changes the WiFi mode.

**Request:**
```json
{
  "mode": "ap|client",
  "ssid": "network-name",
  "password": "optional-password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connected to WiFi network: network-name"
}
```

#### `POST /api/wifi/forget`
Removes a saved WiFi connection.

**Request:**
```json
{
  "ssid": "network-name"
}
```

### Frontend (Flutter)

The WiFi settings UI is implemented in `pumaguard-ui/lib/screens/wifi_settings_screen.dart`.

#### Features:
- **Current Status Display** - Shows current mode, network name, and connection status
- **Network Scanner** - Lists available WiFi networks with signal strength indicators
- **Client Mode Tab** - Connect to existing WiFi networks
- **AP Mode Tab** - Create a custom hotspot
- **Password Protection** - Supports secured networks with password input

#### API Service Methods

The following methods were added to `pumaguard-ui/lib/services/api_service.dart`:

- `scanWifiNetworks()` - Scan for available networks
- `getWifiMode()` - Get current WiFi mode
- `setWifiMode({mode, ssid, password})` - Change WiFi mode
- `forgetWifiNetwork(ssid)` - Remove saved network

## System Requirements

### Linux Dependencies

The WiFi management feature requires:

- **NetworkManager** (`nmcli` command) or **wpa_supplicant/wpa_cli** (for WiFi management)
- **hostapd** (for AP mode)
- **dnsmasq** (for DHCP in AP mode)
- **systemd-networkd** (for network configuration)
- A wireless network interface (automatically detected at startup)

These are typically installed by the Ansible playbook in `scripts/configure-device.yaml`.

### Wireless Interface Detection

The system automatically detects the wireless network interface by checking `/sys/class/net` for interfaces with wireless capabilities. This works with various interface naming schemes:

- Traditional names: `wlan0`, `wlan1`, etc.
- Predictable names: `wlp3s0`, `wlp2s0`, etc.
- Other wireless interfaces

The detection occurs once when the server starts. If multiple wireless interfaces are present, the first one detected is used. Virtual interfaces (docker, veth, br-) and loopback interfaces are automatically excluded.

### NetworkManager vs wpa_supplicant

The system automatically detects which WiFi management tool is available:

- **NetworkManager (nmcli)**: Fully supported for WiFi scanning and status checking. Preferred on desktop/laptop systems.
- **wpa_supplicant (wpa_cli)**: Fully supported for all WiFi operations. Used on embedded systems like Raspberry Pi.

**Current Limitations:**
- WiFi mode switching (`/api/wifi/mode` PUT endpoint) and network forgetting (`/api/wifi/forget`) currently require `wpa_supplicant` and are designed for embedded systems.
- On systems using NetworkManager (most desktops/laptops), WiFi scanning and status checking work perfectly, but mode switching should be done through your system's network settings.
- Future versions will add full NetworkManager support for all operations.

### Permissions

The backend must run with sufficient privileges to:
- Execute `nmcli` commands
- Read/write `/etc/hostapd/hostapd.conf`
- Restart system services (`hostapd`, `dnsmasq`)

On production systems, this is typically achieved by running the PumaGuard service as root or with appropriate sudo permissions.

## Usage

### Accessing WiFi Settings

1. Navigate to the PumaGuard web interface
2. Open **Settings** from the main menu
3. Scroll to the **System Settings** section
4. Click the **WiFi Settings** button

### Connecting to an Existing Network (Client Mode)

1. In the WiFi Settings screen, select the **Connect to Network** tab
2. Click **Scan for Networks** button
3. Select a network from the list
4. If the network is secured, enter the password in the dialog
5. Click **Connect**
6. Wait for the connection to establish (status will update automatically)

**Note:** When switching to client mode, the device will:
- Stop the hostapd and dnsmasq services
- Let NetworkManager manage the wlan0 interface
- Attempt to connect to the specified network
- Obtain an IP address via DHCP

### Creating a Hotspot (AP Mode)

1. In the WiFi Settings screen, select the **Create Hotspot** tab
2. Enter a **Network Name (SSID)** (e.g., "pumaguard")
3. Optionally, enter a **Password** (minimum 8 characters, leave empty for open network)
4. Click **Enable Hotspot**
5. Wait for the hotspot to start

**Note:** When switching to AP mode, the device will:
- Stop NetworkManager management of wlan0
- Configure and start hostapd with the specified SSID/password
- Start dnsmasq for DHCP services
- Assign IP address 192.168.52.1 to itself
- Provide IP addresses in the 192.168.52.50-150 range to clients

### Important Considerations

#### AP Mode Limitations
- **No Internet Access** - In AP mode, the device creates an isolated network without internet connectivity
- **Fixed IP Address** - The device will be accessible at `192.168.52.1:5000`
- **DHCP Range** - Connected devices receive IPs from 192.168.52.50 to 192.168.52.150

#### Client Mode Limitations
- **IP Address Changes** - When connecting to a new network, the device's IP address will change
- **Discovery** - You may need to use mDNS (`pumaguard.local`) or check your router to find the new IP
- **Network Requirements** - The target network must provide DHCP services

#### Switching Between Modes
- **Connection Loss** - When switching modes, you will temporarily lose connection to the device
- **IP Address Changes** - The device's IP address will change when switching modes
- **Reconnection** - You'll need to reconnect to the device on the new network/IP

## Security Considerations

### AP Mode Security
- **Always use a password** when creating a hotspot in production environments
- Use a strong password (at least 12 characters with mixed case, numbers, and symbols)
- WPA2 encryption is used for secured networks

### Client Mode Security
- Passwords are transmitted over the local network to the backend API
- Ensure the web interface is accessed over a secure connection when possible
- Consider using HTTPS if deploying in sensitive environments

### File System Permissions
- The `/etc/hostapd/hostapd.conf` file contains the AP password in plain text
- Ensure proper file permissions (600, root:root) are maintained
- The Ansible playbook handles this automatically

## Troubleshooting

### Enable Debug Logging

For detailed troubleshooting information, enable debug logging to see exactly what the system is detecting and doing:

```bash
export PUMAGUARD_LOG_LEVEL=DEBUG
uv run pumaguard-webui
```

Or test WiFi detection specifically:

```bash
cd pumaguard
uv run python test_wifi_debug.py
```

See [WiFi Debug Logging Reference](WIFI_DEBUG_LOGGING.md) for detailed information about interpreting debug output.

### Mode Switching Not Working (NetworkManager Systems)

**Problem:** WiFi mode switching or network forgetting fails with wpa_cli errors

**Cause:** These operations currently require wpa_supplicant but your system uses NetworkManager

**Solutions:**
- WiFi scanning and status checking will work fine with NetworkManager
- For changing networks, use your system's WiFi settings or NetworkManager directly
- Check debug logs for "set_wifi_mode called with NetworkManager detected" warning
- This is expected behavior on desktop/laptop systems; full NetworkManager support is planned for future releases

### Network Scan Returns Empty List
**Problem:** WiFi scan returns no networks

**Solutions:**
- **Enable debug logging** (see above) to see detailed scan output
- Ensure the WiFi adapter is functioning: `nmcli device status` or `ip link show`
- Check if the wireless interface is blocked: `rfkill list`
- Verify the correct interface is being used: Check server logs for "Using wireless interface: XXX"
- Verify NetworkManager or wpa_supplicant is running
- Try rescanning: The scan button automatically triggers a rescan
- Check debug logs for "Rescan result: exit code" to see if scan was triggered successfully

### Cannot Connect to Network
**Problem:** Connection fails when trying to connect to a network

**Solutions:**
- **Enable debug logging** to see detailed connection attempt information
- Verify the password is correct
- Check signal strength (weak signals may cause connection failures)
- Ensure the network is using a supported security type (WPA/WPA2)
- Check NetworkManager logs: `journalctl -u NetworkManager -f`
- Look for "Parsing network" debug messages to confirm the network was detected

### Hotspot Won't Start
**Problem:** AP mode fails to activate

**Solutions:**
- **Enable debug logging** to see which interface and tool are being used
- Check if hostapd is installed: `which hostapd`
- Verify hostapd configuration: `cat /etc/hostapd/hostapd.conf`
- Check hostapd service status: `systemctl status hostapd`
- Review logs: `journalctl -u hostapd -f`
- Ensure your wireless interface supports AP mode: `iw list | grep "Supported interface modes" -A 8`
- Check server logs for "Detected ... for WiFi management" to confirm tool detection
- Check server logs for "Using wireless interface: XXX" to confirm interface detection

### Connection Lost After Mode Switch
**Problem:** Cannot reconnect to device after switching modes

**Solutions:**
- **Enable debug logging** before switching to see mode transition details
- **From AP to Client:** Check your router's DHCP leases to find the new IP
- **From Client to AP:** Connect to the new hotspot and access `192.168.52.1:5000`
- Use mDNS if configured: `http://pumaguard.local:5000`
- Wait 30-60 seconds for services to fully restart

### No WiFi Interface or Tool Detected
**Problem:** Server logs show "No wireless interface detected" or "No WiFi management tool detected"

**Solutions:**
- **Check debug logs** for detailed detection information:
  - "Checking for wireless interfaces in /sys/class/net"
  - "Found network interfaces: ..." (shows all interfaces)
  - "Checking for nmcli" or "Checking for wpa_cli"
- Install NetworkManager if missing: `sudo apt install network-manager`
- Install wpa_supplicant if missing: `sudo apt install wpasupplicant`
- Verify WiFi adapter is recognized: `lsusb` or `lspci | grep -i wireless`
- Check if drivers are loaded: `lsmod | grep -i wifi`
- See [WiFi Interface Detection](WIFI_INTERFACE_DETECTION.md) for more details

## Testing

### Manual Testing

1. **Test AP Mode:**
   ```bash
   # Check hostapd is running
   systemctl status hostapd
   
   # Verify SSID is broadcasting
   nmcli device wifi list
   
   # Check DHCP is working
   systemctl status dnsmasq
   ```

2. **Test Client Mode:**
   ```bash
   # Check connection status
   nmcli connection show --active
   
   # Verify IP address (replace wlan0 with your interface name)
   ip addr show wlan0
   
   # Test connectivity
   ping -c 4 8.8.8.8
   ```

### API Testing

Using curl:

```bash
# Scan for networks
curl http://192.168.52.1:5000/api/wifi/scan

# Get current mode
curl http://192.168.52.1:5000/api/wifi/mode

# Switch to client mode
curl -X PUT http://192.168.52.1:5000/api/wifi/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "client", "ssid": "MyNetwork", "password": "mypassword"}'

# Switch to AP mode
curl -X PUT http://192.168.52.1:5000/api/wifi/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "ap", "ssid": "pumaguard", "password": "pumaguard"}'
```

## Development Notes

### Adding WiFi Features

When extending the WiFi functionality:

1. Add new endpoints to `web_routes/wifi.py`
2. Add corresponding API methods to `api_service.dart`
3. Update the UI in `wifi_settings_screen.dart`
4. Update this documentation
5. Add tests if appropriate

### Code Style

The WiFi routes follow the same patterns as other route modules:
- Use subprocess with timeouts for external commands
- Proper error handling with try/except blocks
- Logging at appropriate levels
- Return consistent JSON responses

### Flutter UI Guidelines

The WiFi settings screen follows Material Design 3:
- Uses Cards for grouping
- FilledButton for primary actions
- Proper error/success message display
- Loading indicators during operations
- Tab-based navigation for mode selection

## Future Enhancements

Potential improvements for future versions:

- [ ] **Saved Networks** - Remember and auto-connect to known networks
- [ ] **Network Profiles** - Switch between predefined network configurations
- [ ] **WiFi Statistics** - Show connection quality, data usage, etc.
- [ ] **Advanced Settings** - Configure IP address, DNS, gateway manually
- [ ] **5GHz Support** - Support for 5GHz WiFi bands
- [ ] **Hidden Networks** - Connect to networks with hidden SSIDs
- [ ] **Certificate Support** - Support for enterprise WPA2-Enterprise networks
- [ ] **Connection Scheduling** - Automatically switch modes based on schedule
- [ ] **Fallback Mode** - Automatically enable AP if client connection fails

## References

- NetworkManager documentation: https://networkmanager.dev/docs/
- hostapd documentation: https://w1.fi/hostapd/
- dnsmasq documentation: http://www.thekelleys.org.uk/dnsmasq/doc.html
- nmcli examples: `man nmcli-examples`
