# Settings Persistence in PumaGuard

## Overview

This document explains how settings are managed, persisted, and synchronized between the Flutter web UI and the Python backend.

## How Settings Work

### Backend (Python)

Settings are managed by the `Preset` class in `pumaguard/presets.py`:

- **In-Memory**: Settings are stored as Python object attributes (e.g., `yolo_min_size`)
- **On-Disk**: Settings are saved to YAML files (e.g., `model_settings_1_undefined_128_128.yaml`)
- **Format**: Uses hyphenated names in YAML/API (e.g., `YOLO-min-size`) but underscored Python attributes (e.g., `yolo_min_size`)

### Frontend (Flutter)

Settings are managed through the `ApiService` and `SettingsScreen`:

- **Loading**: Fetches current settings via `GET /api/settings`
- **Editing**: User modifies values in the UI
- **Saving**: Sends all settings via `PUT /api/settings`
- **Automatic Persistence**: Backend automatically saves to disk after updating

## API Endpoints

### GET /api/settings

Returns all current settings as JSON.

**Request:**
```http
GET /api/settings HTTP/1.1
```

**Response:**
```json
{
  "YOLO-min-size": 0.02,
  "YOLO-conf-thresh": 0.25,
  "YOLO-max-dets": 12,
  "YOLO-model-filename": "yolov8s_101425.pt",
  "classifier-model-filename": "colorbw_111325.h5",
  "deterrent-sound-file": "deterrent_puma.mp3",
  "file-stabilization-extra-wait": 2.0,
  "play-sound": true,
  ...
}
```

**Notes:**
- Returns ALL fields from the `Preset` class (23+ fields)
- Some fields are read-only and cannot be updated via PUT

### PUT /api/settings

Updates settings and automatically saves them to disk.

**Request:**
```http
PUT /api/settings HTTP/1.1
Content-Type: application/json

{
  "YOLO-min-size": 0.05,
  "YOLO-conf-thresh": 0.30,
  "play-sound": true
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Settings updated and saved"
}
```

**Response (Error):**
```json
{
  "error": "Settings updated but failed to save: <error details>"
}
```

**Behavior:**
1. Updates settings in memory
2. **Automatically saves to disk** (YAML file)
3. Skips unknown/read-only fields (logs but doesn't error)
4. Returns success/error

**Allowed Settings (updatable via API):**
- `YOLO-min-size`
- `YOLO-conf-thresh`
- `YOLO-max-dets`
- `YOLO-model-filename`
- `classifier-model-filename`
- `deterrent-sound-file` (deprecated, use `deterrent-sound-files`)
- `deterrent-sound-files` (list of sound filenames)
- `file-stabilization-extra-wait`
- `play-sound`
- `volume` (0-100)
- `camera-url`

### POST /api/settings/save

Explicitly saves current settings to a specific file (rarely needed).

**Request:**
```http
POST /api/settings/save HTTP/1.1
Content-Type: application/json

{
  "filepath": "/path/to/settings.yaml"
}
```

**Response:**
```json
{
  "success": true,
  "filepath": "/path/to/settings.yaml"
}
```

**Notes:**
- If no filepath provided, uses default settings file
- Typically not needed since PUT auto-saves

### POST /api/settings/load

Loads settings from a specific YAML file.

**Request:**
```http
POST /api/settings/load HTTP/1.1
Content-Type: application/json

{
  "filepath": "/path/to/settings.yaml"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Settings loaded"
}
```

## Settings Persistence Flow

### User Changes a Setting

```
User edits value in Flutter UI
    ↓
User clicks "Save Settings"
    ↓
Flutter calls apiService.updateSettings(allSettings)
    ↓
PUT /api/settings with all fields
    ↓
Backend: For each field in allowed list:
  - Convert hyphenated name to underscored attribute
  - setattr(presets, attr_name, value)
    ↓
Backend: Save to YAML file
    ↓
Response: {"success": true, "message": "Settings updated and saved"}
    ↓
Flutter shows success message
    ↓
User closes settings screen
    ↓
Later: User reopens settings
    ↓
Flutter calls GET /api/settings
    ↓
Backend returns current values (from memory, which match disk)
    ↓
Flutter displays updated values ✓
```

## Name Conversion

The API uses hyphenated names, but Python uses underscored names.

**Conversion Rules:**

```python
# API name → Python attribute name
"YOLO-min-size" → "yolo_min_size"
"YOLO-conf-thresh" → "yolo_conf_thresh"
"classifier-model-filename" → "classifier_model_filename"
"play-sound" → "play_sound"
```

**Implementation:**
```python
attr_name = key.replace("-", "_").replace("YOLO_", "yolo_")
setattr(self.presets, attr_name, value)
```

## Settings File Location

The default settings file location is determined by `get_default_settings_file()` in `pumaguard/presets.py`:

### Location Priority (in order):

1. **Snap Environment** (when `SNAP_USER_DATA` is set):
   ```
   $SNAP_USER_DATA/pumaguard/settings.yaml
   ```
   Used when running as a snap with strict confinement to ensure the app has write access.

2. **XDG Config Home** (standard Linux):
   ```
   $XDG_CONFIG_HOME/pumaguard/settings.yaml
   (typically ~/.config/pumaguard/settings.yaml)
   ```

3. **Legacy Location** (backwards compatibility):
   ```
   ./pumaguard-settings.yaml
   (in current directory)
   ```

### Model-Specific Settings

The model-specific settings file path is determined by:

```python
@property
def settings_file(self):
    return os.path.realpath(
        f"{self.base_output_directory}/"
        f"model_settings_{self.notebook_number}_{self.model_version}"
        f"_{self.image_dimensions[0]}_{self.image_dimensions[1]}.yaml"
    )
```

**Example:**
```
/path/to/pumaguard-models/model_settings_1_undefined_128_128.yaml
```

### Snap Confinement Note

When running as a snap, the app uses `$SNAP_USER_DATA/pumaguard/` for settings storage because strict confinement prevents access to standard XDG locations like `~/.config`. The snap environment automatically sets `SNAP_USER_DATA` to a writable location specific to the snap.

## Flutter UI Implementation

### Loading Settings

```dart
Future<void> _loadSettings() async {
  final apiService = context.read<ApiService>();
  final settings = await apiService.getSettings();
  
  setState(() {
    _settings = settings;
    // Populate text controllers with values
    _yoloMinSizeController.text = settings.yoloMinSize.toString();
    // ... etc
  });
}
```

### Saving Settings

```dart
Future<void> _saveSettings() async {
  final updatedSettings = Settings(
    yoloMinSize: double.tryParse(_yoloMinSizeController.text) ?? 0.01,
    yoloConfThresh: double.tryParse(_yoloConfThreshController.text) ?? 0.25,
    // ... gather all values from UI
  );
  
  final apiService = context.read<ApiService>();
  await apiService.updateSettings(updatedSettings);
  
  // Backend automatically saves to disk - no need for separate save call
  
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('Settings saved successfully')),
  );
}
```

## Troubleshooting

### Settings Don't Persist

**Symptom:** Changes revert when reopening settings page.

**Causes & Solutions:**

1. **Backend not auto-saving** (fixed in recent version)
   - Update to latest version where PUT auto-saves
   - Or manually call `POST /api/settings/save`

2. **File write permissions**
   - Check that the backend has write access to settings directory
   - Check logs for "Error saving settings" messages

3. **Settings file not being loaded on startup**
   - Verify the settings file path
   - Check if file exists: `ls -la pumaguard-models/model_settings_*.yaml`

### "Unknown setting" Error

**Symptom:** API returns error about unknown settings.

**Cause:** Sending fields that aren't in the allowed list.

**Solution (Fixed):** Backend now skips unknown fields instead of erroring.

### Value Not Updating

**Symptom:** PUT returns success but value doesn't change.

**Causes:**
1. **Name mismatch** (fixed) - hyphenated vs underscored
2. **Type validation failure** - check Preset property validators
3. **Out of range** - e.g., yolo_min_size must be between 0 and 1

**Check logs:**
```bash
# Look for validation errors
tail -f /var/log/pumaguard/web_ui.log | grep -i error
```

### Changes Lost After Server Restart

**Symptom:** Settings revert after restarting the server.

**Cause:** Settings file wasn't saved before restart.

**Solutions:**
- Ensure PUT endpoint is saving (should auto-save in current version)
- Manually save: Call `POST /api/settings/save`
- Check file modification time: `ls -l pumaguard-models/model_settings_*.yaml`

## Validation Rules

Settings have validation rules in the `Preset` class:

```python
@yolo_min_size.setter
def yolo_min_size(self, value: float):
    if not isinstance(value, float):
        raise TypeError("needs to be a floating point number")
    if value <= 0 or value > 1:
        raise ValueError("needs to be between (0, 1]")
    self._yolo_min_size = value
```

**Valid Ranges:**
- `yolo_min_size`: 0 < x ≤ 1
- `yolo_conf_thresh`: 0 < x ≤ 1
- `yolo_max_dets`: positive integer
- `file_stabilization_extra_wait`: positive number

## Development Notes

### Testing Settings Persistence

```python
# Test script
from pumaguard.web_ui import WebUI
from pumaguard.presets import Preset
import requests

presets = Preset()
web_ui = WebUI(presets=presets, host='127.0.0.1', port=5000)
web_ui.start()

# Get current
resp = requests.get('http://127.0.0.1:5000/api/settings')
settings = resp.json()

# Modify
settings['YOLO-min-size'] = 0.05

# Save
resp = requests.put('http://127.0.0.1:5000/api/settings', json=settings)
print(resp.json())

# Verify
resp = requests.get('http://127.0.0.1:5000/api/settings')
assert resp.json()['YOLO-min-size'] == 0.05

web_ui.stop()
```

### Adding New Settings

To add a new setting to the API:

1. **Add property to `Preset` class** (`pumaguard/presets.py`):
   ```python
   @property
   def my_new_setting(self) -> str:
       return self._my_new_setting
   
   @my_new_setting.setter
   def my_new_setting(self, value: str):
       self._my_new_setting = value
   ```

2. **Add to `__iter__` method** (for serialization):
   ```python
   def __iter__(self):
       yield from {
           # ... existing settings
           "my-new-setting": self.my_new_setting,
       }
   ```

3. **Add to allowed_settings list** in `web_ui.py`:
   ```python
   allowed_settings = [
       # ... existing settings
       "my-new-setting",
   ]
   ```

4. **Add to Flutter `Settings` model** (`lib/models/settings.dart`):
   ```dart
   class Settings {
       final String myNewSetting;
       // ... constructor, fromJson, toJson
   }
   ```

5. **Add UI controls** in `settings_screen.dart`

## Best Practices

1. **Always send all fields** when calling PUT - backend will skip read-only ones
2. **Check return value** - if error, show user the error message
3. **Validate in UI** - don't wait for backend validation
4. **Use default values** - handle parse failures gracefully
5. **Log liberally** - helps debug issues in production

## Security Considerations

- Settings file may contain sensitive paths - ensure proper file permissions
- API currently accepts any origin (CORS: *) - restrict in production
- No authentication on settings endpoints - add auth for production deployments
- Validate all input types on backend - don't trust client data

## Related Documentation

- [API Service](../pumaguard-ui/lib/services/api_service.dart)
- [Settings Screen](../pumaguard-ui/lib/screens/settings_screen.dart)
- [Preset Class](../pumaguard/presets.py)
- [Web UI Server](../pumaguard/web_ui.py)