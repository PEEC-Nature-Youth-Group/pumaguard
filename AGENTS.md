# Agent Instructions for pumaguard

Notes for coding agents working in this repository, covering tooling
quirks discovered while working in this sandboxed environment.

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
