# Volume Slider Fix

## Problem

The volume slider in the Web UI was moving and saving settings, but the actual sound playback volume wasn't changing. All sounds played at the same volume regardless of the slider position.

## Root Cause

The volume conversion formula was incorrect. We were using:

```python
# WRONG: Treated -32768 to 32767 as the range
mpg123_volume = int((volume / 100.0) * 65535 - 32768)
```

This resulted in:
- 0% → -32768
- 50% → 0
- 80% → 19660 (default)
- 100% → 32767

However, mpg123's `-f` flag doesn't work this way!

## The Fix

After checking the mpg123 documentation (`mpg123 --longhelp`), we found:

```
-f <n> --scale <n>        scale output samples (soft gain - based on 32768), default=32768)
```

The `-f` flag is for **soft gain scaling**, where:
- **32768 is the default/normal level (100%)**
- **0 is muted**
- Values can go higher than 32768 for amplification

The correct formula is:

```python
# CORRECT: Scale based on 32768 = 100%
mpg123_volume = int((volume / 100.0) * 32768)
```

This results in:
- 0% → 0 (muted)
- 25% → 8192 (quiet)
- 50% → 16384 (half volume)
- 75% → 24576 (reduced)
- 80% → 26214 (default)
- 100% → 32768 (normal/full)

## Changes Made

### 1. Fixed Volume Conversion (`pumaguard/sound.py`)

```python
# mpg123 -f flag scales output samples (soft gain)
# Default/normal is 32768 (100%)
# Valid range: 0 to much higher than 32768
# Convert 0-100 percentage to mpg123 scale:
# 0% = 0 (muted), 100% = 32768 (normal), 200% = 65536 (double)
# Linear scaling: mpg123_volume = (volume / 100) * 32768
mpg123_volume = int((volume / 100.0) * 32768)
```

### 2. Added Comprehensive Logging

Added logging throughout the volume workflow to help debug issues:

**In `pumaguard/sound.py`:**
- Log when `playsound()` is called with volume parameter
- Log volume conversion calculation
- Log the exact mpg123 command being executed
- Log process PID when playback starts
- Log when sound is stopped

**In `pumaguard/web_routes/settings.py`:**
- Log when volume setting is updated via API
- Log verification of volume value after setting
- Log volume value when test sound is triggered
- Include volume in saved settings log message

### 3. Updated Documentation

Updated `docs/VOLUME_CONTROL.md` with:
- Correct conversion formula
- Correct mpg123 scale values
- Explanation of soft gain scaling
- Updated examples with correct values

## Testing

### Manual Test

You can test different volumes directly with mpg123:

```bash
# Muted (0%)
mpg123 -o alsa -f 0 sound.mp3

# Quiet (25%)
mpg123 -o alsa -f 8192 sound.mp3

# Half volume (50%)
mpg123 -o alsa -f 16384 sound.mp3

# Default (80%)
mpg123 -o alsa -f 26214 sound.mp3

# Full volume (100%)
mpg123 -o alsa -f 32768 sound.mp3
```

### Log Output

With the new logging, you'll see output like:

```
INFO:pumaguard.sound:playsound called: file=/path/to/sound.mp3, volume=75, blocking=False
DEBUG:pumaguard.sound:Volume conversion: 75% -> mpg123 scale 24576
INFO:pumaguard.sound:Executing command: mpg123 -o alsa -f 24576 /path/to/sound.mp3
INFO:pumaguard.sound:Sound playback started, PID: 12345
```

And in the web routes:

```
INFO:pumaguard.web_routes.settings:Updating setting volume with value 75
INFO:pumaguard.web_routes.settings:Volume setting updated to 75, verified: 75
INFO:pumaguard.web_routes.settings:Settings updated and saved to /path/to/settings.yaml (volume: 75)
INFO:pumaguard.web_routes.settings:Testing sound playback: file=/path/to/sound.mp3, volume=75
```

## Verification Steps

1. **Deploy the fixed version** to your Raspberry Pi
2. **Open the Web UI** and go to Settings → Sound Settings
3. **Set volume to 25%** and click "Test Sound" - should be quiet
4. **Set volume to 50%** and click "Test Sound" - should be moderate
5. **Set volume to 100%** and click "Test Sound" - should be full volume
6. **Check the logs** at `/var/log/syslog` or wherever PumaGuard logs go

You should now hear clear differences in volume levels!

## Related Files

- `pumaguard/sound.py` - Volume conversion and playback
- `pumaguard/web_routes/settings.py` - API endpoint logging
- `docs/VOLUME_CONTROL.md` - User documentation
- `docs/STOP_SOUND_FEATURE.md` - Related feature docs

## Version

Fixed in: **v20.post235**

## See Also

- [mpg123 Manual](https://www.mpg123.de/api/)
- [Volume Control Feature Documentation](VOLUME_CONTROL.md)
- [Stop Sound Feature Documentation](STOP_SOUND_FEATURE.md)