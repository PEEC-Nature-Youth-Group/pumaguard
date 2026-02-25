# Configurable Puma Detection Threshold

## Overview

PumaGuard now supports a configurable classification threshold for puma detection. Previously, the threshold was hardcoded to 0.5 (50%), meaning any image classified with >50% confidence as containing a puma would trigger detection actions (sound playback, automatic plug control, etc.). This threshold is now fully configurable through the web UI and REST API, allowing users to adjust sensitivity based on their specific needs.

## Default Value

The default threshold is **0.5** (50% confidence), maintaining backward compatibility with previous behavior.

## Why Make This Configurable?

Different deployment scenarios may require different sensitivity levels:

- **Higher Threshold (0.7-0.9)**: Reduces false positives in areas with similar-looking animals or challenging lighting conditions
- **Lower Threshold (0.3-0.4)**: Increases sensitivity in critical monitoring areas where missing a detection is worse than occasional false positives
- **Default (0.5)**: Balanced approach suitable for most deployments

## How It Works

### Classification Process

1. **YOLO Detection**: Detects potential animals in the image
2. **EfficientNet Classification**: Assigns a puma probability (0.0 to 1.0) to each detection
3. **Threshold Comparison**: If the probability exceeds `puma-threshold`, the image is classified as containing a puma
4. **Action Trigger**: Puma detections trigger configured actions (sound playback, automatic plug control, image sorting)

### Example

With `puma-threshold: 0.7`:
- Image with 0.85 probability → **Puma detected** ✓
- Image with 0.65 probability → **Not a puma** ✗
- Image with 0.72 probability → **Puma detected** ✓

## Configuration

### Web UI

The threshold can be configured in the **Settings** screen under the **Classifier Settings** section:

1. Navigate to Settings (⚙️ icon)
2. Scroll to "Classifier Settings"
3. Find "Puma Classification Threshold"
4. Enter a value between 0.0 and 1.0 (e.g., 0.7)
5. Changes are automatically saved

**UI Location:**
```
Settings Screen
  └── Classifier Settings
       └── Puma Classification Threshold
            • Label: "Puma Classification Threshold"
            • Default: 0.5
            • Range: 0.0 - 1.0
            • Helper Text: "Confidence threshold for puma detection (0.0 - 1.0)"
```

### REST API

#### Get Current Threshold

```bash
curl http://localhost:5000/api/settings | jq '.["puma-threshold"]'
```

**Response:**
```json
0.5
```

#### Update Threshold

```bash
curl -X PUT http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"puma-threshold": 0.7}'
```

**Response:**
```json
{
  "success": true,
  "message": "Settings updated and saved"
}
```

### Settings File (YAML)

The threshold is persisted in the settings file:

**Location:**
- XDG: `~/.config/pumaguard/pumaguard-settings.yaml`
- Snap: `$SNAP_USER_DATA/pumaguard/pumaguard-settings.yaml`

**Format:**
```yaml
puma-threshold: 0.7
YOLO-min-size: 0.02
YOLO-conf-thresh: 0.15
# ... other settings
```

## Validation

The threshold value is validated both in the backend and frontend:

### Python (Backend)

```python
@puma_threshold.setter
def puma_threshold(self, puma_threshold: float):
    if not isinstance(puma_threshold, (float, int)):
        raise TypeError("puma_threshold needs to be a floating point number")
    if puma_threshold <= 0 or puma_threshold > 1:
        raise ValueError("puma_threshold needs to be between (0, 1]")
    self._puma_threshold = float(puma_threshold)
```

**Valid Range:** 0 < threshold ≤ 1.0

**Invalid Values:**
- ❌ `0.0` (must be greater than 0)
- ❌ `-0.5` (negative values not allowed)
- ❌ `1.5` (maximum is 1.0)
- ❌ `"0.5"` (must be numeric)

### Flutter (Frontend)

Input validation in the UI:
- Text field accepts decimal numbers
- Parse errors default to 0.5
- Visual feedback for invalid input

## Impact on System Behavior

### File Classification

Images are sorted into directories based on the threshold:

```
classification_root/
├── puma/          # probability > puma_threshold
└── other/         # probability ≤ puma_threshold
```

**Example with threshold 0.7:**
```
Image with 0.85 probability → classified_puma_dir/
Image with 0.65 probability → classified_other_dir/
Image with 0.40 probability → classified_other_dir/
```

### Automatic Plug Control

Smart plugs in "automatic" mode are controlled based on the threshold:

```python
if prediction > self.presets.puma_threshold:
    # Turn on automatic plugs
    # Play deterrent sound
    # Turn off automatic plugs
```

**Impact:**
- **Higher threshold**: Fewer plug activations (only high-confidence detections)
- **Lower threshold**: More plug activations (includes lower-confidence detections)

### Sound Playback

Deterrent sounds are played only when detection exceeds the threshold:

```python
if prediction > self.presets.puma_threshold:
    if self.presets.play_sound:
        playsound(sound_file_path, self.presets.volume)
```

### Logging

Log messages reflect the threshold:

```
INFO: Chance of puma in image.jpg: 68.50%
INFO: Puma detected in image.jpg  # Only if 68.50% > puma_threshold
```

## Choosing the Right Threshold

### Conservative (0.7 - 0.9)

**Use When:**
- Frequent false positives from similar animals (bobcats, coyotes)
- Deterrents are disruptive (loud sounds, bright lights)
- Monitoring urban/suburban areas with pets

**Trade-offs:**
- ✅ Fewer false positives
- ❌ May miss some actual pumas

**Recommended For:**
- Residential areas
- Areas with domestic animals
- Noise-sensitive locations

### Balanced (0.5 - 0.7)

**Use When:**
- Standard monitoring scenarios
- Acceptable false positive rate
- General wildlife observation

**Trade-offs:**
- ✅ Good balance of sensitivity and specificity
- ✅ Works well for most deployments

**Recommended For:**
- Wildlife research
- General property monitoring
- Default deployments

### Sensitive (0.3 - 0.5)

**Use When:**
- Critical monitoring (livestock protection)
- Low puma population (rare sightings)
- Deterrents are non-disruptive

**Trade-offs:**
- ✅ Catches more potential pumas
- ❌ More false positives

**Recommended For:**
- Livestock protection
- High-value property
- Areas with confirmed puma presence

## Testing Different Thresholds

### Test Mode

Use the API to test different thresholds without affecting the saved settings:

```bash
# Test with high threshold
curl -X PUT http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"puma-threshold": 0.8}'

# Monitor classifications
tail -f ~/.cache/pumaguard/pumaguard.log

# Test with low threshold
curl -X PUT http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"puma-threshold": 0.3}'
```

### Analyze Historical Data

Review past classifications to determine optimal threshold:

```bash
# Find all puma detections with their probabilities
grep "Chance of puma" ~/.cache/pumaguard/pumaguard.log | \
  awk '{print $(NF-1)}' | \
  sort -n
```

**Example Output:**
```
35.20%
42.50%
53.80%  ← Current threshold (0.5) would catch these
68.90%
72.10%
85.40%
```

## Code Examples

### Reading Current Threshold (Python)

```python
from pumaguard.presets import Settings

presets = Settings()
presets.load("/path/to/settings.yaml")
print(f"Current threshold: {presets.puma_threshold}")
```

### Updating Threshold (Python)

```python
from pumaguard.presets import Settings

presets = Settings()
presets.puma_threshold = 0.7
presets.save()
```

### Using in Classification (Python)

```python
from pumaguard.utils import classify_image_two_stage
from pumaguard.presets import Settings

presets = Settings()
presets.puma_threshold = 0.7

probability = classify_image_two_stage(
    presets=presets,
    image_path="trail_camera_image.jpg"
)

if probability > presets.puma_threshold:
    print(f"Puma detected! Confidence: {probability:.2%}")
else:
    print(f"Not a puma. Confidence: {probability:.2%}")
```

### Flutter UI Integration

```dart
// Load current threshold
final settings = await apiService.getSettings();
print('Current threshold: ${settings.pumaThreshold}');

// Update threshold
final updatedSettings = settings.copyWith(pumaThreshold: 0.7);
await apiService.updateSettings(updatedSettings);
```

## Troubleshooting

### Threshold Not Applied

**Symptom:** Changes to threshold don't affect classifications.

**Solutions:**
1. **Verify settings were saved:**
   ```bash
   curl http://localhost:5000/api/settings | jq '.["puma-threshold"]'
   ```

2. **Restart the server:**
   ```bash
   systemctl restart pumaguard-server
   ```

3. **Check logs for errors:**
   ```bash
   tail -f ~/.cache/pumaguard/pumaguard.log | grep -i threshold
   ```

### Invalid Threshold Error

**Symptom:** API returns validation error.

**Example Error:**
```json
{
  "error": "puma_threshold needs to be between (0, 1]"
}
```

**Solutions:**
- Ensure value is between 0.0 and 1.0 (exclusive of 0, inclusive of 1)
- Use numeric value, not string: `0.7` not `"0.7"`
- Check for typos: `0.5` not `0,5` (use period, not comma)

### Too Many False Positives

**Solutions:**
- Increase threshold (e.g., from 0.5 to 0.7)
- Review YOLO confidence threshold (`YOLO-conf-thresh`)
- Check camera placement and lighting conditions

### Missing Detections

**Solutions:**
- Decrease threshold (e.g., from 0.5 to 0.4)
- Review recent log files for near-threshold classifications
- Verify camera image quality

## Performance Considerations

### Computational Impact

The threshold setting has **no impact on performance**:
- Classification speed is unchanged
- Memory usage is unchanged
- Only affects the decision logic after classification

### Storage Impact

Lower thresholds may result in:
- More images in `classified_puma_dir/`
- More intermediate visualization files
- Increased disk usage over time

## Security & Safety

### Recommended Practices

1. **Start Conservative**: Begin with higher threshold (0.7) and adjust down if needed
2. **Monitor Logs**: Review classifications regularly to tune threshold
3. **Test Thoroughly**: Use test images to verify threshold behavior
4. **Document Changes**: Keep records of threshold changes and their effects

### Access Control

The threshold can be modified by:
- ✅ Web UI users (no authentication by default)
- ✅ REST API clients
- ✅ Direct YAML file editing

**Production Deployment:** Consider adding authentication to prevent unauthorized threshold changes.

## Related Documentation

- [API Reference](API_REFERENCE.md) - Full REST API documentation
- [Settings Persistence](SETTINGS_PERSISTENCE.md) - How settings are stored and loaded
- [Automatic Plug Control](../pumaguard/AUTOMATIC_PLUG_CONTROL.md) - How threshold affects plug control
- [Build Reference](BUILD_REFERENCE.md) - Building the Flutter UI with new threshold field

## Version History

- **v22.x**: Introduced configurable puma threshold (previously hardcoded to 0.5)
- **v21.x and earlier**: Threshold was hardcoded to 0.5 (not configurable)

## Future Enhancements

Potential improvements for consideration:

1. **Time-Based Thresholds**: Different thresholds for day vs. night
2. **Adaptive Thresholds**: Automatically adjust based on detection patterns
3. **Per-Camera Thresholds**: Different thresholds for different camera locations
4. **Threshold Presets**: Quick-select common threshold values (Conservative/Balanced/Sensitive)
5. **Visual Threshold Editor**: Graphical slider in UI with real-time preview
6. **Historical Analysis**: Show detection counts at different threshold levels

## Support

For questions or issues related to the puma threshold feature:

1. Check this documentation
2. Review logs: `~/.cache/pumaguard/pumaguard.log`
3. Test with known images to verify behavior
4. File an issue on GitHub with threshold value and observed behavior