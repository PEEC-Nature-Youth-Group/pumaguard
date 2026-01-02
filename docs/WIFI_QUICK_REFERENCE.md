# WiFi Configuration Quick Reference

## Quick Access

1. Open PumaGuard Web UI
2. Go to **Settings** → **WiFi Settings** button (in System Settings section)

## Switch to Client Mode (Connect to Existing WiFi)

1. Click **Connect to Network** tab
2. Click **Scan for Networks**
3. Select network from list
4. Enter password (if required)
5. Click **Connect**
6. Device IP will change - reconnect using new IP or `pumaguard.local`

## Switch to AP Mode (Create Hotspot)

1. Click **Create Hotspot** tab
2. Enter **Network Name** (e.g., "pumaguard")
3. Enter **Password** (optional, minimum 8 characters)
4. Click **Enable Hotspot**
5. Device will be at `192.168.52.1:5000`

## Important Notes

### AP Mode
- ✅ Cameras can connect directly
- ✅ Fixed IP: `192.168.52.1`
- ❌ No internet access
- ❌ Isolated network

### Client Mode
- ✅ Internet access (if network has it)
- ✅ Can access device from anywhere on network
- ⚠️ Device IP changes when connecting
- ⚠️ Use mDNS (`pumaguard.local`) for easy access

## Troubleshooting

### Can't find device after switching modes

**AP Mode:**
- Connect to the new hotspot SSID
- Access at: `http://192.168.52.1:5000`

**Client Mode:**
- Check router DHCP leases for device IP
- Try: `http://pumaguard.local:5000` (mDNS)
- Wait 30-60 seconds for services to restart

### Scan returns no networks
- Ensure WiFi adapter is working
- Check if WiFi is blocked: `rfkill list`
- Try scanning again

### Connection fails
- Verify password is correct
- Check signal strength (move closer to router)
- Ensure network uses WPA/WPA2 security

## API Endpoints

```bash
# Scan networks
GET /api/wifi/scan

# Get current mode
GET /api/wifi/mode

# Change mode
PUT /api/wifi/mode
{
  "mode": "ap|client",
  "ssid": "network-name",
  "password": "optional"
}

# Forget network
POST /api/wifi/forget
{
  "ssid": "network-name"
}
```

## Default Settings (from Ansible)

**AP Mode Defaults:**
- SSID: `pumaguard`
- Password: `pumaguard`
- Channel: 7
- IP Range: 192.168.52.50-150
- Gateway: 192.168.52.1

## Command Line (Advanced)

```bash
# Check current status
nmcli connection show --active

# Manual AP mode setup
sudo systemctl start hostapd
sudo systemctl start dnsmasq

# Manual client mode
sudo nmcli device wifi connect "SSID" password "PASSWORD"

# View logs
journalctl -u hostapd -f
journalctl -u NetworkManager -f
```

## Security Best Practices

1. **Always use a password** for AP mode in production
2. Use **strong passwords** (12+ characters, mixed case, numbers, symbols)
3. Change default credentials from Ansible deployment
4. Monitor connected devices in AP mode
5. Use **HTTPS** when possible (requires SSL setup)

## Need More Help?

See full documentation: `docs/WIFI_CONFIGURATION.md`
