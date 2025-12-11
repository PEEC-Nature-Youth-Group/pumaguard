# Camera URL Troubleshooting Guide

This guide helps you diagnose and fix issues with the Camera URL feature in PumaGuard.

## Quick Fixes

### Problem: Camera URL not saving

**Symptoms:**
- You enter an IP address in Settings → System Settings → Camera URL
- The field appears to accept the input
- But when you refresh or check again, it's empty

**Solution:**
1. **Verify the backend is running**: Make sure PumaGuard server is running
2. **Check browser console**: Open browser DevTools (F12) and look for errors
3. **Wait for auto-save**: The field auto-saves after 1 second of no typing - wait a moment
4. **Check server logs**: Look for this line in the server output:
   ```
   INFO - Camera URL requested: 'your-ip-here'
   ```

**Debug steps:**
```bash
# 1. Restart the server with verbose logging
uv run pumaguard-webui --host 0.0.0.0

# 2. In browser console, check for API errors:
# Press F12 → Console tab → look for red errors

# 3. Check the settings file was updated:
cat ~/.config/pumaguard/pumaguard-settings.yaml | grep camera-url
```

### Problem: "Camera URL not configured" message

**Symptoms:**
- You click the Camera button
- You see: "Camera URL not configured. Please set it in Settings."

**Cause:** The camera URL is empty or wasn't saved successfully.

**Solution:**
1. Go to **Settings** (from home screen)
2. Scroll down to **System Settings** section
3. Enter your camera's IP address in the **Camera URL** field
   - Examples: `192.168.52.96` or `http://192.168.1.100`
4. Wait 1-2 seconds for auto-save
5. Look for green "Settings saved successfully" message
6. Go back to home and try the Camera button again

### Problem: "Could not open camera URL" error

**Symptoms:**
- Camera URL is configured
- You click the Camera button
- You see: "Could not open camera URL: http://..."

**Possible causes:**
1. **Camera is offline** - Check if camera is powered on and connected
2. **Wrong IP address** - Camera's IP may have changed
3. **Wrong port** - Camera might be on a different port
4. **Invalid URL format** - Check for typos

**Solutions:**

**1. Verify camera is accessible:**
```bash
# From the PumaGuard server, test connectivity:
ping 192.168.52.96

# Test HTTP connection:
curl http://192.168.52.96

# If camera uses a different port:
curl http://192.168.52.96:8080
```

**2. Find camera's current IP:**
```bash
# Scan network for camera (may need sudo):
nmap -p 80,443,554,8000,8080 192.168.52.0/24

# Or use arp-scan:
sudo arp-scan --localnet
```

**3. Try different ports:**
Common camera ports:
- `http://camera-ip` (port 80, default)
- `http://camera-ip:8080`
- `http://camera-ip:443` or `https://camera-ip`
- `http://camera-ip:8000`

Update the Camera URL setting with the correct port.

**4. Set up DHCP reservation (recommended):**

To prevent the IP from changing:
1. Find camera's MAC address: `2C:C3:E6:0A:54:53` (example from nmap)
2. Log into your router's admin interface
3. Find DHCP settings → Static DHCP or DHCP Reservations
4. Add reservation: MAC `2C:C3:E6:0A:54:53` → IP `192.168.52.96`
5. Save and reboot camera (or wait for DHCP lease renewal)

## Debug Mode

For detailed troubleshooting, enable debug output:

### Browser Debug (Flutter Web)

1. Open browser DevTools: Press **F12**
2. Go to **Console** tab
3. Try the Camera button
4. Look for debug messages starting with `[HomeScreen._openCamera]` or `[ApiService.getCameraUrl]`

**Example successful output:**
```
[HomeScreen._openCamera] Starting camera open...
[ApiService.getCameraUrl] Requesting URL: http://192.168.51.104:5000/api/camera/url
[ApiService.getCameraUrl] Response status: 200
[ApiService.getCameraUrl] Response body: {"camera_url":"http://192.168.52.96"}
[ApiService.getCameraUrl] Parsed camera_url: "http://192.168.52.96"
[HomeScreen._openCamera] Got camera URL: "http://192.168.52.96"
[HomeScreen._openCamera] URL to open: "http://192.168.52.96"
[HomeScreen._openCamera] Parsed URI: http://192.168.52.96
[HomeScreen._openCamera] canLaunchUrl result: true
[HomeScreen._openCamera] Launching URL...
[HomeScreen._openCamera] URL launched successfully
```

**Example error output:**
```
[ApiService.getCameraUrl] Response status: 500
[ApiService.getCameraUrl] Response body: {"error":"..."}
```

### Server Debug (Python Backend)

Check the server console output for:

```
INFO - Camera URL requested: 'http://192.168.52.96'
```

If you see errors, check:
```
ERROR - Error getting camera URL
```

### Settings Save Debug

When saving camera URL in settings:

1. Open browser console (F12)
2. Enter camera URL in settings field
3. Wait 1 second
4. Look for:
```
[SettingsScreen._saveSettings] Camera URL from controller: "192.168.52.96"
[SettingsScreen._saveSettings] Settings object camera URL: "192.168.52.96"
[ApiService.updateSettings] Settings JSON: {..., "camera-url": "192.168.52.96", ...}
[ApiService.updateSettings] Response status: 200
[SettingsScreen._saveSettings] Settings saved successfully
```

## Common Issues

### Issue: Camera URL shows empty after refresh

**Diagnosis:**
```bash
# Check if setting is in the file:
cat ~/.config/pumaguard/pumaguard-settings.yaml | grep camera-url

# Expected output:
# camera-url: http://192.168.52.96

# If not present, there's a serialization issue
```

**Fix:**
The backend code includes the fix - make sure you're running the latest version:
```bash
# Update to latest code
git pull

# Restart server
uv run pumaguard-webui --host 0.0.0.0
```

### Issue: Wrong network segment

**Symptoms:**
- PumaGuard is on `192.168.51.x` network
- Camera is on `192.168.52.x` network
- Cannot access camera from browser

**Check your network setup:**
```bash
# Show all network interfaces:
ip addr show

# Example output:
# eth0: inet 192.168.51.104/24   (wired network)
# wlan0: inet 192.168.52.1/24    (wireless network)
```

**Solution:**
If PumaGuard server has multiple network interfaces:
1. Camera should be accessible from the server directly
2. But your browser might be on a different network
3. Either:
   - Connect your computer to the same network as the camera
   - Configure routing between networks
   - Access PumaGuard from the network the camera is on

### Issue: CORS errors in browser

**Symptoms:**
Browser console shows:
```
Access to XMLHttpRequest at 'http://...' from origin 'http://...' has been blocked by CORS policy
```

**Cause:** CORS is already enabled in PumaGuard, but this might indicate:
- Trying to access camera directly from browser (expected - camera might not have CORS)
- Accessing PumaGuard API from wrong origin

**Note:** 
- PumaGuard → Camera: Server-side connection, no CORS issue
- Browser → Camera: Opens in new tab, bypasses CORS
- Browser → PumaGuard API: CORS enabled, should work

If you see CORS errors for PumaGuard API:
```bash
# Restart server with CORS explicitly enabled (it's on by default):
uv run pumaguard-webui --host 0.0.0.0
```

## Testing Steps

To verify the camera URL feature works:

### 1. Test Backend API

```bash
# Start server:
uv run pumaguard-webui --host 0.0.0.0

# In another terminal, test the endpoint:
curl http://localhost:5000/api/camera/url

# Expected output:
# {"camera_url":""}  (if not configured)
# or
# {"camera_url":"http://192.168.52.96"}  (if configured)
```

### 2. Test Settings Update

```bash
# Update settings via API:
curl -X PUT http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"camera-url":"http://192.168.52.96"}'

# Verify it was saved:
curl http://localhost:5000/api/camera/url

# Check the settings file:
cat ~/.config/pumaguard/pumaguard-settings.yaml | grep camera-url
```

### 3. Test UI

1. Open PumaGuard web UI: `http://pumaguard.local:5000` or `http://192.168.51.104:5000`
2. Go to Settings
3. Enter camera URL: `192.168.52.96`
4. Wait for "Settings saved successfully" message
5. Go back to home
6. Click Camera button
7. Camera web interface should open in new tab

## Network Discovery Tips

If you don't know your camera's IP address:

### Method 1: nmap (most detailed)
```bash
# Install nmap:
sudo apt-get install nmap

# Scan for common camera ports:
sudo nmap -p 80,443,554,8000,8080 192.168.52.0/24

# Look for devices with ports 80 (HTTP) and 554 (RTSP) open
```

### Method 2: arp-scan (fastest)
```bash
# Install arp-scan:
sudo apt-get install arp-scan

# Scan local network:
sudo arp-scan --localnet

# Look for manufacturer name matching your camera brand
```

### Method 3: Router DHCP leases
1. Log into router admin interface
2. Look for "DHCP Clients" or "Connected Devices"
3. Find device with camera's hostname or MAC address

### Method 4: Check camera for IP display
Many cameras have:
- LCD screen showing IP address
- Mobile app that shows IP
- Reset button that announces IP via speaker

## Advanced Debugging

### Enable Python Debug Logging

```python
# Temporarily edit pumaguard/web_ui.py
# Add at the top after imports:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Network Connectivity

```bash
# From PumaGuard server, verify camera is reachable:
ping -c 4 192.168.52.96

# Check specific port:
nc -zv 192.168.52.96 80

# Or using telnet:
telnet 192.168.52.96 80
```

### Inspect Settings File

```bash
# View full settings:
cat ~/.config/pumaguard/pumaguard-settings.yaml

# Check specifically for camera-url:
grep -i camera ~/.config/pumaguard/pumaguard-settings.yaml

# Check file permissions:
ls -la ~/.config/pumaguard/pumaguard-settings.yaml

# Should be readable/writable by your user
```

### Test URL Launcher

The Flutter app uses `url_launcher` package. If camera button doesn't work:

1. Check if `url_launcher` is installed:
   ```bash
   cd pumaguard-ui
   flutter pub deps | grep url_launcher
   ```

2. Test with a known-good URL:
   - Temporarily change camera URL to `http://google.com`
   - Click Camera button
   - If Google opens, the URL launcher works
   - Problem is with camera URL or camera itself

## Still Having Issues?

If none of these solutions work:

1. **Collect debug information:**
   ```bash
   # Server info:
   uv run pumaguard --version
   
   # Settings file:
   cat ~/.config/pumaguard/pumaguard-settings.yaml
   
   # Network interfaces:
   ip addr show
   
   # Can you reach the camera?
   ping -c 4 CAMERA_IP
   curl -I http://CAMERA_IP
   ```

2. **Check GitHub issues**: Search for similar problems at https://github.com/nrb/pumaguard/issues

3. **Create an issue** with:
   - PumaGuard version
   - Error messages from browser console (F12)
   - Error messages from server logs
   - Network configuration (server IP, camera IP)
   - Camera make/model

## Related Documentation

- [Camera Integration Guide](CAMERA_INTEGRATION.md) - Feature overview and setup
- [mDNS Setup](MDNS_SETUP.md) - Network discovery configuration
- [API Reference](API_REFERENCE.md) - API endpoint specifications