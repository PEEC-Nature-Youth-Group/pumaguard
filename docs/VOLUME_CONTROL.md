# Volume Control Feature

This document describes the volume control feature for PumaGuard's deterrent sound playback.

## Overview

The volume control feature allows you to adjust the playback volume of deterrent sounds from 0% (muted) to 100% (maximum volume). The volume setting is configurable through:

1. The Web UI Settings page
2. The REST API
3. The YAML configuration file
4. Command-line tools

## Web UI

### Volume Slider

In the Settings screen, you'll find a volume slider in the "Sound Settings" section:

- **Location**: Settings → Sound Settings → Volume Slider
- **Range**: 0% to 100%
- **Default**: 80%
- **Divisions**: 20 (5% increments)

The slider provides real-time feedback with a percentage display and saves automatically when you release the slider.

### Testing Volume

Use the "Test Sound" button in the Sound Settings section to preview the configured deterrent sound at the current volume level.

## Configuration File

The volume setting is stored in your PumaGuard settings YAML file (typically `~/.config/pumaguard/settings.yaml`):

```yaml
volume: 80  # Volume level 0-100
play-sound: true
deterrent-sound-file: deterrent_puma.mp3
```

## REST API

### Get Current Volume

```bash
curl http://localhost:5000/api/settings
```

Response includes the volume setting:
```json
{
  "volume": 80,
  "play-sound": true,
  "deterrent-sound-file": "deterrent_puma.mp3"
}
```

### Update Volume

```bash
curl -X PUT http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"volume": 75}'
```

### Test Sound with Current Volume

```bash
curl -X POST http://localhost:5000/api/settings/test-sound
```

## Python API

### Using the Preset Class

```python
from pumaguard.presets import Preset

# Load settings
presets = Preset()
presets.load()

# Get current volume
print(f"Current volume: {presets.volume}%")

# Set volume
presets.volume = 75

# Save settings
presets.save()
```

### Playing Sound with Volume

```python
from pumaguard.sound import playsound

# Play at default volume (80%)
playsound("path/to/sound.mp3")

# Play at specific volume
playsound("path/to/sound.mp3", volume=50)

# Play at maximum volume
playsound("path/to/sound.mp3", volume=100)

# Mute
playsound("path/to/sound.mp3", volume=0)
```

## Command-Line Tools

### Test Volume with Script

```bash
# Test different volume levels
python -m pumaguard.scripts.test_volume

# Play specific file at specific volume
python -m pumaguard.scripts.test_volume /path/to/sound.mp3 75
```

### Using pumaguard-sound Command

```bash
# Play at default volume
pumaguard-sound /path/to/sound.mp3

# Play at specific volume
pumaguard-sound /path/to/sound.mp3 60
```

## Technical Details

### Volume Conversion

The volume control uses a 0-100 scale for user convenience, which is converted to mpg123's native format:

- **User Scale**: 0-100 (percentage)
- **mpg123 Scale**: 0 to 32768+ (soft gain scaling, 32768 = 100%)
- **Conversion Formula**: `mpg123_volume = (volume / 100) * 32768`

Examples:
- 0% → 0 (muted)
- 25% → 8192 (quiet)
- 50% → 16384 (half volume)
- 75% → 24576 (reduced)
- 80% → 26214 (default)
- 100% → 32768 (normal/full)

### mpg123 Integration

The volume is applied using mpg123's `-f` (scale) flag for soft gain:

```bash
# At 80% volume (default)
mpg123 -o alsa -f 26214 sound.mp3

# At 100% volume (normal)
mpg123 -o alsa -f 32768 sound.mp3

# At 50% volume
mpg123 -o alsa -f 16384 sound.mp3
```

The `-f` flag scales output samples, where 32768 is the normal/default level (100%).

### ALSA Integration

The volume control operates at the software level (mpg123) and is independent of ALSA mixer settings. You can still use `alsamixer` to adjust hardware volume levels separately.

## Best Practices

1. **Start at 80%**: The default volume of 80% is a good starting point for most setups
2. **Test Before Deployment**: Use the "Test Sound" button to verify volume levels before deploying
3. **Consider Environment**: Outdoor installations may need higher volume (90-100%)
4. **Combine with Hardware**: Adjust both software (PumaGuard) and hardware (ALSA) volume for optimal results
5. **Safety First**: Start with lower volumes and increase gradually to avoid startling nearby people or animals unintentionally

## Troubleshooting

### Volume Too Quiet

1. Check PumaGuard volume setting (increase to 90-100%)
2. Check ALSA mixer levels: `alsamixer`
3. Verify speaker connections and power
4. Test with a known-loud sound file

### Volume Too Loud

1. Decrease PumaGuard volume setting (try 50-60%)
2. Adjust ALSA mixer levels: `alsamixer`
3. Consider using a different deterrent sound file

### Volume Control Not Working

1. Verify mpg123 is installed: `which mpg123`
2. Check that mpg123 supports the `-f` flag: `mpg123 --longhelp | grep -- -f`
3. Test manually: `mpg123 -o alsa -f 0 sound.mp3`
4. Check PumaGuard logs for errors

### Settings Not Persisting

1. Verify settings file exists: `~/.config/pumaguard/settings.yaml`
2. Check file permissions (should be readable/writable by your user)
3. Verify the Web UI is saving: check browser console for errors
4. Manually verify in settings file after saving

## Version History

- **v20.post235**: Initial volume control implementation
  - Added volume slider to Web UI
  - Added volume property to Preset class
  - Updated playsound() to accept volume parameter
  - Added REST API support for volume setting

## See Also

- [Settings API Documentation](../pumaguard/web_routes/settings.py)
- [Sound Module](../pumaguard/sound.py)
- [Preset Class](../pumaguard/presets.py)
- [mpg123 Documentation](https://www.mpg123.de/api/)