# PumaGuard AI Agent Instructions

## Project Overview

PumaGuard is a machine learning-based wildlife detection system designed to identify pumas (mountain lions) and other wildlife from camera trap images. The project uses TensorFlow and PyTorch for model training and inference, and includes a modern Flutter-based web interface for monitoring and configuration.

### Key Components

- **Python Package (`pumaguard/`)**: Core ML models and classification logic
- **Web UI (`pumaguard-ui/`)**: Flutter-based web interface (submodule)
- **Models (`pumaguard-models/`)**: Pre-trained model weights (submodule)
- **Training Data (`training-data/`)**: Image datasets for training (submodule)
- **Scripts (`scripts/`)**: Training, deployment, and configuration scripts
- **Documentation (`docs/`)**: Sphinx-based documentation

## Development Environment

The project supports two package managers:
- **uv** (recommended): Fast Python package installer
- **poetry**: Alternative package manager

### Setting Up Development Environment

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate
uv sync --extra dev --extra extra-dev

# Using poetry (alternative)
poetry install
```

## Code Quality Requirements

**ALL CHANGES MUST PASS THE LINTERS BEFORE SUBMISSION.**

### Required Linters

The project uses multiple linters to ensure code quality:

1. **pylint**: Python code linting with project-specific configuration in `pylintrc`
   - Max line length: 79 characters
   - Disabled checks: R0801, R0902, R0912, R0914, R0915, W0511

2. **black**: Python code formatting
   - Line length: 79 characters
   - Enforces consistent code style

3. **isort**: Python import sorting
   - Ensures consistent import organization
   - Configuration in `pyproject.toml`

4. **mypy**: Static type checking
   - Checks type hints and annotations
   - Excludes `pumaguard-ui/` directory

5. **bashate**: Bash script linting
   - Ignores E006 (line length for readability)

6. **ansible-lint**: Ansible playbook linting
   - Used for deployment scripts

### Running Linters

#### Run All Linters
```bash
make lint
```

#### Run Individual Linters
```bash
make pylint    # Python linting
make black     # Python formatting check
make isort     # Import sorting check
make mypy      # Type checking
make bashate   # Bash script linting
make ansible-lint  # Ansible playbook linting
```

### Before Submitting Changes

1. **Run linters early and often**: Don't wait until the end to check linting
2. **Fix all linting errors**: The CI will fail if any linter reports issues
3. **Test your changes**: Run `make test` to ensure tests pass
4. **Update documentation**: If you change APIs or functionality, update docs

## Building and Testing

### Running Tests
```bash
make test              # Run Python tests with coverage
make test-ui           # Run Flutter UI tests
make test-server       # Run server integration tests
```

### Building the Project
```bash
make build             # Build Python package and UI
make build-ui          # Build Flutter web UI only
```

### Working with the Flutter UI Submodule

The `pumaguard-ui/` directory is a git submodule containing the Flutter-based web interface. When making changes to the UI:

1. **Navigate to the submodule**:
   ```bash
   cd pumaguard-ui
   ```

2. **Run pre-commit checks** (REQUIRED before submitting UI changes):
   ```bash
   make pre-commit
   ```
   This target runs:
   - `make version`: Generates version from git tags
   - `make analyze`: Runs `flutter analyze` to check for errors
   - `make format`: Runs `dart format` to format code
   - `make build`: Builds the web app with WASM

3. **Individual Flutter linting commands**:
   ```bash
   flutter analyze        # Check for errors and warnings
   dart format lib        # Format Dart code
   flutter test          # Run all tests
   ```

4. **Return to parent repository**:
   ```bash
   cd ..
   ```

**Important**: Always run `make pre-commit` in the `pumaguard-ui/` directory before committing UI changes. This ensures the Flutter code is properly analyzed, formatted, and builds successfully.

### Backend Debugging: Path Resolution

When debugging image browser 404s related to path resolution, enable backend path debug to include helpful metadata in API responses:

```bash
# Enable debug paths for backend (temporary, non-production)
export PG_DEBUG_PATHS=1
make dev-backend
```

With `PG_DEBUG_PATHS=1`, the server will:
- Add `"_abs"`, `"_base"`, and `"_folder_abs"` to `/api/folders/{folder}/images` items
- Include `"_requested"`, `"_tried_bases"`, `"_resolved"`, and `"_ext"` in error responses from `/api/photos/<filepath>`

Turn off by unsetting `PG_DEBUG_PATHS`.

### Documentation
```bash
make docs              # Build Sphinx documentation
make apidoc            # Generate API documentation
```

## Project Structure

```
pumaguard/
├── .github/           # GitHub workflows and actions
│   ├── agents/        # AI agent instructions (this file)
│   ├── actions/       # Custom GitHub actions
│   └── workflows/     # CI/CD workflows
├── docs/              # Sphinx documentation
├── pumaguard/         # Main Python package
│   ├── main.py        # CLI entry point
│   ├── model_cli.py   # Model management CLI
│   └── ...
├── pumaguard-models/  # Pre-trained models (submodule)
├── pumaguard-ui/      # Flutter web UI (submodule)
├── scripts/           # Utility scripts
├── tests/             # Python tests
├── training-data/     # Training datasets (submodule)
├── Makefile           # Build and test automation
├── pyproject.toml     # Python project configuration
├── pylintrc           # Pylint configuration
└── README.md          # Project documentation
```

## Continuous Integration

The project uses GitHub Actions for CI/CD:
- **Linting**: All linters run on every PR (`test-and-package.yaml`)
- **Testing**: Python and UI tests run automatically
- **Building**: Packages are built for PyPI and Snap
- **Documentation**: Docs are built and published to ReadTheDocs

### CI Workflow Jobs

1. `lint-python`: Runs pylint, black, isort, mypy
2. `lint-bash`: Runs bashate on shell scripts
3. `lint-ansible`: Runs ansible-lint on playbooks
4. `test-python`: Runs pytest with coverage
5. `test-ui`: Runs Flutter tests
6. `build-python`: Builds Python wheel package
7. `build-snap`: Builds Snap packages

## Important Coding Standards

### Python
- **Line length**: 79 characters (enforced by black and pylint)
- **Import style**: Use isort configuration in `pyproject.toml`
- **Type hints**: Required for new code (checked by mypy)
- **Docstrings**: Follow existing patterns in the codebase
- **Testing**: Write tests for new functionality

### Bash Scripts
- Follow bashate guidelines (except E006)
- Use shellcheck-compatible syntax

### Ansible
- Follow ansible-lint rules
- Use vault for sensitive data

## Making Changes

1. **Understand the change**: Read the issue/requirement carefully
2. **Explore the code**: Familiarize yourself with relevant files
3. **Make minimal changes**: Only modify what's necessary
4. **Run linters frequently**: Check your work as you go
   ```bash
   # For Python code
   make lint
   
   # For Flutter UI code
   cd pumaguard-ui && make pre-commit && cd ..
   ```
5. **Run tests**: Ensure nothing breaks
   ```bash
   make test              # Python tests
   make test-ui           # Flutter tests (from parent dir)
   cd pumaguard-ui && flutter test && cd ..  # Flutter tests (from submodule)
   ```
6. **Update documentation**: If needed
7. **Commit with clear messages**: Describe what and why

## Linting Failures in CI

If CI fails due to linting:
1. Check the specific linter that failed in the workflow logs
2. Run that linter locally: `make <linter-name>`
3. Fix the reported issues
4. Re-run all linters: `make lint`
5. Commit and push the fixes

## Common Linting Issues

### Black Formatting
```bash
# Check formatting
make black

# Auto-fix formatting issues
uv run black pumaguard
```

### Import Sorting (isort)
```bash
# Check import order
make isort

# Auto-fix import order
uv run isort pumaguard tests scripts
```

### Pylint Issues
- Follow the project's pylintrc configuration
- Some checks are disabled; don't re-enable without discussion
- Focus on fixing warnings that affect code quality

### Type Checking (mypy)
- Add type hints to new functions
- Use `typing` module for complex types
- Check with: `make mypy`

## Resources

- **Documentation**: http://pumaguard.rtfd.io/
- **Repository**: https://github.com/PEEC-Nature-Youth-Group/pumaguard
- **PyPI Package**: https://pypi.org/project/pumaguard/
- **CI Workflows**: `.github/workflows/test-and-package.yaml`

## Summary

**Remember**: The most important rule is that **all changes must pass the linters**. 

- For **Python changes**: Run `make lint` before submitting
- For **Flutter UI changes**: Run `cd pumaguard-ui && make pre-commit && cd ..` before submitting

The CI system will automatically verify this, and PRs with linting failures cannot be merged.
