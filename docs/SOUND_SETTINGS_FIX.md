# Sound Settings Persistence Fix

## Problem

When users selected multiple sound files in the Settings screen, their choices were not being saved to the settings file. After leaving the settings menu, all sound selections were lost.

## Root Cause

The issue was a mismatch between the Flutter UI and the Python backend:

- **Flutter UI** sends sound selections as `deterrent-sound-files` (plural, array format)
- **Backend API** only accepted `deterrent-sound-file` (singular, old format)

In `pumaguard/web_routes/settings.py`, the `allowed_settings` list contained only:
```python
allowed_settings = [
    # ...
    "deterrent-sound-file",  # Only singular form was allowed
    # ...
]
```

When the Flutter UI sent `deterrent-sound-files`, the server would log:
```
Skipping unknown/read-only setting: deterrent-sound-files
```

The setting was silently rejected and never saved to disk.

## Solution

Added `deterrent-sound-files` (plural) to the `allowed_settings` list in `pumaguard/web_routes/settings.py`:

```python
allowed_settings = [
    "YOLO-min-size",
    "YOLO-conf-thresh",
    "YOLO-max-dets",
    "YOLO-model-filename",
    "classifier-model-filename",
    "deterrent-sound-file",      # Kept for backwards compatibility
    "deterrent-sound-files",     # Added for multiple sound files
    "file-stabilization-extra-wait",
    "play-sound",
    "volume",
    "camera-url",
]
```

## Technical Details

### Data Flow

1. **User selects sounds** in Settings UI
2. **Flutter sends PUT request** to `/api/settings`:
   ```json
   {
     "deterrent-sound-files": ["sound1.mp3", "sound2.mp3", "sound3.mp3"],
     "play-sound": true,
     "volume": 80
   }
   ```
3. **Server validates** field names against `allowed_settings` list
4. **Server saves** to `~/.config/pumaguard/pumaguard-settings.yaml`:
   ```yaml
   deterrent-sound-files:
     - sound1.mp3
     - sound2.mp3
     - sound3.mp3
   ```
5. **Settings persist** across restarts

### Backwards Compatibility

The fix maintains backwards compatibility:

- **Old format** (`deterrent-sound-file`: single string) still works
- **New format** (`deterrent-sound-files`: array) now works
- **Server reads both** formats via `Settings.load()` in `presets.py`
- **Server always writes** new format via `Settings.__iter__()`

See `pumaguard/presets.py` lines 242-258 for backwards-compatible loading logic.

## Testing

### Manual Testing

1. Start the server:
   ```bash
   uv run pumaguard-webui
   ```

2. Open web UI and navigate to Settings

3. Select multiple sound files in the "Sound Settings" section

4. Click "Save Settings"

5. Refresh the page or restart the server

6. Verify sound selections persist

### Automated Testing

Existing tests in `tests/test_presets.py` verify:
- ✅ Multiple sound files can be saved
- ✅ Settings serialize correctly to YAML
- ✅ Settings load correctly from YAML
- ✅ Backwards compatibility with single file format

Run with:
```bash
uv run pytest tests/test_presets.py -k deterrent
```

## Files Changed

### Backend (Python)
- **`pumaguard/web_routes/settings.py`**: Added `deterrent-sound-files` to allowed settings (line 99)
- **`docs/API_REFERENCE.md`**: Updated documentation
- **`docs/SETTINGS_PERSISTENCE.md`**: Updated documentation

### No Frontend Changes Required
The Flutter UI was already sending the correct format (`deterrent-sound-files`). Only the backend needed fixing.

## Impact

- **Before**: Sound selections lost after leaving settings
- **After**: Sound selections persist correctly
- **Users can now**: Select multiple deterrent sounds that will play in sequence

## Related Features

This fix enables the multiple sound file feature documented in:
- Sound playback system (`pumaguard/sound.py`)
- Settings model (`pumaguard-ui/lib/models/settings.dart`)
- Multiple sound picker UI (`pumaguard-ui/lib/screens/settings_screen.dart`)

## Notes

- The singular `deterrent-sound-file` is kept in `allowed_settings` for backwards compatibility with old clients/configs
- The server's `Settings` class has always supported both formats internally
- Only the API validation layer was blocking the new format
- No database migration needed (YAML format is flexible)