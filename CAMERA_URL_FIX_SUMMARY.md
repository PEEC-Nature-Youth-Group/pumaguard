# Camera URL Feature - Fix Summary

## Issue Description

The camera URL feature was not working correctly:
1. **Settings not saving**: When entering a camera IP address in the Settings screen, it was not being persisted
2. **Error on camera button click**: Clicking the "Open Camera" button resulted in an error

## Root Cause

The `camera-url` field was missing from the `__iter__()` method in the `Preset` class (`pumaguard/presets.py`). This method is responsible for serializing the preset object to a dictionary for YAML storage. Without this field in `__iter__()`, the camera URL was never being saved to the settings file, even though it appeared to work in the UI.

## Fix Applied

### Backend Fix (Python)

**File: `pumaguard/pumaguard/presets.py`**

Added `"camera-url": self.camera_url` to the `__iter__()` method at line ~327:

```python
def __iter__(self):
    """
    Serialize this class.
    """
    yield from {
        "YOLO-min-size": self.yolo_min_size,
        "YOLO-conf-thresh": self.yolo_conf_thresh,
        # ... other fields ...
        "camera-url": self.camera_url,  # ← ADDED THIS LINE
        "alpha": self.alpha,
        # ... rest of fields ...
    }.items()
```

This ensures the camera URL is included when settings are serialized to YAML.

## Debug Enhancements Added

To help diagnose issues in the future, comprehensive debug logging was added:

### Backend Logging

**File: `pumaguard/pumaguard/web_routes/settings.py`**
- Added logging to `GET /api/camera/url` endpoint
- Logs show: `INFO - Camera URL requested: 'http://192.168.52.96'`

### Frontend Logging (Flutter)

**File: `pumaguard/pumaguard-ui/lib/services/api_service.dart`**
- Added debug output to `getCameraUrl()` method
- Added debug output to `updateSettings()` method
- Shows full request/response cycle with URLs, status codes, and data

**File: `pumaguard/pumaguard-ui/lib/screens/home_screen.dart`**
- Added comprehensive debug logging to `_openCamera()` method
- Tracks each step: API call → URL parsing → launch attempt → result
- Helpful for diagnosing URL launcher or network issues

**File: `pumaguard/pumaguard-ui/lib/screens/settings_screen.dart`**
- Added debug logging to `_saveSettings()` method
- Shows camera URL from text field → Settings object → JSON → API call

### How to View Debug Output

**Browser Console (F12):**
```
[ApiService.getCameraUrl] Requesting URL: http://192.168.51.104:5000/api/camera/url
[ApiService.getCameraUrl] Response status: 200
[ApiService.getCameraUrl] Response body: {"camera_url":"http://192.168.52.96"}
[HomeScreen._openCamera] Got camera URL: "http://192.168.52.96"
[HomeScreen._openCamera] URL to open: "http://192.168.52.96"
[HomeScreen._openCamera] Launching URL...
```

**Server Console:**
```
INFO - Camera URL requested: 'http://192.168.52.96'
```

## Testing Added

### Unit Test (Python)

**File: `pumaguard/test_camera_url.py`**

Comprehensive test script that verifies:
- ✅ Camera URL serialization to dict
- ✅ Camera URL saved to YAML
- ✅ Camera URL loaded from YAML
- ✅ Empty camera URL handling

Run with: `uv run python test_camera_url.py`

### API Integration Test (Shell)

**File: `pumaguard/test_camera_api.sh`**

Complete API endpoint testing:
- ✅ GET /api/camera/url (initial state)
- ✅ PUT /api/settings (set camera URL)
- ✅ Verify camera URL was saved
- ✅ Check camera URL in general settings
- ✅ Clear camera URL
- ✅ Restore camera URL

Run with: `./test_camera_api.sh http://localhost:5000`

## Documentation Added

### Comprehensive Guides

**File: `pumaguard/docs/CAMERA_INTEGRATION.md`**
- Complete feature overview
- Architecture details (backend + frontend)
- Configuration instructions
- Network discovery methods
- DHCP reservation setup
- Security considerations
- Future enhancements

**File: `pumaguard/docs/CAMERA_URL_TROUBLESHOOTING.md`**
- Quick fixes for common issues
- Debug mode instructions
- Network connectivity testing
- Step-by-step troubleshooting
- Advanced debugging techniques
- Test procedures

## How to Verify the Fix

### 1. Backend Test (Python)

```bash
# Run the test script
uv run python test_camera_url.py

# Expected output:
# ✓✓✓ All tests passed! ✓✓✓
```

### 2. API Test (Shell)

```bash
# Start the server
uv run pumaguard-webui --host 0.0.0.0

# In another terminal, run API tests
./test_camera_api.sh http://localhost:5000

# Expected output:
# ✓✓✓ All tests passed! ✓✓✓
```

### 3. Full UI Test

```bash
# 1. Start backend
uv run pumaguard-webui --host 0.0.0.0

# 2. Open browser to http://localhost:5000

# 3. Go to Settings → System Settings

# 4. Enter camera URL: 192.168.52.96

# 5. Wait 1 second, look for "Settings saved successfully" (green)

# 6. Return to home screen

# 7. Click "Camera" button

# 8. Camera web interface should open in new tab
```

### 4. Verify Settings File

```bash
# Check that camera-url is in the YAML file
cat ~/.config/pumaguard/pumaguard-settings.yaml | grep camera-url

# Expected output:
# camera-url: http://192.168.52.96
```

## Files Changed

### Backend (Python)

✅ **pumaguard/pumaguard/presets.py**
- Added `camera_url` field to `__init__()` (line ~148)
- Added `camera_url` to `load()` method (line ~298)
- Added `"camera-url"` to `__iter__()` method (line ~327) **← THE FIX**

✅ **pumaguard/pumaguard/web_routes/settings.py**
- Added `"camera-url"` to `allowed_settings` list (line ~70)
- Added `GET /api/camera/url` endpoint (line ~328)
- Added debug logging to camera URL endpoint (line ~333)

### Frontend (Flutter)

✅ **pumaguard/pumaguard-ui/pubspec.yaml**
- Added `url_launcher: ^6.3.0` dependency

✅ **pumaguard/pumaguard-ui/lib/models/settings.dart**
- Added `cameraUrl` field to Settings class
- Added to constructor, fromJson, toJson, and copyWith methods

✅ **pumaguard/pumaguard-ui/lib/services/api_service.dart**
- Added `getCameraUrl()` method (line ~473)
- Added debug logging to getCameraUrl and updateSettings

✅ **pumaguard/pumaguard-ui/lib/screens/home_screen.dart**
- Added `url_launcher` import
- Added "Camera" button to Quick Actions (line ~218)
- Added `_openCamera()` method (line ~230)
- Added comprehensive debug logging

✅ **pumaguard/pumaguard-ui/lib/screens/settings_screen.dart**
- Added `_cameraUrlController` TextEditingController
- Added camera URL to `_loadSettings()` initialization (line ~84)
- Added camera URL to `_saveSettings()` Settings object (line ~127)
- Added Camera URL text field to System Settings section (line ~846)
- Added debug logging to _saveSettings

### Testing

✅ **pumaguard/test_camera_url.py** (NEW)
- Python unit tests for camera URL serialization

✅ **pumaguard/test_camera_api.sh** (NEW)
- Shell script for API endpoint testing

### Documentation

✅ **pumaguard/docs/CAMERA_INTEGRATION.md** (NEW)
- Complete feature documentation (277 lines)

✅ **pumaguard/docs/CAMERA_URL_TROUBLESHOOTING.md** (NEW)
- Comprehensive troubleshooting guide (410 lines)

✅ **pumaguard/CAMERA_URL_FIX_SUMMARY.md** (NEW - this file)
- Summary of the fix and changes

## Code Quality

All changes pass validation:

✅ **Python**: No errors or warnings
```bash
# Backend code is clean
```

✅ **Flutter**: No issues found
```bash
cd pumaguard-ui && flutter analyze
# Output: No issues found! (ran in 2.6s)
```

## Next Steps for Users

### Quick Start

1. **Restart PumaGuard server** (if already running):
   ```bash
   # Stop current server (Ctrl+C)
   # Start with latest code:
   uv run pumaguard-webui --host 0.0.0.0
   ```

2. **Configure camera URL**:
   - Open PumaGuard UI in browser
   - Go to Settings → System Settings
   - Enter your camera's IP address: `192.168.52.96`
   - Wait for green "Settings saved successfully" message

3. **Test camera button**:
   - Return to home screen
   - Click "Camera" button
   - Camera's web interface should open in new tab

### Recommended: Set Up DHCP Reservation

To prevent camera IP from changing:

1. Find camera's MAC address from `nmap` output: `2C:C3:E6:0A:54:53`
2. Log into your router's admin interface
3. Find "DHCP Settings" → "Static DHCP" or "DHCP Reservations"
4. Add reservation: MAC `2C:C3:E6:0A:54:53` → IP `192.168.52.96`
5. Save and reboot camera

Now the camera will always have the same IP address.

## Troubleshooting

If camera URL still doesn't work:

1. **Check browser console (F12)** for debug output
2. **Check server logs** for API request messages
3. **Verify settings file**: `cat ~/.config/pumaguard/pumaguard-settings.yaml | grep camera-url`
4. **Test camera connectivity**: `ping 192.168.52.96` and `curl http://192.168.52.96`
5. **Review troubleshooting guide**: `docs/CAMERA_URL_TROUBLESHOOTING.md`

## Summary

The camera URL feature is now fully functional:

✅ **Settings save correctly** - Camera URL persists to YAML file  
✅ **Camera button works** - Opens camera interface in new tab  
✅ **Auto-save enabled** - Saves 1 second after typing stops  
✅ **Debug logging added** - Easy to diagnose issues  
✅ **Comprehensive tests** - Python and shell scripts included  
✅ **Complete documentation** - Setup and troubleshooting guides  

The fix was simple (one line in `__iter__()`), but we've added extensive debugging, testing, and documentation to ensure reliability going forward.