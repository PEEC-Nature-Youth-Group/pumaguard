"""
Model downloader utility for PumaGuard.
"""

import datetime
import hashlib
import json
import logging
import os
import shutil
from pathlib import (
    Path,
)

import requests
import yaml

logger = logging.getLogger("PumaGuard")

MODEL_TAG = "05db288bdef4c67ac54223ea6e359ff42fa4f946"
MODEL_BASE_URI = (
    "https://github.com/PEEC-Nature-Youth-Group/pumaguard-models/raw"
)

_settings_file = Path(__file__).parent / "model-registry.yaml"
if not _settings_file.exists():
    raise FileNotFoundError("Could not open model registry")

with open(_settings_file, encoding="utf-8") as fd_registry:
    MODEL_REGISTRY: dict[str, dict[str, str | dict[str, dict[str, str]]]] = (
        yaml.load(fd_registry, Loader=yaml.SafeLoader)
    )


def create_registry(models_dir: Path):
    """
    Create a new registry file in the cache directory.

    This file stores the checksums of the models cached.
    """
    registry_file = models_dir / "model-resgistry.json"
    if not registry_file.exists():
        logger.debug("Creating new registry at %s", registry_file)
        with open(registry_file, "w", encoding="utf-8") as fd:
            json.dump(
                {
                    "version": "1.0",
                    "created": datetime.datetime.now().isoformat(),
                    "last-updated": datetime.datetime.now().isoformat(),
                    "models": MODEL_REGISTRY,
                    "cached-models": {},
                },
                fd,
                indent=2,
                ensure_ascii=False,
            )
        logger.info("Created model registry at %s", registry_file)


def get_models_directory() -> Path:
    """
    Get the directory where models should be stored.
    Uses XDG_DATA_HOME or defaults to ~/.local/share/pumaguard/models
    """
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        models_dir = Path(xdg_data_home) / "pumaguard" / "models"
    else:
        models_dir = Path.home() / ".local" / "share" / "pumaguard" / "models"

    models_dir.mkdir(parents=True, exist_ok=True)

    create_registry(models_dir)

    return models_dir


def verify_file_checksum(file_path: Path, expected_sha256: str) -> bool:
    """
    Verify file checksum.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)

    computed_hash = sha256_hash.hexdigest()
    return computed_hash == expected_sha256


def download_file(  # pylint: disable=too-many-branches
    url: str,
    destination: Path,
    expected_sha256: str | None = None,
    print_progress: bool = True,
) -> bool:
    """
    Download a file from URL to destination with progress reporting.

    The file is downloaded to a temporary path first and only moved into
    place (atomically, via ``os.replace``) once the download (and, if
    requested, the checksum verification) has succeeded. This guarantees
    that a pre-existing, working file at ``destination`` is never deleted
    or truncated just because a *replacement* download failed (e.g.
    because the device has no network access) or was corrupted in
    transit.

    Args:
        url: URL to download from
        destination: Local file path to save to
        expected_sha256: Optional SHA256 checksum for verification

    Returns:
        bool: True if download and verification successful
    """
    tmp_destination = destination.with_name(destination.name + ".part")
    try:
        logger.info("Downloading %s to %s", url, destination)

        # Respect custom CA bundle if provided via environment or system path
        ca_bundle: str | None = None
        # Priority:
        # 1. explicit PumaGuard var
        # 2. then common envs
        # 3. then system bundle
        for var in (
            "PUMAGUARD_CA_BUNDLE",
            "REQUESTS_CA_BUNDLE",
            "SSL_CERT_FILE",
        ):
            val = os.environ.get(var)
            if val and Path(val).exists():
                ca_bundle = val
                break
        if ca_bundle is None:
            # Debian/Ubuntu system bundle
            sys_bundle = "/etc/ssl/certs/ca-certificates.crt"
            if Path(sys_bundle).exists():
                ca_bundle = sys_bundle

        response = requests.get(
            url,
            stream=True,
            timeout=60,
            verify=ca_bundle if ca_bundle else True,
        )
        logger.debug("response: %s", response)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(tmp_destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=25 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and print_progress:
                        percent = (downloaded / total_size) * 100
                        # pylint: disable=line-too-long
                        print(
                            f"\rDownload progress: {percent:.1f}% "
                            + f"({downloaded / 1024 / 1024:.1f}/{total_size / 1024 / 1024:.1f} MB)",
                            end="",
                            flush=True,
                        )
            logger.info("Done downloading %s", url)

        # Verify checksum if provided
        if expected_sha256:
            if not verify_file_checksum(tmp_destination, expected_sha256):
                logger.error(
                    "Checksum verification failed for %s", destination
                )
                tmp_destination.unlink()  # Remove corrupted temp file
                return False
            logger.debug("Checksum verification passed for %s", destination)

        # Only now that the download is known-good do we replace any
        # existing file at the destination. This is atomic on POSIX
        # filesystems, so a reader never observes a partially-written
        # file at `destination`.
        os.replace(tmp_destination, destination)

        logger.info("Successfully downloaded %s", destination)
        return True

    except requests.RequestException as e:
        # Covers connection errors, DNS failures, timeouts, HTTP errors,
        # etc. This is an expected failure mode (e.g. the device has no
        # network access) and must never take down the pre-existing
        # `destination` file with it.
        logger.error("Failed to download %s: %s", url, e)
        if tmp_destination.exists():
            tmp_destination.unlink()  # Clean up partial download
        return False

    except Exception:
        logger.error("uncaught exception")
        if tmp_destination.exists():
            tmp_destination.unlink()  # Clean up partial download
        raise


def assemble_model_fragments(
    fragment_paths: list[Path],
    output_path: Path,
    expected_sha256: str | None = None,
) -> bool:
    """
    Assemble model fragments into a single file (equivalent
    to 'cat file* > output').

    The fragments are assembled into a temporary file which is only
    moved into place (atomically) once assembly and checksum
    verification succeed. This ensures a pre-existing, working file at
    ``output_path`` is never clobbered by a failed or incomplete
    assembly attempt.

    Args:
        fragment_paths: List of paths to fragment files (in order)
        output_path: Path where assembled file should be written

    Returns:
        bool: True if assembly successful
    """
    tmp_output_path = output_path.with_name(output_path.name + ".part")
    try:
        logger.info(
            "Assembling %d fragments into %s", len(fragment_paths), output_path
        )

        with open(tmp_output_path, "wb") as output_file:
            for i, fragment_path in enumerate(fragment_paths):
                if not fragment_path.exists():
                    logger.error("Fragment %s does not exist", fragment_path)
                    tmp_output_path.unlink()
                    return False

                logger.debug(
                    "Adding fragment %d/%d: %s",
                    i + 1,
                    len(fragment_paths),
                    fragment_path,
                )

                with open(fragment_path, "rb") as fragment_file:
                    # Copy fragment to output file in chunks
                    while True:
                        chunk = fragment_file.read(8192)
                        if not chunk:
                            break
                        output_file.write(chunk)

        # Verify checksum if provided
        if expected_sha256:
            if not verify_file_checksum(tmp_output_path, expected_sha256):
                logger.error(
                    "Checksum verification failed for %s", output_path
                )
                tmp_output_path.unlink()  # Remove corrupted temp file
                return False
            logger.debug("Checksum verification passed for %s", output_path)

        os.replace(tmp_output_path, output_path)

        logger.info("Successfully assembled model: %s", output_path)
        return True

    except OSError as e:
        logger.error("Failed to assemble fragments: %s", e)
        if tmp_output_path.exists():
            tmp_output_path.unlink()  # Clean up partial file
        return False


def download_model_fragments(
    fragment_urls: list[str],
    models_dir: Path,
    print_progress: bool = True,
) -> list[Path]:
    """
    Download all fragments for a split model.

    Args:
        fragment_urls: List of URLs to download fragments from
        models_dir: Directory to store fragments

    Returns:
        List[Path]: Paths to downloaded fragment files
    """
    fragment_paths: list[Path] = []

    for _, url in enumerate(fragment_urls):
        # Extract fragment filename from URL
        fragment_name = url.split("/")[-1]
        fragment_path = models_dir / fragment_name

        if not fragment_path.exists():
            if not download_file(
                url, fragment_path, print_progress=print_progress
            ):
                raise RuntimeError(f"Failed to download fragment: {url}")

        fragment_paths.append(fragment_path)

    return fragment_paths


# pylint: disable=too-many-branches
def ensure_model_available(
    model_name: str, print_progress: bool = True
) -> Path:
    """
    Ensure a model is available locally, downloading and assembling
    if necessary.

    Args:
        model_name: Name of the model (must be in MODEL_REGISTRY)

    Returns:
        Path: Path to the local model file

    Raises:
        ValueError: If model_name not in registry
        RuntimeError: If download or assembly fails
    """
    if model_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model: {model_name}. "
            f"Available models: {list(MODEL_REGISTRY.keys())}"
        )

    models_dir = get_models_directory()
    model_path = models_dir / model_name

    logger.debug("model_path = %s", model_path)

    # Check if model already exists and is valid
    model_already_present = model_path.exists()
    if model_already_present:
        model_info = MODEL_REGISTRY[model_name]
        sha256 = model_info.get("sha256")
        if isinstance(sha256, str) and verify_file_checksum(
            model_path, sha256
        ):
            logger.debug(
                "Model %s already available at %s", model_name, model_path
            )
            return model_path
        if not isinstance(sha256, str):
            raise RuntimeError("Could not get sha256")
        # Intentionally *not* deleting the existing file here. Downloads
        # below are written atomically and only replace `model_path` once
        # a verified replacement is fully available, so the current
        # (checksum-mismatched) file is kept as a fallback in case a
        # refresh can't be completed (e.g. no network connectivity).
        logger.warning(
            "Model %s exists at %s but failed checksum verification; "
            "attempting to download a fresh copy. The existing file "
            "will be kept and used as a fallback if the download "
            "cannot be completed.",
            model_name,
            model_path,
        )

    model_info = MODEL_REGISTRY[model_name]

    try:
        # Handle fragmented models
        if "fragments" in model_info:
            fragment_urls: str | dict[str, dict[str, str]] = model_info[
                "fragments"
            ]
            logger.info(
                "Downloading fragmented model %s (%d fragments)",
                model_name,
                len(fragment_urls),
            )

            logger.debug("fragment_urls = %s", fragment_urls)

            # Download all fragments
            fragment_paths: list[Path] = []
            if not isinstance(fragment_urls, dict):
                raise RuntimeError("Unexpected type for fragment_urls")
            for fragment_name, fragment_data in fragment_urls.items():
                fragment_path = models_dir / fragment_name
                fragment_sha256 = fragment_data["sha256"]

                # If we already have a valid copy of this fragment
                # (e.g. from a previous, partially-completed download),
                # reuse it instead of hitting the network again. This
                # also allows fully offline recovery when only the
                # assembled model file was lost but its fragments are
                # still cached locally.
                if fragment_path.exists() and verify_file_checksum(
                    fragment_path, fragment_sha256
                ):
                    logger.debug(
                        "Fragment %s already cached at %s",
                        fragment_name,
                        fragment_path,
                    )
                else:
                    url = (
                        MODEL_BASE_URI + "/" + MODEL_TAG + "/" + fragment_name
                    )
                    if not download_file(
                        url,
                        fragment_path,
                        fragment_sha256,
                        print_progress=print_progress,
                    ):
                        raise RuntimeError(
                            f"Failed to download fragment: {fragment_name}"
                        )
                fragment_paths.append(fragment_path)

            # Assemble fragments into final model
            sha256 = model_info.get("sha256")
            if not isinstance(sha256, str):
                raise RuntimeError("Could not get sha256 for model assembly")
            if not assemble_model_fragments(
                fragment_paths, model_path, sha256
            ):
                raise RuntimeError(
                    f"Failed to assemble model fragments for: {model_name}"
                )

        # Handle single-file models
        else:
            url = MODEL_BASE_URI + "/" + MODEL_TAG + "/" + model_name
            sha256 = model_info.get("sha256")
            if not isinstance(sha256, str):
                raise RuntimeError(
                    f"Invalid or missing sha256 for model: {model_name}"
                )
            if not download_file(url, model_path, sha256, print_progress):
                raise RuntimeError(f"Failed to download model: {model_name}")
    except RuntimeError:
        if model_already_present and model_path.exists():
            logger.error(
                "Could not refresh model %s (download/assembly failed, "
                "possibly due to lack of network access); continuing to "
                "use the existing local copy at %s even though it failed "
                "checksum verification.",
                model_name,
                model_path,
            )
            return model_path
        raise

    return model_path


def list_available_models() -> list[str]:
    """
    List all available models in the registry.

    Returns:
        Dict: Mapping of model names to their URLs
    """
    return list(MODEL_REGISTRY.keys())


def clear_model_cache():
    """
    Clear all downloaded models from cache.
    """
    models_dir = get_models_directory()
    if models_dir.exists():
        shutil.rmtree(models_dir)
        logger.info("Cleared model cache: %s", models_dir)


def update_model():
    """
    Update a model to cache.
    """


def export_registry():
    """
    Export registry to standard out.
    """
    print(yaml.dump(MODEL_REGISTRY))


def cache_models():
    """
    Cache all available models.
    """
    for model_name in MODEL_REGISTRY:
        logger.info("Caching %s", model_name)
        ensure_model_available(model_name)
