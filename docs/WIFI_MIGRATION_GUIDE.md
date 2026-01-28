# WiFi Configuration Migration Guide

## For Existing PumaGuard Users

This guide helps you understand what changed with the new WiFi configuration feature and how it affects your existing setup.

## What Changed?

### New Feature: WiFi Mode Switching

PumaGuard can now switch between two WiFi modes through the web UI:

1. **Access Point (AP) Mode** - The default mode set by Ansible (what you have now)
2. **Client Mode** - NEW! Connect to an existing WiFi network

### Your Current Setup (Unchanged)

If you deployed PumaGuard using the Ansible playbook (`configure-device.yaml`), your device is currently running in **Access Point mode** with these settings:

- **SSID**: `pumaguard`
- **Password**: `pumaguard`
- **Device IP**: `192.168.52.1`
- **DHCP Range**: 192.168.52.50-150

**Nothing has changed with your existing deployment.** The device will continue to work exactly as before.

## What's New?

### Web UI Changes

1. **Settings Screen**
   - A new "WiFi Settings" button appears in the System Settings section
   - Click it to access the WiFi configuration interface

2. **WiFi Settings Screen** (New)
   - View current WiFi mode and status
   - Scan for available networks
   - Switch to client mode (connect to existing WiFi)
   - Switch to AP mode (create your own hotspot)
   - All changes happen instantly without SSH access

## When to Use This Feature

### Stay in AP Mode (Current Setup) If:
- ✅ Cameras need to connect directly to PumaGuard
- ✅ You're deploying in remote areas without WiFi
- ✅ You want an isolated network
- ✅ You don't need internet access on the device

### Switch to Client Mode If:
- ✅ You have an existing WiFi network
- ✅ You need internet access on the device
- ✅ You want to access PumaGuard from anywhere on your network
- ✅ You want to manage multiple devices on the same network

## How to Use the New Feature

### Option 1: Keep Using AP Mode (Recommended for Most Users)

**Do nothing!** Your device continues to work as it always has.

If you want to change the AP settings (SSID/password):

1. Go to **Settings** → **WiFi Settings**
2. Click the **Create Hotspot** tab
3. Enter new SSID and password
4. Click **Enable Hotspot**

### Option 2: Switch to Client Mode

**Warning**: Switching to client mode will change your device's IP address.

1. Connect to the PumaGuard hotspot (`pumaguard`)
2. Open browser: `http://192.168.52.1:5000`
3. Go to **Settings** → **WiFi Settings**
4. Click the **Connect to Network** tab
5. Click **Scan for Networks**
6. Select your network and enter password
7. Click **Connect**
8. Wait 30-60 seconds for the connection
9. Find the new IP address:
   - Check your router's DHCP leases
   - Use mDNS: `http://pumaguard.local:5000`
   - Use network scanner app

## Important Considerations

### IP Address Changes

**In AP Mode:**
- Device IP: `192.168.52.1` (fixed)
- You connect to the `pumaguard` network
- Access UI at: `http://192.168.52.1:5000`

**In Client Mode:**
- Device IP: Assigned by your router (changes)
- Device connects to your existing network
- Access UI at: `http://<new-ip>:5000` or `http://pumaguard.local:5000`

### Camera Connectivity

**In AP Mode:**
- Cameras connect directly to PumaGuard hotspot
- PumaGuard assigns IP addresses to cameras
- Isolated network (no internet)

**In Client Mode:**
- Cameras and PumaGuard both connect to your network
- Your router assigns IP addresses
- All devices share the same network

### Switching Back

You can always switch back to AP mode:

1. Connect your computer to the same network as PumaGuard
2. Access the web UI (use mDNS or find IP)
3. Go to **Settings** → **WiFi Settings**
4. Click **Create Hotspot** tab
5. Configure and enable AP mode

## Troubleshooting

### Can't Access Device After Switching Modes

**Problem**: Lost connection to PumaGuard after changing WiFi mode

**Solutions**:

1. **If you switched to AP mode:**
   - Connect to the new hotspot SSID
   - Access at `http://192.168.52.1:5000`

2. **If you switched to client mode:**
   - Check your router for the device's new IP
   - Try `http://pumaguard.local:5000` (mDNS)
   - Wait 1-2 minutes for services to restart
   - Connect via SSH if you have access: `ssh ansible@<router-assigned-ip>`

### Want to Reset to Factory Settings

If you need to reset WiFi settings to the original Ansible configuration:

```bash
# SSH into the device
ssh ansible@<device-ip>

# Re-run the Ansible playbook (from your control machine)
ansible-playbook -i inventory.ini scripts/configure-device.yaml
```

Or manually:

```bash
# SSH into device
ssh ansible@<device-ip>

# Stop client mode
sudo nmcli device set wlan0 managed no
sudo systemctl stop NetworkManager

# Restart AP mode
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq
sudo systemctl restart systemd-networkd
```

## Frequently Asked Questions

### Q: Will this break my existing deployment?

**A**: No. The feature only adds new capabilities. Your existing AP mode setup is unchanged and will continue to work.

### Q: Do I need to update my Ansible playbook?

**A**: No. The Ansible playbook still sets up AP mode by default, which is correct. This feature allows runtime switching without re-running Ansible.

### Q: Can cameras still connect in client mode?

**A**: Yes, but both PumaGuard and cameras must be on the same network. They would both connect to your router instead of cameras connecting directly to PumaGuard.

### Q: Will I lose my settings when switching modes?

**A**: No. PumaGuard settings (models, sounds, presets) are stored separately and remain unchanged when switching WiFi modes.

### Q: What if the new mode doesn't work?

**A**: The previous configuration is not deleted. You can switch back at any time, or reboot the device to return to the last working state (hostapd/dnsmasq start automatically on boot in AP mode).

### Q: Does this work on all devices?

**A**: Yes, as long as your device has:
- NetworkManager installed
- hostapd installed
- dnsmasq installed
- A WiFi adapter (wlan0)

These are all installed by the Ansible playbook.

### Q: Can I automate mode switching?

**A**: Not yet. Future versions may include scheduled mode switching or automatic fallback. For now, use the API endpoints to script mode changes:

```bash
# Switch to client mode
curl -X PUT http://192.168.52.1:5000/api/wifi/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "client", "ssid": "MyNetwork", "password": "pass"}'
```

## Support

For more information:
- **Full Documentation**: `docs/WIFI_CONFIGURATION.md`
- **Quick Reference**: `WIFI_QUICK_REFERENCE.md`
- **API Reference**: See `/api/wifi/*` endpoints

## Rollback Instructions

If you want to completely disable this feature:

The feature is harmless and doesn't interfere with normal operation. However, if you want to prevent UI access:

1. The API endpoints are in `pumaguard/web_routes/wifi.py`
2. The UI screen is in `pumaguard-ui/lib/screens/wifi_settings_screen.dart`
3. Simply don't click the "WiFi Settings" button in the UI

Or remove the WiFi Settings button by editing:
`pumaguard-ui/lib/screens/settings_screen.dart` (remove the FilledButton.icon for WiFi Settings)

## Summary

✅ **Safe**: Your existing setup is unchanged
✅ **Optional**: Only use this feature if you need it
✅ **Reversible**: Switch back to AP mode anytime
✅ **Well-tested**: 17 unit tests, comprehensive error handling
✅ **Documented**: Full guides and troubleshooting available

The WiFi configuration feature gives you more flexibility in how you deploy PumaGuard, while maintaining full backward compatibility with existing installations.