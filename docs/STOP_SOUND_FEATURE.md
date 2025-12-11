# Stop Sound Feature

This document describes the "Stop Sound" feature that allows users to interrupt long sound test playback in the PumaGuard Web UI.

## Overview

When testing deterrent sounds through the Web UI, some sound files can be quite long (30+ seconds). The Stop Sound feature allows users to interrupt playback at any time without waiting for the entire sound file to finish.

## User Interface

### Location
Settings → Sound Settings → Test/Stop Sound Buttons

### Visual Layout
```
[▶ Test Sound]  [⏹ Stop Sound]
```

- **Test Sound Button**: Starts playback (left button)
  - Disabled while sound is playing
  - Shows spinner during playback
  - Green success message on start

- **Stop Sound Button**: Stops playback (right button)
  - Enabled only while sound is playing
  - Orange color scheme
  - Orange confirmation message on stop

### Behavior

1. **Starting Test**: Click "Test Sound"
   - Button shows spinner
   - "Sound test started" snackbar appears
   - "Stop Sound" button becomes enabled
   - UI polls sound status every 500ms

2. **Stopping Test**: Click "Stop Sound"
   - Playback immediately stops
   - "Sound stopped" snackbar appears
   - Both buttons return to normal state

3. **Automatic Completion**:
   - If sound finishes naturally, buttons return to normal state
   - UI detects completion through status polling

## Technical Implementation

### Backend (Python)

#### New Functions in `pumaguard/sound.py`

```python
playsound(soundfile: str, volume: int = 80, blocking: bool = True)
```
- Added `blocking` parameter
- When `blocking=False`, returns immediately after starting playback
- Tracks process globally for control

```python
stop_sound() -> bool
```
- Terminates currently playing sound process
- Returns `True` if a sound was stopped
- Handles cleanup of terminated process

```python
is_playing() -> bool
```
- Checks if sound is currently playing
- Returns `True` if process is active
- Auto-cleans up finished processes

#### Implementation Details

- Uses `subprocess.Popen` instead of `subprocess.run` for process control
- Global `_current_process` variable tracks active playback
- Thread-safe with `threading.Lock`
- Graceful termination with fallback to kill

#### New API Endpoints

**POST `/api/settings/test-sound`**
- Now starts sound in non-blocking mode
- Returns immediately after starting playback
- Response: `{"success": true, "message": "Sound started: filename.mp3"}`

**POST `/api/settings/stop-sound`**
- Stops currently playing sound
- Response: `{"success": true, "message": "Sound stopped"}`

**GET `/api/settings/sound-status`**
- Checks if sound is currently playing
- Response: `{"playing": true|false}`

### Frontend (Flutter)

#### New Methods in `lib/services/api_service.dart`

```dart
Future<bool> stopSound()
```
- Calls `/api/settings/stop-sound` endpoint
- Returns `true` on success

```dart
Future<bool> getSoundStatus()
```
- Calls `/api/settings/sound-status` endpoint
- Returns `true` if sound is playing

#### Updated Methods in `lib/screens/settings_screen.dart`

```dart
Future<void> _testSound()
```
- Starts non-blocking sound playback
- Polls status every 500ms
- Automatically updates UI when sound finishes

```dart
Future<void> _stopSound()
```
- Stops sound playback
- Shows confirmation snackbar
- Updates UI state

#### UI State Management

- `_isTestingSound`: Boolean flag for button states
- Enables "Stop" button only while playing
- Disables "Test" button while playing
- Status polling loop checks for completion

## Usage Examples

### API Examples

**Start sound test:**
```bash
curl -X POST http://localhost:5000/api/settings/test-sound
```

**Stop sound:**
```bash
curl -X POST http://localhost:5000/api/settings/stop-sound
```

**Check status:**
```bash
curl http://localhost:5000/api/settings/sound-status
```

### Python Examples

```python
from pumaguard.sound import playsound, stop_sound, is_playing

# Non-blocking playback
playsound("sound.mp3", volume=80, blocking=False)

# Check if playing
if is_playing():
    print("Sound is playing")

# Stop playback
if stop_sound():
    print("Sound stopped")
```

## Process Management

### Sound Playback Process

1. **Start**: `Popen(['mpg123', '-o', 'alsa', '-f', volume, file])`
2. **Track**: Store process in global `_current_process`
3. **Stop**: Call `terminate()` then `wait(timeout=1)`
4. **Fallback**: Call `kill()` if terminate fails
5. **Cleanup**: Set `_current_process = None`

### Thread Safety

All process operations are protected by `_process_lock`:
- Starting new playback
- Stopping playback
- Checking status
- Cleaning up finished processes

## Error Handling

### Backend

- `subprocess.SubprocessError`: Caught when starting/stopping fails
- `ProcessLookupError`: Ignored during cleanup (process already gone)
- `TimeoutExpired`: Falls back to `kill()` if `terminate()` times out

### Frontend

- Network errors: Shows red error snackbar
- API errors: Displays error message from backend
- Status polling: Silently handles errors, assumes not playing

## Benefits

1. **User Control**: Stop long sounds immediately
2. **Better UX**: No waiting for completion
3. **Quick Testing**: Test multiple sounds rapidly
4. **Non-Blocking**: UI remains responsive during playback
5. **Safe**: Proper process cleanup prevents zombies

## Known Limitations

1. **Single Sound**: Only one sound can play at a time
2. **Test Only**: Stop feature only for test playback, not detection alerts
3. **Polling Overhead**: Status checks every 500ms during playback
4. **Process Management**: Relies on OS process signals

## Future Enhancements

Possible improvements:
- WebSocket for real-time status updates (no polling)
- Queue multiple sounds for testing
- Volume adjustment during playback
- Waveform visualization
- Playback progress bar
- Looping/repeat options

## Troubleshooting

### Sound Won't Stop

1. Check mpg123 process: `ps aux | grep mpg123`
2. Manually kill if needed: `pkill mpg123`
3. Check PumaGuard logs for errors
4. Verify mpg123 supports signals on your system

### Button Not Enabling

1. Check browser console for errors
2. Verify API endpoint is reachable
3. Check network tab in browser dev tools
4. Ensure sound actually started playing

### Status Polling Issues

1. Check `/api/settings/sound-status` endpoint
2. Verify network connectivity
3. Check for CORS issues
4. Monitor console for polling errors

## Version History

- **v20.post235**: Initial stop sound implementation
  - Added non-blocking playback mode
  - Added stop and status API endpoints
  - Added Stop Sound button to UI
  - Implemented status polling

## See Also

- [Volume Control Feature](VOLUME_CONTROL.md)
- [Sound Module](../pumaguard/sound.py)
- [Settings API](../pumaguard/web_routes/settings.py)
- [API Service](../../pumaguard-ui/lib/services/api_service.dart)