# Truncated Image Tests Documentation

## Overview

This document describes the tests added to verify that `_wait_for_file_stability()` correctly handles truncated (incomplete) image files. These tests ensure the system is robust when dealing with files that are still being written or are corrupted.

## Test Cases

### 1. `test_wait_for_file_stability_truncated_image`

**Purpose**: Verify that the function retries when encountering a truncated image and succeeds once the file is complete.

**Scenario**:
- A JPEG file is initially written incompletely (truncated)
- On the first attempt to open, PIL raises an `OSError` indicating the file is truncated
- The function sleeps and retries
- On the second attempt, the file is complete and can be opened successfully

**Expected Behavior**:
- The function should retry opening the file
- Once the file is complete, it should return the converted image
- Should make exactly 2 attempts (1 failure + 1 success)

**Why This Matters**:
In real-world scenarios, camera trap systems or file sync operations may create files that are initially incomplete. The system needs to wait for the complete file before processing.

### 2. `test_wait_for_file_stability_permanently_truncated`

**Purpose**: Verify that the function times out gracefully when a file remains truncated/corrupted.

**Scenario**:
- A JPEG file is written with only 20 bytes (severely truncated)
- Every attempt to open the file fails with an error
- The function retries until the timeout is reached
- The file never becomes complete

**Expected Behavior**:
- The function should retry multiple times
- After the timeout expires, it should return `None`
- Should log a warning about the file being unreadable

**Why This Matters**:
Not all truncated files will eventually complete. Some may be corrupted or abandoned. The system must not hang indefinitely and should gracefully handle unrecoverable files.

## Technical Implementation Details

### Test Setup

Both tests use Python's `tempfile.TemporaryDirectory()` to create isolated test environments:

```python
with tempfile.TemporaryDirectory() as temp_dir:
    test_file = os.path.join(temp_dir, "test_image.jpg")
    # ... test logic ...
```

This ensures:
- Tests don't interfere with each other
- No leftover files after tests complete
- Tests work on any platform

### Creating Test Images

Tests create real JPEG images using PIL:

```python
img = Image.new("RGB", (10, 10), color="red")
img_bytes = io.BytesIO()
img.save(img_bytes, format="JPEG")
full_image_data = img_bytes.getvalue()
```

To create a truncated image, we write only part of the data:

```python
truncated_data = full_image_data[:len(full_image_data) // 2]
with open(test_file, "wb") as f:
    f.write(truncated_data)
```

### Mocking Strategy

The first test uses a custom mock that simulates file completion:

```python
def mock_open_with_completion(filepath, *args, **kwargs):
    attempt_count[0] += 1
    if attempt_count[0] == 1:
        # First attempt: file is still truncated
        raise OSError("image file is truncated")
    else:
        # Second attempt: complete the file
        with open(test_file, "wb") as f:
            f.write(full_image_data)
        return original_open(filepath, *args, **kwargs)
```

This allows us to simulate the exact moment when a file transitions from truncated to complete.

## Error Handling in `_wait_for_file_stability()`

The function catches several types of errors:

1. **`FileNotFoundError`**: File doesn't exist yet (still being created)
2. **`OSError`**: File exists but can't be read (truncated, locked, corrupted)
3. **`subprocess.TimeoutExpired`**: Process timeout (legacy check)

Each error triggers a sleep and retry until:
- The file opens successfully → returns converted image
- Timeout is reached → returns `None`

## Common PIL Errors with Truncated Images

When PIL encounters truncated images, it may raise various errors:

- `OSError: image file is truncated`
- `OSError: broken data stream when reading image file`
- `SyntaxError: broken PNG file`
- `UnidentifiedImageError: cannot identify image file`

All of these are caught by the `OSError` handler (or its subclasses).

## Real-World Scenarios These Tests Cover

1. **Camera Trap Upload**: A wildlife camera is uploading an image over slow/unreliable network
2. **File Sync**: A cloud sync service is downloading a file
3. **FTP Transfer**: Images being transferred from a remote server
4. **SD Card Write**: Camera writing directly to storage that PumaGuard is monitoring
5. **Corrupted Files**: Storage media errors causing incomplete writes

## Configuration

The `_wait_for_file_stability()` function accepts parameters:

- **`timeout`** (default: 30 seconds): Maximum time to wait
- **`interval`** (default: 0.5 seconds): Time between retry attempts

In tests, we use shorter values (timeout=1-2s, interval=0.01s) for faster execution.

## Running the Tests

```bash
# Run only the truncated image tests
pytest tests/test_server.py::TestFolderObserver::test_wait_for_file_stability_truncated_image -v
pytest tests/test_server.py::TestFolderObserver::test_wait_for_file_stability_permanently_truncated -v

# Run all file stability tests
pytest tests/test_server.py -k "wait_for_file_stability" -v

# Run all server tests
pytest tests/test_server.py -v
```

## Expected Output

When tests pass, you should see:

```
tests/test_server.py::TestFolderObserver::test_wait_for_file_stability_truncated_image PASSED
tests/test_server.py::TestFolderObserver::test_wait_for_file_stability_permanently_truncated PASSED
```

The permanently truncated test will log a warning (which is expected):

```
WARNING  PumaGuard:server.py:131 File /tmp/.../test_image.jpg is still open after 1 seconds
```

## Future Enhancements

Potential additional tests could cover:

1. **Different image formats**: PNG, BMP, TIFF truncation
2. **File locking**: Simulate file being locked by another process
3. **Permission errors**: Simulate insufficient permissions
4. **Network mounted files**: Simulate network filesystem delays
5. **Very large files**: Test behavior with multi-MB images
6. **Rapid file updates**: File being continuously updated during monitoring

## Related Files

- **Implementation**: `pumaguard/pumaguard/server.py` (line ~100-135)
- **Tests**: `pumaguard/tests/test_server.py` (TestFolderObserver class)
- **Dependencies**: PIL (Pillow), Python's tempfile and io modules