# PumaGuard UI Development Context

This document provides context for AI assistants (like GitHub Copilot) working on the PumaGuard Flutter UI in the `pumaguard-ui` repository.

## Project Overview

**PumaGuard** is an AI-powered wildlife monitoring system that uses computer vision to detect pumas/mountain lions from trail camera images. The system consists of:

1. **Backend (Python/Flask)**: Image processing, YOLO object detection, TensorFlow classification
2. **Frontend (Flutter)**: Cross-platform UI (Web, Desktop, Mobile) for configuration and monitoring

You are working on the **Flutter UI** which communicates with the Python backend via REST API.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Flutter UI (This Repo)                │
│  ┌────────────┬────────────┬────────────┬─────────────┐ │
│  │   Home     │  Settings  │ Directories│   Images    │ │
│  │  Screen    │   Screen   │   Screen   │   Browser   │ │
│  └────────────┴────────────┴────────────┴─────────────┘ │
│                         │                                │
│                    API Service                           │
│                         │                                │
└─────────────────────────┼────────────────────────────────┘
                          │ HTTP/REST
                          │
┌─────────────────────────┼────────────────────────────────┐
│                         │                                │
│                  Flask Backend                           │
│  ┌────────────┬────────────┬────────────┬─────────────┐ │
│  │   YOLO     │Classifier  │  Folder    │    Web      │ │
│  │  Detection │   Model    │  Monitor   │     UI      │ │
│  └────────────┴────────────┴────────────┴─────────────┘ │
│                  Python/TensorFlow/Flask                 │
└──────────────────────────────────────────────────────────┘
```

## Backend API

The Flask backend runs on `http://localhost:5000` (or server IP) and provides these endpoints:

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/status` | GET | Server status and info |
| `/api/settings` | GET/PUT | Get/update detection settings |
| `/api/directories` | GET/POST/DELETE | Manage watched folders |
| `/api/photos` | GET | List all captured photos |
| `/api/photos/{path}` | GET/DELETE | Access/delete specific photo |
| `/api/folders` | GET | List folders with image counts |
| `/api/folders/{path}/images` | GET | List images in folder |
| `/api/sync/checksums` | POST | Compare checksums for smart sync |
| `/api/sync/download` | POST | Download files (ZIP or single) |

**See `API_REFERENCE.md` for complete API documentation.**

## Key Configuration

### Detection Settings (via API)

```json
{
  "YOLO-min-size": 0.02,           // Min object size (0.0-1.0)
  "YOLO-conf-thresh": 0.25,        // Confidence threshold (0.0-1.0)
  "YOLO-max-dets": 12,             // Max detections per image
  "YOLO-model-filename": "yolov8s_101425.pt",
  "classifier-model-filename": "colorbw_111325.h5",
  "play-sound": true               // Play deterrent sound
}
```

### Settings Storage

- **Backend**: Uses XDG Base Directory specification
- **Default location**: `~/.config/pumaguard/settings.yaml`
- **Legacy location**: `./pumaguard-settings.yaml`

## Flutter Project Structure

```
lib/
├── main.dart                    # App entry point
├── models/                      # Data models
│   ├── status.dart             # Server status
│   └── settings.dart           # Settings model
├── screens/                     # UI screens
│   ├── home_screen.dart        # Main dashboard
│   ├── settings_screen.dart    # Settings configuration
│   ├── directories_screen.dart # Folder management
│   ├── image_browser_screen.dart # Image browsing & download
│   └── server_discovery_screen.dart # mDNS discovery
├── services/                    # Business logic
│   └── api_service.dart        # API communication
└── utils/                       # Utilities
```

## Key Features

### 1. Home Screen
- Display server status
- Quick access to settings, directories, image browser
- Connection status indicator

### 2. Settings Screen
- Configure YOLO detection parameters
- Configure classifier settings
- Enable/disable sound playback
- Save/load settings to/from file

### 3. Directories Screen
- Add/remove watched folders
- View list of monitored directories
- Integration with backend folder observer

### 4. Image Browser Screen (NEW)
- Browse watched folders
- View image thumbnails in grid
- Select multiple images
- Smart sync download (rsync-like)
- Download as ZIP or individual files

## API Service Pattern

All API calls go through `ApiService`:

```dart
// Example usage
final apiService = Provider.of<ApiService>(context);

// Get status
final status = await apiService.getStatus();

// Update settings
await apiService.updateSettings(newSettings);

// Get folders for image browser
final folders = await apiService.getFolders();

// Download images with smart sync
final filesToDownload = await apiService.getFilesToSync(localChecksums);
final zipBytes = await apiService.downloadFiles(filePaths);
```

## Smart Sync Feature

The UI implements rsync-like functionality:

1. **User selects images** to download
2. **Calculate local checksums** (SHA256) of existing files
3. **POST to `/api/sync/checksums`** with local checksums
4. **Server compares** and returns list of files to download
5. **Download only changed/new files** via `/api/sync/download`
6. **Extract ZIP** if multiple files

```dart
// Smart sync workflow
Map<String, String> localChecksums = {}; // path: checksum
for (var file in selectedFiles) {
  if (await localFileExists(file)) {
    localChecksums[file] = await calculateChecksum(file);
  } else {
    localChecksums[file] = ""; // Empty = doesn't exist
  }
}

// Get files that need downloading
final toDownload = await apiService.getFilesToSync(localChecksums);

// Download only necessary files
if (toDownload.isNotEmpty) {
  final bytes = await apiService.downloadFiles(
    toDownload.map((f) => f['path']).toList()
  );
  await saveFiles(bytes);
}
```

## State Management

- **Provider** for dependency injection (ApiService)
- **StatefulWidget** for screen-level state
- Reload data after navigation (`.then((_) => _loadData())`)

## Dependencies

Key packages in `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0              # HTTP requests
  provider: ^6.1.0          # State management
  crypto: ^3.0.3            # SHA256 checksums
  file_picker: ^8.0.0+1     # File/folder selection
  multicast_dns: ^0.3.2+7   # mDNS server discovery
  intl: ^0.19.0             # Date formatting
  web: ^1.1.0               # Web APIs (dart:html replacement)
```

## Platform Considerations

### Web
- Uses `Uri.base.origin` to auto-detect server URL
- Downloads via browser download API
- Limited file system access

### Desktop/Mobile
- Configurable server URL
- Full file system access for smart sync
- Can store local file database
- File picker for destination selection

## Security

- **No authentication** currently (local network only)
- **Path validation**: All file paths validated server-side
- **CORS enabled**: For web UI from any origin
- **Path traversal protection**: Server blocks `../` attempts

## Common Patterns

### Making API Calls

```dart
Future<void> _loadData() async {
  setState(() {
    _isLoading = true;
    _error = null;
  });
  
  try {
    final apiService = Provider.of<ApiService>(context, listen: false);
    final data = await apiService.getSomething();
    setState(() {
      _data = data;
      _isLoading = false;
    });
  } catch (e) {
    setState(() {
      _error = e.toString();
      _isLoading = false;
    });
  }
}
```

### Error Handling

```dart
if (_error != null) {
  return Center(
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.error_outline, size: 48, color: Colors.red),
        SizedBox(height: 16),
        Text('Error: $_error'),
        ElevatedButton(
          onPressed: _loadData,
          child: Text('Retry'),
        ),
      ],
    ),
  );
}
```

### Navigation

```dart
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (context) => const SettingsScreen(),
  ),
).then((_) => _loadStatus()); // Reload after returning
```

## Image File Types

Supported formats:
- `.jpg`, `.jpeg`
- `.png`
- `.gif`
- `.bmp`
- `.webp`

## Testing

### Manual Testing
1. Start backend: `cd .. && make run-server`
2. Run Flutter: `flutter run -d chrome` (web) or `flutter run` (desktop)
3. Access: `http://localhost:5000`

### Automated Tests
```bash
flutter test
```

## Theme

Material 3 with custom color scheme:
- Seed color: `#8B4513` (brown/puma color)
- Light and dark mode support
- System theme mode

## mDNS Discovery

The app can discover PumaGuard servers on the network:
- Service type: `_pumaguard._tcp.local.`
- Default port: `5000`
- Use `multicast_dns` package for discovery

## Best Practices

1. **Always use ApiService** for backend communication
2. **Handle errors gracefully** with user-friendly messages
3. **Show loading states** during async operations
4. **Reload data** after navigation or updates
5. **Use Provider** for dependency injection
6. **Follow Material 3** design guidelines
7. **Support both platforms** (web and native)

## Development Workflow

1. Make UI changes in `pumaguard-ui/` repository
2. Test with local backend: `cd ../pumaguard && make run-server`
3. Build for web: `flutter build web --wasm`
4. Backend auto-serves built UI from `pumaguard-ui/build/web/`

## Common Tasks

### Add New API Endpoint
1. Add method to `lib/services/api_service.dart`
2. Follow existing patterns (error handling, JSON parsing)
3. Use the endpoint in screens

### Add New Screen
1. Create `lib/screens/new_screen.dart`
2. Add navigation from home screen
3. Reload parent data after navigation

### Add New Setting
1. Update `lib/models/settings.dart`
2. Add UI control in `lib/screens/settings_screen.dart`
3. Use `ApiService.updateSettings()` to save

## Troubleshooting

### Cannot Connect to Server
- Check backend is running: `cd ../pumaguard && make run-server`
- Check URL is correct (localhost:5000 or server IP)
- Check CORS is enabled (should be by default)
- Try mDNS discovery if on same network

### Images Not Loading
- Check paths are correct (use `apiService.getPhotoUrl(path)`)
- Verify files exist in watched folders
- Check browser console for network errors
- Ensure files are in allowed directories

### Downloads Not Working
- Web: Check browser download permissions
- Native: Check file picker permissions
- Verify selected files are in watched folders
- Check server logs for errors

## Related Documentation

- **API_REFERENCE.md**: Complete API documentation
- **IMAGE_BROWSER.md**: Image browser feature details
- **XDG_MIGRATION.md**: Settings file location
- **LXC_TESTING.md**: Container testing
- **TESTING.md**: General testing guide

## Support

- GitHub: https://github.com/PEEC-Nature-Youth-Group/pumaguard
- Documentation: http://pumaguard.rtfd.io/

## Quick Reference

### Server Status Response
```json
{
  "status": "running",
  "version": "1.0.0",
  "uptime": 3600,
  "monitored_directories": ["..."],
  "total_images": 150
}
```

### Folder List Response
```json
{
  "folders": [
    {
      "path": "/path/to/folder",
      "name": "folder",
      "image_count": 42
    }
  ]
}
```

### Image List Response
```json
{
  "images": [
    {
      "filename": "image.jpg",
      "path": "/full/path/image.jpg",
      "size": 1024000,
      "modified": 1234567890.0,
      "created": 1234567890.0
    }
  ],
  "folder": "/path/to/folder"
}
```

This context should help you understand how the PumaGuard UI interacts with the backend and guide your development work!