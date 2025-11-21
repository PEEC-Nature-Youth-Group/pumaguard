# Web UI Directory Structure and Build Process

## Overview

PumaGuard includes a Flutter-based web UI that is served by the Python Flask backend. This document explains the directory structure, build process, and how the files are packaged and served.

## Directory Structure

### Development Structure

```
pumaguard/
├── pumaguard/              # Python package
│   ├── web_ui.py          # Flask server that serves the UI
│   ├── pumaguard-ui/      # Packaged Flutter build (created during build)
│   │   ├── index.html     # Built Flutter files (copied here for packaging)
│   │   ├── main.dart.js
│   │   ├── main.dart.wasm
│   │   ├── flutter.js
│   │   ├── assets/
│   │   └── canvaskit/
│   └── ...
├── pumaguard-ui/          # Flutter project source (at project root)
│   ├── lib/               # Flutter source code
│   │   ├── main.dart
│   │   ├── screens/
│   │   ├── services/
│   │   ├── models/
│   │   └── utils/
│   ├── build/             # Flutter build output
│   │   └── web/          # Built web files
│   ├── pubspec.yaml       # Flutter dependencies
│   └── ...
└── ...
```

### Why This Structure?

1. **`pumaguard-ui/` at project root**: Flutter project lives at the root for easier development
2. **`pumaguard/pumaguard-ui/`**: Built files are copied directly here for Python packaging
3. **Separation**: Keeps Flutter source separate from Python package but includes build output

## Build Process

### Building the Flutter UI

```bash
# Navigate to Flutter project
cd pumaguard-ui

# Get dependencies
flutter pub get

# Build for web with WebAssembly
flutter build web --wasm
```

This creates files in `pumaguard-ui/build/web/`:
- `index.html` - Main HTML entry point
- `main.dart.js` - JavaScript code
- `main.dart.wasm` - WebAssembly binary
- `flutter.js`, `flutter_bootstrap.js` - Flutter framework
- `assets/` - Images, fonts, etc.
- `canvaskit/` - Flutter rendering engine

### Building the Python Package

```bash
# Build both UI and Python package
make build

# Or manually:
make build-ui    # Builds Flutter and copies files
python -m build  # Creates Python wheel
```

The `build-ui` Makefile target does:
1. `flutter pub get` - Install dependencies
2. `flutter build web --wasm` - Build Flutter app
3. `rsync -av --delete pumaguard-ui/build/web/ pumaguard/pumaguard-ui/` - Copy built files to package directory

### What Gets Packaged?

The Python wheel includes only the **built** Flutter files, not the source:

**Included** (via `pyproject.toml`):
```toml
[tool.setuptools.package-data]
pumaguard = ["pumaguard-ui/**/*"]
```

**Included** (via `MANIFEST.in`):
```
recursive-include pumaguard/pumaguard-ui *
```

**Not included**:
- Flutter source code (`pumaguard-ui/lib/`)
- Flutter configuration (`pubspec.yaml`, etc.)
- Development files (`.dart_tool/`, `test/`, etc.)

## How the Server Finds the UI Files

The `WebUI` class in `web_ui.py` uses intelligent path detection with fallback:

```python
# 1. Packaged location (when installed via pip)
pumaguard/pumaguard-ui/

# 2. Development location (when running from source)
../../../pumaguard-ui/build/web/

# 3. Legacy location (backwards compatibility)
pumaguard/web-ui-flutter/build/web/
```

The code checks each location in order and uses the first one that exists.

### Path Detection Logic

```python
# In web_ui.py __init__:
pkg_build_dir = Path(__file__).parent / "pumaguard-ui"
dev_build_dir = Path(__file__).parent.parent.parent / "pumaguard-ui" / "build" / "web"
old_build_dir = Path(__file__).parent / "web-ui-flutter" / "build" / "web"

if pkg_build_dir.exists() and (pkg_build_dir / "index.html").exists():
    # Installed package - use packaged files
    self.flutter_dir = pkg_build_dir
    self.build_dir = pkg_build_dir
elif dev_build_dir.exists() and (dev_build_dir / "index.html").exists():
    # Development - use source repo build
    self.flutter_dir = dev_build_dir.parent.parent
    self.build_dir = dev_build_dir
elif old_build_dir.exists() and (old_build_dir / "index.html").exists():
    # Legacy - backwards compatibility
    self.flutter_dir = old_build_dir.parent.parent
    self.build_dir = old_build_dir
else:
    # Default to package location
    self.flutter_dir = pkg_build_dir
    self.build_dir = pkg_build_dir
```

## Serving the UI

### Flask Routes

The Flask server serves the UI with these routes:

1. **`/`** → Serves `index.html`
2. **`/<path:path>`** → Serves static files (JS, CSS, images, etc.)
   - Falls back to `index.html` for client-side routing
3. **`/api/*`** → API endpoints (handled before static file route)

### Static File Serving

```python
@app.route("/")
def index():
    return send_file(build_dir / "index.html")

@app.route("/<path:path>")
def serve_static(path):
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404
    
    file_path = build_dir / path
    if file_path.exists() and file_path.is_file():
        return send_from_directory(build_dir, path)
    
    # SPA fallback - return index.html for client-side routing
    return send_file(build_dir / "index.html")
```

## Development Workflow

### Working on the UI

```bash
# 1. Make changes to Flutter code
cd pumaguard-ui
# Edit files in lib/

# 2. Test with hot reload (optional)
flutter run -d chrome

# 3. Build for web
flutter build web --wasm

# 4. Test with Python server
cd ..
python -m pumaguard.web_ui
# Visit http://localhost:5000
```

### Working on the Backend

```bash
# Python changes don't require UI rebuild
python -m pumaguard.web_ui

# Or with auto-reload
python -m pumaguard.web_ui --debug
```

## Packaging Workflow

### For Release

```bash
# 1. Build UI
make build-ui

# 2. Build Python package
make build

# This creates:
# - dist/pumaguard-X.Y.Z-py3-none-any.whl
# - dist/pumaguard-X.Y.Z.tar.gz
```

### What's in the Wheel?

```
pumaguard-X.Y.Z-py3-none-any.whl
└── pumaguard/
    ├── __init__.py
    ├── web_ui.py
    ├── classify.py
    ├── ...
    └── pumaguard-ui/
        ├── index.html
        ├── main.dart.js
        ├── main.dart.wasm
        ├── flutter.js
        └── assets/
```

## Testing

### Test UI Build

```bash
# Build and test
make build-ui
python -c "
from pumaguard.web_ui import WebUI
from pumaguard.presets import Preset

presets = Preset()
web_ui = WebUI(presets=presets)
print('Build dir:', web_ui.build_dir)
print('Build exists:', web_ui.build_dir.exists())
"
```

### Test Server

```bash
# Start server
pumaguard-webui --host 0.0.0.0 --port 5000

# In browser:
# http://localhost:5000

# Test API:
curl http://localhost:5000/api/diagnostic
curl http://localhost:5000/api/status
```

## Troubleshooting

### "Flutter web app not built" Error

**Problem**: Server shows error message that Flutter app is not built.

**Solution**:
```bash
cd pumaguard-ui
flutter build web --wasm

# If packaging:
make build-ui
```

### UI Shows 404 or Blank Page

**Problem**: Server starts but UI doesn't load.

**Check**:
1. Build directory exists:
   ```bash
   ls -la pumaguard/pumaguard-ui/
   # or
   ls -la pumaguard-ui/build/web/
   ```

2. Key files present:
   ```bash
   # Should see in pumaguard/pumaguard-ui/:
   # - index.html
   # - main.dart.js
   # - main.dart.wasm
   # - flutter.js
   ```

3. Server is looking in the right place:
   ```python
   from pumaguard.web_ui import WebUI
   from pumaguard.presets import Preset
   
   web_ui = WebUI(presets=Preset())
   print(web_ui.build_dir)
   print(web_ui.build_dir.exists())
   ```

### Old UI Showing (Cache Issue)

**Problem**: Changes to UI not appearing.

**Solution**:
1. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
2. Clear browser cache
3. Rebuild UI:
   ```bash
   cd pumaguard-ui
   rm -rf build/
   flutter build web --wasm
   make build-ui  # If packaging
   ```

### Wrong Directory Error

**Problem**: Server can't find files.

**Solution**:
Ensure you're using the new structure:
- Flutter project at: `pumaguard-ui/`
- Not: `pumaguard/pumaguard/web-ui-flutter/`

If you have both, remove the old one:
```bash
rm -rf pumaguard/pumaguard/web-ui-flutter/
```

## Migration Notes

### From Old Structure

If you have the old `web-ui-flutter` directory:

```bash
# Old location (deprecated)
pumaguard/pumaguard/web-ui-flutter/

# New location
pumaguard/pumaguard-ui/
```

The code supports both locations for backwards compatibility, but new development should use `pumaguard-ui/` at the project root.

## CI/CD Considerations

### GitHub Actions / CI Pipeline

```yaml
# Example workflow
- name: Setup Flutter
  uses: subosito/flutter-action@v2
  with:
    flutter-version: '3.27.x'
    channel: 'beta'

- name: Build Flutter UI
  run: |
    cd pumaguard-ui
    flutter pub get
    flutter build web --wasm

- name: Copy built files for packaging
  run: |
    mkdir -p pumaguard/pumaguard-ui
    rsync -av --delete pumaguard-ui/build/web/ pumaguard/pumaguard-ui/

- name: Build Python package
  run: python -m build
```

## Best Practices

1. **Always build UI before packaging**: Run `make build-ui` before `make build`
2. **Keep builds out of git**: `build/` directories are in `.gitignore`
3. **Test both locations**: Test in development (`pumaguard-ui/`) and as installed package
4. **Clear caches**: When in doubt, clear browser cache and rebuild
5. **Version consistency**: Keep Flutter and Python versions in sync

## Future Improvements

Potential enhancements:
- [ ] Automatic version injection from Python to Flutter
- [ ] Development server with live reload
- [ ] Separate development and production builds
- [ ] Source maps for debugging
- [ ] Bundle size optimization
- [ ] Progressive Web App (PWA) configuration

## References

- Flutter Web Deployment: https://docs.flutter.dev/deployment/web
- Flask Static Files: https://flask.palletsprojects.com/en/3.0.x/tutorial/static/
- Python Packaging: https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/