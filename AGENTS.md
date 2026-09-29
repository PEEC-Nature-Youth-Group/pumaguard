# Agent Instructions for pumaguard

Notes for coding agents working in this repository, covering tooling
quirks discovered while working in this sandboxed environment.

## Project overview

PumaGuard is a machine-learning project for classifying trail-camera
images as containing a mountain lion or not, for wildlife monitoring,
research, and (potentially) automated deterrence. See
`docs/source/index.rst` / <http://pumaguard.rtfd.io/> for the full
project description and `notebooks/Mountain_Lions.ipynb` for the
model-training walkthrough.

This is a **monorepo** with a Python backend and a Flutter web
frontend:

- `pumaguard/pumaguard/` — the Python package (installed as the
  `pumaguard` console script via `pumaguard/main.py:main`). Its
  subcommands (see `main.py`'s `configure_subparsers`) are:
  - `classify` (`classify.py`) — run a trained model over one or more
    images.
  - `server` (`server.py`, `web_routes/`, `web_ui.py`) — a Flask app
    that watches folders for new images, classifies them, exposes a
    JSON API, and serves the built Flutter web UI as static files.
  - `verify` (`verify.py`) — score a model against a fixed
    verification image set (from the `training-data` submodule) to
    check accuracy hasn't regressed.
  - `models` (`model_cli.py`, `model_downloader.py`) — list, download,
    and verify model weights against `model-registry.yaml`.
  - Supporting modules: `presets.py` (settings/config), `utils.py`,
    `stats.py`, `lock_manager.py`, `sound.py` (the separate
    `playsound` script), and `camera_heartbeat.py` /
    `device_heartbeat.py` / `plug_heartbeat.py` /
    `shelly_control.py` (monitoring/controlling cameras and Shelly
    smart plugs used as deterrents in the field).
- `pumaguard-ui/` — the Flutter/Dart web frontend. It's a **plain
  tracked directory**, not a Git submodule (see the Flutter section
  below) — it's built and copied into
  `pumaguard/pumaguard/pumaguard-ui/` for the Flask server to serve.
- `pumaguard-models/` and `training-data/` — real Git submodules
  holding trained model weights and training/verification images,
  respectively (see the "Large Git submodules" note below).
- `scripts/` — Ansible playbooks/shell scripts for provisioning real
  Raspberry Pi hardware in the field (`configure-device`,
  `configure-laptop` Makefile targets) and for local
  LXD/multipass-based test environments.
- `pumaguard/pumaguard/model-registry.yaml` — source-of-truth
  checksum registry for published model files (see "Project layout
  notes" below).

When in doubt about a workflow (running tests, linting, building,
deploying), check the `Makefile` first — it's the canonical entry
point for nearly everything in this repo.

## Sandboxed terminal gotcha: spurious exit code 2

Every command run through the sandboxed `terminal` tool in this
environment reports a **failed exit code (2)**, even when the command
succeeded, because the pty can't set a tty process group:

```
/bin/sh: 1: Cannot set tty process group (No such process)
```

This happens even for trivial, always-succeeding commands like
`echo hi`. **Don't trust the reported exit code** — check the actual
stdout/stderr content to determine whether a command succeeded or
failed.

## Package manager: `uv`

This project uses [`uv`](https://docs.astral.sh/uv/) (not Poetry, not
plain `pip`) for dependency management, virtualenvs, and running
scripts. See the `Makefile` for the canonical commands — prefer
reusing its targets over inventing new ones.

- `uv` is installed as a **snap package** (`astral-uv`). Snap-packaged
  commands need to talk to `snapd` for their confinement profile,
  which does **not** work inside this tool's sandboxed `terminal`
  calls. Every sandboxed invocation fails with:

  ```
  internal error, please report: running "astral-uv.uv" failed: timeout waiting for snap system profiles to get updated
  ```

  **Fix:** always pass `unsandboxed: true` (with a short `reason`)
  whenever invoking `uv` or any `make` target that shells out to `uv`.
  Plain read-only commands that don't touch `uv` (e.g. `cat`, `grep`,
  `ls`) don't need this.

- The project virtualenv lives at `.venv` (created via `uv venv` /
  `make .venv`).

## Running tests

Prefer the Makefile target, which installs dev deps and runs the full
suite with coverage:

```sh
make test-python
```

This runs `uv sync --extra dev --frozen` (installs everything in the
`dev` extra, including `torch`/`tensorflow`/`ultralytics` — this is a
heavy, slow install the first time) followed by:

```sh
uv run --system-certs --frozen pytest --verbose --cov=pumaguard --cov-report=term-missing
```

Once `.venv` is populated, you can iterate faster on a subset of tests
without reinstalling everything:

```sh
uv run --system-certs --frozen pytest tests/test_model_downloader.py -q
```

Remember to run these `unsandboxed: true` per the note above. Network
access to `pypi.org`/`files.pythonhosted.org` (and
`download.pytorch.org` for the CPU torch wheels) is needed the first
time dependencies are installed; after that everything is cached in
`.venv` and no network is needed.

## Linting

Individual linters can be run directly instead of the full `make lint`
(which also runs `ansible-lint`, `bashate`, etc.):

```sh
uv run --system-certs --frozen black --check --target-version py312 <path>
uv run --system-certs --frozen isort --check-only <path>
uv run --system-certs --frozen pylint --rcfile=pylintrc <path>
. .venv/bin/activate && mypy --check-untyped-defs <path>
```

`black`'s AST safety check can warn about "cannot parse code formatted
for Python 3.15" if the running interpreter is older than the one
`black` detects as the target; pass `--target-version py312` to match
this project's `requires-python`.

## Flutter / Dart UI (`pumaguard-ui`)

The Flutter web UI lives in `pumaguard/pumaguard-ui/` and is built by
`make lint-ui`, `make test-ui`, `make build-ui`, and `make dev-ui-web`
(see the `Makefile`).

- `flutter`/`dart` are installed directly (not as a snap), so they
  don't need `unsandboxed: true` the way `uv` does.
- They **do** need write access outside the project: pass
  `fs_write_paths` for `~/flutter`, `~/.dart-tool`, and
  `~/.pub-cache` (their cache/telemetry dirs), or commands like
  `flutter --version`/`flutter pub get`/`flutter analyze` will crash
  with `Read-only file system` errors.
- The first `flutter pub get` in a fresh environment needs
  `allow_hosts` for `pub.dev`, `*.pub.dev`, and
  `storage.googleapis.com`. After packages are cached in
  `~/.pub-cache`, no network is needed.
- Despite `CONTRIBUTING.md` describing `pumaguard-ui` as a separate
  Git submodule, it was merged into this monorepo by commit
  `41e5e63` ("Prepare for monorepo") and is now a plain tracked
  directory — there's no nested `.git` and no `.gitmodules` entry for
  it. Don't expect submodule semantics (independent commits/pushes)
  to apply to it.

## Project layout notes

- Repo root: `pumaguard/` (this is also a project root directory in
  the editor). The Python package itself is nested one level down at
  `pumaguard/pumaguard/`.
- Tests live in `pumaguard/tests/`.
- `pumaguard/pumaguard/model-registry.yaml` is the source-of-truth
  registry of model file checksums (whole-file and per-fragment
  `sha256`), consumed by `pumaguard/pumaguard/model_downloader.py` at
  import time via `MODEL_REGISTRY`.
- `model_downloader.py` maintains a local JSON cache at
  `<models_dir>/model-resgistry.json` (note: existing typo in the
  filename, preserved intentionally for compatibility) with a
  `cached-models` section recording, per model, the last verified
  `sha256`/`size`/`mtime`. This lets `ensure_model_available()` skip
  re-hashing an already-verified model file on every call, while still
  re-verifying automatically if the on-disk file changes or the
  registry's expected checksum changes (e.g. after a model update).
- `pumaguard-models/` (~2 GB) and `training-data/` (~12 GB) are real
  Git submodules (see `.gitmodules`), already initialized in this
  environment. They hold the actual model weights and
  verification/training images used by `make verify` and
  `make functional-python`. They're large — avoid unnecessary
  recursive searches or copies across them, and there's normally no
  need to re-fetch or re-init them.
