# Quick Reference: Truncated Image Tests

## What Was Added

Two new tests to verify robust handling of incomplete/corrupted image files:

### 1. `test_wait_for_file_stability_truncated_image` ✅
Tests that the system **retries** when encountering truncated images and succeeds once complete.

**Real-world scenario**: Camera uploading image over slow network

### 2. `test_wait_for_file_stability_permanently_truncated` ✅  
Tests that the system **times out gracefully** when files remain corrupted.

**Real-world scenario**: Corrupted file that will never complete

## Quick Test

```bash
# Run the new tests
pytest tests/test_server.py -k "truncated" -v

# See demonstration
python tests/example_truncated_test.py
```

## Expected Behavior

### Complete Image
```
PIL.Image.open(file) → SUCCESS
Returns: converted RGB image
```

### Truncated Image (First Attempt)
```
PIL.Image.open(file) → OSError: "image file is truncated"
Action: Sleep and retry
```

### Truncated Image (After Retry)
```
PIL.Image.open(file) → SUCCESS  
Returns: converted RGB image
```

### Permanently Corrupted
```
PIL.Image.open(file) → OSError (repeated)
After timeout → Returns: None
Logs: "File X is still open after Y seconds"
```

## Code Location

- **Implementation**: `pumaguard/pumaguard/server.py` (lines 100-135)
- **Tests**: `pumaguard/tests/test_server.py` (lines 187-254)
- **Docs**: `pumaguard/tests/TRUNCATED_IMAGE_TESTS.md`

## Parameters

```python
_wait_for_file_stability(
    filepath: str,
    timeout: int = 30,      # Max seconds to wait
    interval: float = 0.5   # Seconds between retries
)
```

## Common Errors Caught

- `OSError: image file is truncated`
- `OSError: broken data stream`
- `FileNotFoundError: file doesn't exist`
- `SyntaxError: broken PNG file`

## Test Results

```
✅ test_wait_for_file_stability_truncated_image PASSED
✅ test_wait_for_file_stability_permanently_truncated PASSED
✅ All 28 tests passing
```

## Why This Matters

Camera trap systems often deal with:
- Slow SD card writes
- Network file transfers
- FTP uploads
- Cloud sync operations
- Storage corruption

These tests ensure PumaGuard handles these situations gracefully without crashing or hanging.
