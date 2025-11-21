# Build Reference - Web UI

Quick reference for building and packaging the PumaGuard web UI.

## Directory Structure

```
pumaguard/
├── pumaguard-ui/              # Flutter source (development)
│   ├── lib/                   # Dart/Flutter source code
│   ├── pubspec.yaml           # Flutter dependencies
│   └── build/web/            # Build output (git-ignored)
│
└── pumaguard/                 # Python package
    ├── web_ui.py             # Flask server
    └── pumaguard-ui/         # Built UI files (git-ignored, copied during build)
        ├── index.html
        ├── main.dart.js
        ├── main.dart.wasm
        ├── flutter.js
        ├── assets/
        └── canvaskit/
```

## Quick Commands

### Build UI Only
```bash
make build-ui
```

This runs:
1. `cd pumaguard-ui && flutter pub get`
2. `cd pumaguard-ui && flutter build web --wasm`
3. `rsync -av --delete pumaguard-ui/build/web/ pumaguard/pumaguard-ui/`

### Build Python Package (includes UI)
```bash
make build
```

This runs `make build-ui` first, then `python -m build`.

### Test UI Changes
```bash
# Build UI
make build-ui

# Run server
pumaguard-webui --host 0.0.0.0 --port 5000
```

### Run in Development
```bash
# Without building UI (uses existing build)
python -m pumaguard.web_ui --host 0.0.0.0 --port 5000

# Or use the script
pumaguard-webui --host 0.0.0.0
```

## What Gets Packaged?

### In Python Wheel
- ✅ Built Flutter files (`pumaguard/pumaguard-ui/**/*`)
- ❌ Flutter source code (`pumaguard-ui/lib/`)
- ❌ Flutter config (`pumaguard-ui/pubspec.yaml`)
- ❌ Development files (`.dart_tool/`, `test/`)

Package size: ~32 MB (mostly WASM and JS files)

### Configuration

**pyproject.toml:**
```toml
[tool.setuptools.package-data]
pumaguard = ["pumaguard-ui/**/*"]
```

**MANIFEST.in:**
```
recursive-include pumaguard/pumaguard-ui *
```

## Path Detection

The server automatically detects the UI files in this order:

1. **Package location** (installed via pip):
   ```
   /path/to/site-packages/pumaguard/pumaguard-ui/
   ```

2. **Development location** (running from source):
   ```
   /path/to/repo/pumaguard-ui/build/web/
   ```

3. **Legacy location** (backwards compatibility):
   ```
   /path/to/repo/pumaguard/web-ui-flutter/build/web/
   ```

## Verify Build

```bash
# Check files exist
ls -lh pumaguard/pumaguard-ui/

# Should see:
# - index.html
# - main.dart.js (2.4M)
# - main.dart.wasm (2.1M)
# - flutter.js
# - assets/
# - canvaskit/

# Test server finds them
python3 -c "
from pumaguard.web_ui import WebUI
from pumaguard.presets import Preset
web_ui = WebUI(presets=Preset())
print('Build dir:', web_ui.build_dir)
print('Exists:', web_ui.build_dir.exists())
print('Has index.html:', (web_ui.build_dir / 'index.html').exists())
"
```

## Common Issues

### Build directory is empty
```bash
# Solution: Run build-ui
make build-ui
```

### Server can't find UI files
```bash
# Check what the server sees
python3 -c "
from pumaguard.web_ui import WebUI
from pumaguard.presets import Preset
ui = WebUI(presets=Preset())
print('Looking in:', ui.build_dir)
print('Exists:', ui.build_dir.exists())
"

# If wrong location, rebuild
make build-ui
```

### Old UI showing (cache)
```bash
# Clear browser cache or hard reload
# Ctrl+Shift+R (Linux/Windows)
# Cmd+Shift+R (macOS)

# Or rebuild UI
cd pumaguard-ui
rm -rf build/
flutter build web --wasm
cd ..
make build-ui
```

### Changes not appearing
```bash
# Always rebuild UI after changes
cd pumaguard-ui
flutter build web --wasm
cd ..
make build-ui

# Then restart server
pumaguard-webui
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Setup Flutter
  uses: subosito/flutter-action@v2
  with:
    flutter-version: '3.27.x'
    channel: 'beta'

- name: Build Web UI
  run: make build-ui

- name: Build Python Package
  run: python -m build

- name: Upload Wheel
  uses: actions/upload-artifact@v4
  with:
    name: wheel
    path: dist/*.whl
```

### Docker Example
```dockerfile
FROM python:3.10-slim

# Install Flutter
RUN apt-get update && apt-get install -y \
    curl \
    git \
    unzip \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/flutter/flutter.git -b beta /flutter
ENV PATH="/flutter/bin:$PATH"
RUN flutter doctor

# Copy source
COPY . /app
WORKDIR /app

# Build UI and package
RUN make build-ui
RUN pip install .

CMD ["pumaguard-webui", "--host", "0.0.0.0", "--port", "5000"]
```

## File Sizes

Typical build output sizes:
- `index.html`: 1.2 KB
- `main.dart.js`: 2.4 MB
- `main.dart.wasm`: 2.1 MB
- `flutter.js`: 9.2 KB
- `assets/`: ~4 MB
- `canvaskit/`: ~20 MB

**Total**: ~32 MB

## Cleaning Build Artifacts

```bash
# Clean Flutter build
cd pumaguard-ui
flutter clean

# Clean packaged files
rm -rf pumaguard/pumaguard-ui/

# Clean Python build
rm -rf dist/ build/ *.egg-info
```

## Development Tips

1. **During UI development**: Use `flutter run -d chrome` for hot reload
2. **Testing with backend**: Run `make build-ui` then start the server
3. **Before committing**: Run `make test-ui` to check Flutter code
4. **Before release**: Run `make build` to create wheel with UI included

## Makefile Targets

```bash
make build-ui       # Build Flutter UI and copy to package
make test-ui        # Run Flutter tests and linting
make build          # Build Python package (includes UI)
make run-server     # Build UI and run server
```

## Related Documentation

- [WEB_UI_STRUCTURE.md](WEB_UI_STRUCTURE.md) - Detailed structure explanation
- [MDNS_SETUP.md](MDNS_SETUP.md) - mDNS configuration
- [QUICK_START_MDNS.md](QUICK_START_MDNS.md) - Quick mDNS setup

## Version Compatibility

- Flutter: 3.27+ (beta channel for WASM)
- Python: 3.10+
- Node.js: Not required (Flutter bundles JS)

## Performance Notes

- WASM build provides better performance than JS-only
- First load: ~32 MB download
- Subsequent loads: Cached by browser
- Consider CDN for production deployments