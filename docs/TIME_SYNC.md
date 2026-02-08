# Time Synchronization Feature

## Overview

The time synchronization feature allows users to synchronize the PumaGuard server's system time with their client device (phone, tablet, or computer). This is especially useful for wildlife camera deployments in remote locations where:

- The server device (e.g., Raspberry Pi) lacks internet connectivity for NTP
- Accurate timestamps are critical for wildlife monitoring logs
- Manual time configuration is needed after power failures

## Features

- **View Server Time**: Check the current time on the PumaGuard server
- **Automatic Sync**: Push your device's current time to the server with one click
- **Manual Time Setting**: Set a specific time if needed (via API)
- **Cross-Platform Support**: Works on Linux, macOS, and Windows servers

## User Interface

The time synchronization controls are located in the **Settings** screen under the **System Settings** section:

1. **Current Server Time**: Displays the server's current time in your local timezone
2. **Refresh Button**: Updates the displayed server time
3. **Sync Time Button**: Pushes your device's current time to the server

### Using the UI

1. Navigate to **Settings** → **System Settings**
2. View the current server time in the "Server Time" card
3. Click **"Sync Time from This Device"** to synchronize
4. A success or error message will appear
5. The server time display will automatically refresh after successful sync

## API Reference

### Get Server Time

Retrieve the current server time.

**Endpoint**: `GET /api/system/time`

**Response**:
```json
{
  "timestamp": 1705318200.0,
  "iso": "2024-01-15T10:30:00+00:00",
  "local_iso": "2024-01-15T02:30:00",
  "timezone": "UTC"
}
```

**Fields**:
- `timestamp`: Unix timestamp in seconds (UTC)
- `iso`: ISO 8601 formatted UTC datetime
- `local_iso`: ISO 8601 formatted local datetime (server's timezone)
- `timezone`: Server's timezone (always UTC for consistency)

### Set Server Time

Set the server's system time.

**Endpoint**: `PUT /api/system/time`

**Request Body** (choose one format):

Using Unix timestamp:
```json
{
  "timestamp": 1705318200.0
}
```

Using ISO 8601 string:
```json
{
  "iso": "2024-01-15T10:30:00Z"
}
```

**Success Response** (200):
```json
{
  "success": true,
  "message": "Time set successfully using timedatectl",
  "new_time": "2024-01-15T10:30:00+00:00"
}
```

**Error Response** (400/500):
```json
{
  "error": "Permission denied. Server needs appropriate permissions..."
}
```

## Permissions Requirements

Setting system time requires elevated privileges:

### Linux

The server needs one of the following:

1. **Run with sudo**: `sudo pumaguard-webui`
2. **Grant CAP_SYS_TIME capability**:
   ```bash
   sudo setcap CAP_SYS_TIME+ep /path/to/python
   ```
3. **Configure systemd service** with appropriate capabilities:
   ```ini
   [Service]
   AmbientCapabilities=CAP_SYS_TIME
   ```

**Commands Used**:
- Primary: `timedatectl set-time "YYYY-MM-DD HH:MM:SS"` (systemd-based systems)
- Fallback: `date -u -s @<timestamp>` (non-systemd systems)

### macOS

Run the server with sudo:
```bash
sudo pumaguard-webui
```

**Command Used**: `date -u MMDDhhmmYYYY.SS`

### Windows

Run the server as Administrator (right-click → "Run as Administrator").

**Commands Used**:
- `time HH:MM:SS`
- `date MM-DD-YYYY`

## Implementation Details

### Backend (Python)

**Files Modified**:
- `pumaguard/web_routes/system.py` - New routes module for system administration
- `pumaguard/web_ui.py` - Imports and registers system routes

**Key Functions**:
- `register_system_routes()` - Registers Flask routes for time management
- `_set_system_time()` - Platform-specific time setting logic
- `_command_exists()` - Checks for available system commands

### Frontend (Flutter)

**Files Modified**:
- `pumaguard-ui/lib/services/api_service.dart` - API methods for time sync
- `pumaguard-ui/lib/screens/settings_screen.dart` - UI controls and state management

**Key Methods**:
- `getServerTime()` - Fetches current server time
- `syncServerTime()` - Syncs using device's current time
- `setServerTime()` - Sets server time with specific timestamp/ISO string

## Error Handling

The implementation handles various error scenarios:

1. **Permission Denied**: Displays detailed message about required privileges
2. **Command Not Found**: Falls back to alternative commands on Linux
3. **Invalid Time Format**: Returns 400 error with format details
4. **Network Errors**: Shows user-friendly error messages in UI
5. **Platform Support**: Detects and reports unsupported platforms

## Security Considerations

1. **No Authentication**: Currently, the API endpoints are not authenticated. If exposing the server to untrusted networks, consider:
   - Adding authentication to `/api/system/time` endpoints
   - Using a firewall to restrict access
   - Running behind a reverse proxy with authentication

2. **Privilege Escalation**: The server needs elevated privileges to set time. Use the least-privilege approach:
   - On Linux, prefer CAP_SYS_TIME capability over full sudo
   - On systemd, use `AmbientCapabilities` instead of running as root

3. **Input Validation**: All time inputs are validated and sanitized to prevent command injection

## Testing

Run the test suite:
```bash
# All tests
uv run pytest tests/

# Time sync tests only
uv run pytest tests/test_system_routes.py -v
```

**Test Coverage**:
- API endpoint responses (GET/PUT)
- Time format parsing (Unix timestamp, ISO 8601)
- Platform-specific command execution
- Permission error handling
- Invalid input handling

## Troubleshooting

### "Permission denied" error

**Symptom**: Sync fails with permission error message.

**Solution**: Ensure the server has appropriate privileges (see Permissions Requirements above).

### Time sync appears to work but server time doesn't change

**Symptom**: Success message shown but `date` command shows old time.

**Possible Causes**:
1. NTP service is overriding the manual time setting
2. System has a read-only filesystem
3. Hardware clock (RTC) is not updated

**Solutions**:
- Disable NTP: `sudo timedatectl set-ntp false` (Linux)
- Update hardware clock: `sudo hwclock --systohc` (Linux)
- Check system logs: `journalctl -xe` (Linux)

### Server time display shows "Loading..." indefinitely

**Symptom**: UI never loads the server time.

**Solution**: 
- Check network connectivity between device and server
- Verify the server is running
- Check browser console for CORS or network errors

## Future Enhancements

Potential improvements for future versions:

1. **NTP Configuration**: Allow users to configure NTP servers via UI
2. **Time Zone Selection**: Let users set the server's timezone
3. **Automatic Sync**: Periodic automatic time sync from connected devices
4. **Time Drift Detection**: Alert users when server time drifts significantly
5. **Manual Time Picker**: Calendar/clock widget for setting specific times in UI
6. **Authentication**: Add authentication layer for security-sensitive deployments

## References

- [timedatectl man page](https://man7.org/linux/man-pages/man1/timedatectl.1.html)
- [date command documentation](https://man7.org/linux/man-pages/man1/date.1.html)
- [Linux capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html)
- [RFC 3339 (ISO 8601 profile)](https://www.rfc-editor.org/rfc/rfc3339)

## Contributing

When contributing to this feature:

1. Run tests: `uv run pytest tests/test_system_routes.py`
2. Run linting: `uv run pylint pumaguard/web_routes/system.py`
3. Format code: `uv run black pumaguard/web_routes/system.py`
4. Update this documentation if adding new functionality
5. Test on multiple platforms if possible (Linux, macOS, Windows)

For Flutter changes:
```bash
cd pumaguard-ui
make pre-commit  # REQUIRED before committing UI changes
```
