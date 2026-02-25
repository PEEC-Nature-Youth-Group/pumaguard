# PumaGuard AI Agent Instructions

## Project Overview

PumaGuard is a **wildlife monitoring system** that uses ML to detect mountain lions in camera trap images. It's a **hybrid Python/Flutter application** combining TensorFlow/YOLO detection with a web-based monitoring interface.

**Architecture**: Two-stage ML pipeline (YOLO object detection → EfficientNet classification) + Flask REST API + Flutter web UI

## Critical Architecture Concepts

### Two-Stage ML Pipeline

The core classification uses a two-stage approach (see `pumaguard/utils.py::classify_image_two_stage`):

1. **Stage 1 - YOLO Detection**: YOLOv8 detects potential animals in images
2. **Stage 2 - EfficientNet Classification**: Crops are classified as "puma" or "not puma"

**Why two stages?** YOLO filters out false positives (shadows, trees) before expensive classification. Only crops above `YOLO-min-size` threshold proceed to classification.

```python
# Key settings in Preset class:
yolo_model_filename = "yolov8s_101425.pt"
classifier_model_filename = "colorbw_111325.h5"
yolo_min_size = 0.02  # Minimum object size as fraction of image
yolo_conf_thresh = 0.15  # Confidence threshold
```

### Model Distribution System

Models are **split into fragments** (e.g., `color_103025.h5_aa`, `_ab`, etc.) due to GitHub's 100MB file size limit. The `model_downloader.py` module automatically reassembles them using checksums from `model-registry.yaml`.

**Never manually concatenate model fragments** - use `ensure_model_available()` which handles checksums and caching.

### Hybrid Flutter + Python Web UI

The web UI is a **Git submodule** (`pumaguard-ui/`) built separately then bundled into the Python package:

```
pumaguard-ui/              # Flutter source
└── build/web/            # Flutter build output

pumaguard/pumaguard-ui/   # Built files copied here for packaging
└── (included in Python wheel)
```

The Flask server (`web_ui.py::WebUI`) serves the built Flutter files and provides REST endpoints under `/api/*`.

## Development Workflows

### Python Development (Backend)

```bash
# Setup with uv (strongly preferred over poetry)
uv venv && source .venv/bin/activate
uv sync --extra dev --extra extra-dev

# Run tests (ALWAYS run before committing)
make test          # Python tests with coverage
make lint          # black, pylint, isort, mypy, bashate
make pre-commit    # Full validation (lint + docs + tests)

# Run server for testing
uv run pumaguard server /path/to/watch/folder
```

### Flutter UI Development

**Parallel development** (backend + UI simultaneously):

```bash
# Terminal 1 - Backend with CORS for dev
make dev-backend

# Terminal 2 - Flutter with hot reload
make dev-ui-web                                    # Uses localhost:5000
make dev-ui-web API_BASE_URL=http://10.0.2.2:5000 # For Android emulator
```

The Flutter UI auto-detects the API URL:

- **Web**: Uses `Uri.base.origin` (current browser URL)
- **Mobile/Desktop**: Uses configured `baseUrl` or `localhost:5000`

See `pumaguard-ui/lib/services/api_service.dart::getApiUrl()` for logic.

**CRITICAL: Before committing UI changes**, ALWAYS run pre-commit validation in the submodule:

```bash
cd pumaguard-ui
make pre-commit    # Runs version, analyze, format, build
cd ..
```

**⚠️ MANDATORY:** This step is REQUIRED for ALL UI changes. Do not skip it.

This ensures:

- Version is generated from git tags
- Flutter analyze passes with no issues (zero warnings/errors)
- Code is properly formatted with `dart format`
- Web build succeeds without errors

**Note:** If `flutter analyze` reports warnings about unused elements, either:

1. Remove the unused code, OR
2. Add `// ignore: unused_element` comment if the code is intentionally reserved for future use

### UI Submodule Workflow

The UI is in a **separate Git repository** tracked as a submodule:

```bash
# Pull UI updates
make update-ui

# After making UI changes in pumaguard-ui/
cd pumaguard-ui
git commit -m "feat: new feature"
git push
cd ..
git add pumaguard-ui  # Updates submodule pointer
git commit -m "chore(ui): bump submodule to feature/my-feature"
```

**Branch pairing strategy**: Use matching branch names (e.g., `feature/my-feature`) in both repos for related changes.

## Code Patterns & Conventions

### Settings Management (XDG Compliance)

PumaGuard uses **XDG Base Directory specification** for all user data:

```python
# Config: ~/.config/pumaguard/pumaguard-settings.yaml
get_xdg_config_home() / "pumaguard" / "pumaguard-settings.yaml"

# Cache: ~/.cache/pumaguard/
get_xdg_cache_home() / "pumaguard"

# Logs: ~/.cache/pumaguard/pumaguard.log
```

**Never hardcode `~/.pumaguard/`** - always use XDG functions from `presets.py`.

### Model Caching

Models are cached in memory using `_MODEL_CACHE` dict in `utils.py`:

```python
# Cache key format: f"{model_type}_{model_path}"
classifier = get_cached_model("classifier", classifier_model_path)
detector = get_cached_model("detector", yolo_model_path)
```

This prevents reloading multi-GB models on every classification.

### File Watching

The server supports two watch methods (`server.py::FolderObserver`):

- **`inotify`**: Fast, event-driven (Linux native filesystems only)
- **`os`**: Polling-based (works everywhere, including WSL mounted drives)

Default is `os` for maximum compatibility. Use `--watch-method inotify` for better performance on native Linux.

### REST API Conventions

All API endpoints in `web_ui.py` follow these patterns:

- **Path validation**: Files MUST be in `classification_directories` (prevents path traversal)
- **CORS enabled**: Required for web UI to work from any IP
- **Checksums for sync**: SHA256 hashes in `/api/sync/checksums` enable rsync-like downloads

Example validation pattern:

```python
abs_filepath = os.path.abspath(filepath)
if not any(abs_filepath.startswith(d) for d in self.classification_directories):
    return jsonify({"error": "Access denied"}), 403
```

## Testing Patterns

### Functional Tests

Use exact percentage assertions for model verification (`Makefile::check-functional`):

```makefile
# Extract prediction with sed regex
sed --quiet --regexp-extended '/^Predicted.*lion\.5/s/^.*:\s*([0-9.%]+).*$$/\1/p'
```

These are **regression tests** - percentages must match exactly to catch model degradation.

### Unit Tests

**Python Tests:**

- **Test settings persistence**: `test_presets.py`
- **Test server routes**: `test_server.py`
- **Test model loading**: `test_utils.py`

Run with `make test` for coverage reports.

**Flutter Tests:**

- Run `make test-ui` from root directory, or
- Run `flutter test` from `pumaguard-ui/` subdirectory
- **Before committing UI code**: Always run `cd pumaguard-ui && make pre-commit`

## Critical Files to Review

When modifying core functionality, understand these files first:

- **`pumaguard/utils.py`**: ML pipeline, model loading, caching
- **`pumaguard/presets.py`**: Settings management, XDG paths
- **`pumaguard/web_ui.py`**: Flask server, REST API, file serving
- **`pumaguard/server.py`**: File watching, classification loop
- **`pumaguard-ui/lib/services/api_service.dart`**: UI ↔ API communication

## Common Pitfalls

1. **Don't run `poetry run` and `uv run` in the same environment** - choose one package manager
2. **Flutter UI must be built** before `make build` or server will show empty page
3. **Model fragments are read-only** - don't modify files in `pumaguard-models/` directly
4. **Settings files use YAML** - use `yaml.safe_load()`, never `yaml.load()`
5. **Path traversal attacks** - always validate file paths against allowed directories

## Deployment Notes

### mDNS/Zeroconf

Server advertises as `pumaguard.local` via mDNS for easy discovery:

```bash
pumaguard-webui --mdns-name my-server  # Accessible at my-server.local:5000
pumaguard-webui --no-mdns              # Disable mDNS
```

Requires Avahi (Linux), Bonjour (Windows), or native support (macOS). See `docs/MDNS_SETUP.md`.

### Packaging

Python wheel includes:

- ✅ Compiled Python code
- ✅ Built Flutter app (`pumaguard/pumaguard-ui/`)
- ✅ Model registry YAML
- ❌ Model files (downloaded on first use)
- ❌ Flutter source code

Build process: `make build-ui` → `make build` → `dist/*.whl`

## Key Commands Reference

```bash
# Development
make install-dev              # Install with dev dependencies
make dev-backend              # Start backend with hot reload
make dev-ui-web              # Start Flutter with hot reload

# Testing & Quality
make test                     # Run Python tests
make test-ui                  # Run Flutter tests
make lint                     # All linters (Python)
make pre-commit              # Full validation suite (Python)

# Flutter UI Quality (run from pumaguard-ui/)
cd pumaguard-ui && make pre-commit   # UI validation (analyze, format, build)

# Building
make build-ui                # Build Flutter → copy to pumaguard/
make build                   # Build Python wheel (includes UI)

# Server Operations
uv run pumaguard server FOLDER              # Watch folder
uv run pumaguard classify image.jpg         # One-off classification
uv run pumaguard verify                     # Validate model accuracy
uv run pumaguard-webui --host 0.0.0.0       # Start web UI
```

## Documentation

Full docs at <http://pumaguard.rtfd.io/>. Key references:

- **API Reference**: `docs/API_REFERENCE.md` (REST endpoint specs)
- **Build Reference**: `docs/BUILD_REFERENCE.md` (Flutter + Python packaging)
- **Contributing**: `CONTRIBUTING.md` (branch strategy, PR workflow)
- **Web UI Structure**: `docs/WEB_UI_STRUCTURE.md` (detailed UI build process)

---

_When in doubt, check existing test files for patterns and consult the comprehensive documentation in `docs/`._
