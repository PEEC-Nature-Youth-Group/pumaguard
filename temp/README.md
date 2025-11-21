# PumaGuard Web UI

A modern Flutter web interface for monitoring and configuring the PumaGuard wildlife detection system.

## Features

- **Real-time Status Display**: View system status and monitoring information
- **Settings Management**: Configure YOLO detection and EfficientNet classifier parameters
- **Directory Management**: Add and remove image directories to monitor
- **Responsive Design**: Works on desktop and mobile browsers
- **Material Design 3**: Modern, clean UI with light/dark theme support

## Screenshots

### Home Screen

- System status indicator
- Quick access to settings and directories
- System information display

### Settings Screen

- YOLO detection parameters (min size, confidence threshold, max detections)
- Classifier model configuration
- Sound deterrent settings
- System behavior options

### Directories Screen

- List of monitored directories
- Add/remove directories with confirmation
- Empty state with helpful guidance

## Prerequisites

- Flutter SDK (3.10.0 or later)
- Dart SDK (included with Flutter)
- PumaGuard backend server running

## Installation

1. Install Flutter dependencies:

   ```bash
   cd web-ui-flutter
   flutter pub get
   ```

2. Run code generation (if needed):
   ```bash
   flutter pub run build_runner build --delete-conflicting-outputs
   ```

## Development

### Run in Development Mode

Start the Flutter development server:

```bash
flutter run -d chrome
```

Or for web server mode:

```bash
flutter run -d web-server --web-hostname=0.0.0.0 --web-port=8080
```

### Hot Reload

When running in development mode, press `r` to hot reload or `R` to hot restart.

## Building for Production

### Build Web App

```bash
flutter build web --release
```

The built files will be in `build/web/` directory.

### Build Options

For optimized builds:

```bash
# Build with web renderer
flutter build web --web-renderer canvaskit

# Build with HTML renderer (smaller size)
flutter build web --web-renderer html

# Build with auto-selection
flutter build web --web-renderer auto
```

## Configuration

### API Endpoint

By default, the app connects to `http://localhost:5000`. To change this, modify the `ApiService` constructor in `lib/services/api_service.dart`:

```dart
ApiService({this.baseUrl = 'http://your-server:5000'});
```

Or set it at runtime when creating the provider in `lib/main.dart`:

```dart
Provider<ApiService>(
  create: (_) => ApiService(baseUrl: 'http://your-server:5000'),
  // ...
)
```

## Project Structure

```
lib/
├── main.dart                    # App entry point
├── models/                      # Data models
│   ├── status.dart              # System status model
│   └── settings.dart            # Settings model
├── screens/                     # UI screens
│   ├── home_screen.dart         # Main dashboard
│   ├── settings_screen.dart    # Settings configuration
│   └── directories_screen.dart # Directory management
├── services/                    # API services
│   └── api_service.dart         # Backend API client
└── widgets/                     # Reusable widgets
```

## API Integration

The Flutter app communicates with the PumaGuard backend via REST API:

- `GET /api/status` - Get system status
- `GET /api/settings` - Get current settings
- `PUT /api/settings` - Update settings
- `POST /api/settings/save` - Save settings to file
- `POST /api/settings/load` - Load settings from file
- `GET /api/directories` - Get monitored directories
- `POST /api/directories` - Add directory
- `DELETE /api/directories/:index` - Remove directory

## Starting the Backend

Before using the web UI, start the PumaGuard backend server:

```bash
# From the project root
python -m pumaguard.web_ui --host 0.0.0.0 --port 5000
```

With settings and image directories:

```bash
python -m pumaguard.web_ui \
  --host 0.0.0.0 \
  --port 5000 \
  --settings settings.yaml \
  --image-dir /path/to/images1 \
  --image-dir /path/to/images2
```

## Deployment

### Option 1: Serve with Backend

The PumaGuard backend automatically serves the built Flutter web app from `web-ui-flutter/build/web/`.

1. Build the Flutter app:

   ```bash
   cd web-ui-flutter
   flutter build web --release
   ```

2. Start the backend server:

   ```bash
   cd ..
   python -m pumaguard.web_ui --host 0.0.0.0 --port 5000
   ```

3. Access the UI at `http://localhost:5000`

### Option 2: Serve Separately

Deploy the `build/web/` directory to any web server (nginx, Apache, etc.) and configure CORS on the backend.

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name pumaguard.local;

    root /path/to/web-ui-flutter/build/web;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Troubleshooting

### Cannot Connect to Backend

**Error**: `Failed to connect to PumaGuard server`

**Solutions**:

1. Ensure the backend server is running
2. Check the backend URL in `api_service.dart`
3. Verify CORS is enabled on the backend (it should be by default)
4. Check firewall settings

### Flutter Build Issues

**Error**: `Packages are not up to date`

**Solution**:

```bash
flutter pub get
```

**Error**: `Cannot find module 'canvaskit'`

**Solution**:

```bash
flutter clean
flutter pub get
flutter build web
```

### Settings Not Saving

**Symptoms**: Settings appear to save but don't persist

**Solutions**:

1. Check backend logs for errors
2. Verify write permissions on settings file
3. Ensure settings file path is correctly configured in backend

## Development Tips

### Adding New Settings

1. Add field to `Settings` model in `lib/models/settings.dart`
2. Update `fromJson` and `toJson` methods
3. Add UI control in `lib/screens/settings_screen.dart`
4. Update backend to handle new setting

### Customizing Theme

Edit the `ThemeData` in `lib/main.dart`:

```dart
colorScheme: ColorScheme.fromSeed(
  seedColor: const Color(0xFF8B4513), // Change this color
  brightness: Brightness.light,
),
```

### Adding New Screens

1. Create screen file in `lib/screens/`
2. Add navigation in `home_screen.dart` or app bar
3. Update routing if using named routes

## Testing

Run tests:

```bash
flutter test
```

Run integration tests:

```bash
flutter test integration_test/
```

## Dependencies

Main dependencies:

- `flutter` - Flutter SDK
- `http` ^1.1.0 - HTTP requests
- `provider` ^6.1.0 - State management
- `intl` ^0.19.0 - Internationalization

Dev dependencies:

- `flutter_test` - Testing framework
- `flutter_lints` ^6.0.0 - Linting rules
- `build_runner` ^2.4.0 - Code generation
- `json_serializable` ^6.7.0 - JSON serialization

## Contributing

1. Follow Flutter style guidelines
2. Run `flutter analyze` before committing
3. Format code with `flutter format lib/`
4. Add tests for new features

## License

Same as PumaGuard project.

## Support

For issues, see the main PumaGuard documentation or file an issue on the project repository.

## Related Documentation

- [PumaGuard Main README](../README.md)
- [Backend API Documentation](../docs/api.md)
- [Flutter Documentation](https://flutter.dev/docs)
- [Material Design 3](https://m3.material.io/)
