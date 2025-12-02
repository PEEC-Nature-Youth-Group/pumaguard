# Contributing to PumaGuard

Thank you for your interest in contributing to PumaGuard! This guide will help you set up your development environment and understand our workflow.

## Table of Contents

- [Development Setup](#development-setup)
- [Parallel Backend and UI Development](#parallel-backend-and-ui-development)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Submitting Changes](#submitting-changes)

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or poetry
- Flutter SDK (for UI development)
- Git with submodule support

### Clone the Repository

```bash
git clone --recurse-submodules https://github.com/PEEC-Nature-Youth-Group/pumaguard.git
cd pumaguard
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

### Install Dependencies

**Using uv (recommended):**

```bash
uv venv
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate  # On Windows

# Install development dependencies
uv sync --extra dev
```

**Using poetry:**

```bash
poetry install
```

## Parallel Backend and UI Development

The PumaGuard UI is maintained as a separate Git submodule under `pumaguard-ui/`. The Flask backend serves the built Flutter web app as static files. This architecture allows independent development and testing.

### Development Workflow

For most efficient development, run the backend and UI in separate terminals:

**Terminal 1 - Backend API Server:**

```bash
make dev-backend
```

This starts the Flask server in debug mode on `http://localhost:5000` with hot-reloading enabled. The server includes CORS support for cross-origin requests from the Flutter dev server.

**Terminal 2 - Flutter Web Dev Server:**

```bash
make dev-ui-web
```

This starts Flutter's web development server with hot-reload. By default, it connects to `http://localhost:5000` for API calls.

### Configuring the API URL

When developing on different devices or using emulators, you may need to override the API base URL:

**For Android emulator:**

```bash
make dev-ui-web API_BASE_URL=http://10.0.2.2:5000
```

**For physical devices on the same network:**

```bash
# Find your local IP first (e.g., 192.168.1.50)
make dev-ui-web API_BASE_URL=http://192.168.1.50:5000
```

### Building and Testing the Integrated App

To test the backend serving the built Flutter app (production mode):

```bash
make run-server
```

This builds the Flutter web app and copies it to `pumaguard/pumaguard-ui/`, then starts the Flask server. The integrated app will be available at `http://localhost:5000`.

To build the UI without starting the server:

```bash
make build-ui
```

### Working with UI Changes

#### Updating the UI Submodule

To pull the latest UI changes from the tracked branch:

```bash
make update-ui
```

This fetches updates and merges them into your local submodule. Review the changes, then commit the submodule pointer update:

```bash
git commit -m "chore(ui): bump submodule to latest"
```

#### Making UI Changes

1. **Create matching branches**: Create a feature branch in both repos with the same name for clarity
2. **Work in the submodule**: `cd pumaguard-ui` and make your changes
3. **Test with live backend**: Use `make dev-backend` (in parent repo) and `make dev-ui-web`
4. **Commit UI changes**: Commit and push from within `pumaguard-ui/`
5. **Update parent repo**: The parent repo's submodule pointer will automatically update. Commit this change:
   ```bash
   git add pumaguard-ui
   git commit -m "chore(ui): update submodule to feature/my-feature"
   ```
6. **Submit PRs**: Open separate pull requests for both the UI repo and the parent repo

#### Branch Pairing Strategy

For changes that span both backend and UI:

1. Create a feature branch in `pumaguard-ui`: `git checkout -b feature/my-feature`
2. Push your UI changes and open a PR in the UI repository
3. In the parent repo, create a matching branch: `git checkout -b feature/my-feature`
4. Update the submodule pointer to your UI branch commit: `git add pumaguard-ui`
5. Make your backend changes
6. Open a PR in the parent repository (which will reference the UI PR via the submodule)

When both PRs are approved, merge the UI PR first, then update the parent repo's submodule pointer to the merged commit before merging the parent PR.

## Testing

### Backend Tests

Run the full Python test suite:

```bash
make test
```

This includes unit tests and coverage reporting.

### UI Tests

Test the Flutter application:

```bash
make test-ui
```

This runs Flutter formatting checks, static analysis, and unit tests.

### Integration Testing

Test the complete server workflow:

```bash
make test-server
```

## Code Quality

We enforce code quality standards via automated linting and formatting.

### Run All Checks

```bash
make lint
```

This runs:
- `black` - Python code formatting
- `pylint` - Python linting
- `isort` - Import sorting
- `mypy` - Static type checking
- `bashate` - Shell script linting

### Run Individual Tools

```bash
make black      # Format Python code
make pylint     # Lint Python code
make isort      # Sort imports
make mypy       # Type check
make bashate    # Lint shell scripts
```

### Pre-commit Checks

Before committing, run the full pre-commit suite:

```bash
make pre-commit
```

This runs linting, documentation builds, and all tests.

## Submitting Changes

1. **Create a feature branch**: `git checkout -b feature/your-feature-name`
2. **Make your changes**: Follow the code style and add tests
3. **Test thoroughly**: Run `make pre-commit` to ensure all checks pass
4. **Commit with clear messages**: Use conventional commit format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `chore:` for maintenance tasks
   - `test:` for test changes
5. **Push your branch**: `git push origin feature/your-feature-name`
6. **Open a Pull Request**: Include a clear description of your changes

### CI/CD Pipeline

Our GitHub Actions workflow will automatically:
- Run linting and formatting checks
- Execute the full test suite
- Build documentation
- Create distribution packages
- Run integration tests

All checks must pass before a PR can be merged.

## Additional Resources

- [API Reference](docs/API_REFERENCE.md)
- [Build Reference](docs/BUILD_REFERENCE.md)
- [Web UI Structure](docs/WEB_UI_STRUCTURE.md)
- [mDNS Setup Guide](docs/MDNS_SETUP.md)
- [UI Development Context](pumaguard-ui/UI_DEVELOPMENT_CONTEXT.md)

## Getting Help

- Open an [issue](https://github.com/PEEC-Nature-Youth-Group/pumaguard/issues) for bugs or feature requests
- Join discussions in [GitHub Discussions](https://github.com/PEEC-Nature-Youth-Group/pumaguard/discussions)
- Check existing [documentation](http://pumaguard.rtfd.io/)

Thank you for contributing to PumaGuard! 🐾
