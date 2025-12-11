# Camera Integration

This document describes the camera URL integration feature that allows users to quickly access their security camera's web interface from the PumaGuard UI.

## Overview

The camera URL feature provides a convenient way to open your security camera's web interface in a new browser tab directly from the PumaGuard home screen. This is particularly useful when you want to:

- Quickly check the camera's live feed
- Access camera settings
- Review camera-specific features
- Verify camera connectivity

## Architecture

The feature consists of three main components:

### 1. Backend (Python)

**Settings Storage (`pumaguard/presets.py`)**
- Added `camera_url` field to the `Preset` class
- Stored in YAML settings file as `camera-url`
- Default value: empty string (`""`)

**API Endpoint (`pumaguard/web_routes/settings.py`)**
- New endpoint: `GET /api/camera/url`
- Returns: `{"camera_url": "http://192.168.1.100"}`
- The `camera-url` setting is also included in the general settings endpoints:
  - `GET /api/settings` - retrieves all settings including camera URL
  - `PUT /api/settings` - updates settings including camera URL

### 2. Frontend (Flutter)

**Data Model (`pumaguard-ui/lib/models/settings.dart`)**
- Added `cameraUrl` field to `Settings` class
- Serialized to/from JSON as `camera-url`
- Included in `copyWith()` method for immutable updates

**API Service (`pumaguard-ui/lib/services/api_service.dart`)**
- New method: `Future<String> getCameraUrl()`
- Calls `GET /api/camera/url` endpoint
- Returns camera URL string or empty string if not configured

**UI Components**
- **Settings Screen** (`pumaguard-ui/lib/screens/settings_screen.dart`):
  - Camera URL text field in "System Settings" section
  - Auto-saves after 1 second of no typing (debounced)
  - Accepts IP addresses, hostnames, or full URLs
  
- **Home Screen** (`pumaguard-ui/lib/screens/home_screen.dart`):
  - "Camera" button in Quick Actions section
  - Opens camera URL in external browser/tab
  - Shows helpful error messages if URL not configured

### 3. Dependencies

**Added to `pubspec.yaml`:**
```yaml
url_launcher: ^6.3.0
```

This package enables opening URLs in the system's default browser across all platforms (web, mobile, desktop).

## Configuration

### Setting the Camera URL

1. Navigate to **Settings** screen from the home page
2. Scroll to the **System Settings** section
3. Enter your camera's URL in the **Camera URL** field

**Accepted formats:**
- IP address only: `192.168.52.96`
- IP with port: `192.168.52.96:8080`
- Full URL: `http://192.168.52.96`
- Hostname: `camera.local`
- HTTPS: `https://camera.example.com`

**Notes:**
- If you don't specify a protocol (`http://` or `https://`), the system will automatically add `http://`
- The setting auto-saves after you stop typing for 1 second
- Leave blank if you don't have a camera or don't want this feature

### Using the Camera Button

1. From the home screen, click the **Camera** button in the Quick Actions section
2. The camera's web interface will open in a new browser tab/window
3. If the URL is not configured, you'll see a message prompting you to set it in Settings

## Network Discovery

### Why Not mDNS?

While PumaGuard itself uses mDNS (as `pumaguard.local`), many security cameras do not advertise themselves via mDNS/Zeroconf. Therefore, this feature requires manual configuration of the camera URL.

### Finding Your Camera's IP Address

If your camera has a dynamic IP (DHCP), you can find it using:

**1. Network Scan with `nmap`:**
```bash
# Scan your network (adjust IP range)
sudo nmap -p 80,443,554,8000,8080 192.168.1.0/24
```

**2. ARP Scan:**
```bash
sudo apt-get install arp-scan
sudo arp-scan --localnet
```

**3. Check Router's DHCP Leases:**
Most routers have a web interface showing connected devices and their IP addresses.

**4. Use Avahi/mDNS (if camera supports it):**
```bash
avahi-browse -art
```

### Recommended: DHCP Reservation

To prevent the camera URL from becoming invalid when the camera's IP changes, configure a **DHCP reservation** (also called "static DHCP") in your router:

1. Find your camera's MAC address (from router or camera label)
2. Log into your router's admin interface
3. Navigate to DHCP settings
4. Create a reservation mapping the camera's MAC address to a fixed IP
5. Configure PumaGuard with this fixed IP address

**Example:**
- Camera MAC: `2C:C3:E6:0A:54:53`
- Reserved IP: `192.168.1.100`
- PumaGuard Setting: `http://192.168.1.100`

## Technical Details

### URL Handling

The home screen's `_openCamera()` method:

1. Fetches the camera URL from the API
2. Validates that it's not empty
3. Adds `http://` prefix if no protocol specified
4. Parses the URL to ensure it's valid
5. Uses `url_launcher` to open in external browser
6. Shows appropriate error messages if anything fails

### Security Considerations

- Camera URLs are stored in the settings file (`~/.config/pumaguard/pumaguard-settings.yaml`)
- No authentication credentials are stored by PumaGuard
- The camera's own authentication is handled by the camera's web interface
- URLs are opened in the system's default browser, using its security context

### Cross-Platform Behavior

The `url_launcher` package handles platform-specific behaviors:

- **Web**: Opens in new browser tab
- **Desktop**: Opens in default system browser
- **Mobile**: Opens in external browser app
- **Android Emulator**: Use IP `10.0.2.2` to access host machine's localhost

## Example Configuration

### Camera on Same Network as PumaGuard

If both PumaGuard and the camera are on `192.168.52.x`:

```yaml
# ~/.config/pumaguard/pumaguard-settings.yaml
camera-url: "http://192.168.52.96"
```

### Camera with Custom Port

If your camera uses port 8080:

```yaml
camera-url: "http://192.168.1.100:8080"
```

### Camera with Hostname

If you've configured DNS or `/etc/hosts`:

```yaml
camera-url: "http://security-camera.local"
```

## Troubleshooting

### "Camera URL not configured" message

**Solution:** Go to Settings → System Settings → enter your camera's IP address or URL

### "Could not open camera URL" error

**Possible causes:**
1. Invalid URL format
2. Camera is offline
3. IP address changed (if using DHCP without reservation)
4. Port is incorrect (try 80, 8080, or 443)

**Solution:** 
- Verify the camera is accessible: `ping <camera-ip>`
- Check camera is on correct port: `curl http://<camera-ip>:80`
- Update the URL in Settings if it changed

### Camera works but URL opens to wrong page

Some cameras use different URLs for different features:
- Main interface: `http://camera-ip/`
- Live view: `http://camera-ip/live`
- Settings: `http://camera-ip/admin`

You can configure the exact path you want in the Camera URL setting.

## Future Enhancements

Potential improvements for future versions:

1. **Auto-discovery**: Background scanning for cameras on the network
2. **Multiple cameras**: Support for multiple camera URLs with dropdown selector
3. **Embedded view**: Display camera feed directly in PumaGuard UI
4. **Camera integration**: Automatically pull images from camera's RTSP stream
5. **Camera status**: Show online/offline status on home screen

## Related Documentation

- [mDNS Setup Guide](MDNS_SETUP.md) - For PumaGuard's own mDNS configuration
- [Web UI Structure](WEB_UI_STRUCTURE.md) - For understanding the UI architecture
- [API Reference](API_REFERENCE.md) - For all API endpoint specifications

## Testing

To test the camera integration:

1. **Backend test** (Python):
   ```bash
   # Verify settings are saved/loaded correctly
   make test
   ```

2. **Frontend test** (Flutter):
   ```bash
   cd pumaguard-ui
   flutter analyze  # Check for code issues
   flutter test     # Run unit tests
   ```

3. **Integration test**:
   ```bash
   # Start backend with test camera URL
   uv run pumaguard-webui --host 0.0.0.0
   
   # In another terminal, start Flutter dev server
   cd pumaguard-ui
   flutter run -d chrome
   
   # Test: Set camera URL → Click Camera button → Verify it opens
   ```

## Code Locations

**Backend:**
- Settings model: `pumaguard/pumaguard/presets.py` (line ~148)
- API endpoint: `pumaguard/pumaguard/web_routes/settings.py` (line ~328)

**Frontend:**
- Data model: `pumaguard-ui/lib/models/settings.dart`
- API service: `pumaguard-ui/lib/services/api_service.dart` (line ~471)
- Camera button: `pumaguard-ui/lib/screens/home_screen.dart` (line ~218)
- Settings field: `pumaguard-ui/lib/screens/settings_screen.dart` (line ~846)

**Dependencies:**
- `pumaguard-ui/pubspec.yaml` - Added `url_launcher: ^6.3.0`
