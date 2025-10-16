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
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

import requests
import yaml

logger = logging.getLogger("PumaGuard")

MODEL_TAG = "c3535fd37db833f93d2e77cad0734d7e8b681741"
MODEL_BASE_URI = (
    "https://github.com/PEEC-Nature-Youth-Group/pumaguard-models/raw"
)

_settings_file = Path(__file__).parent / "model-registry.yaml"
if not _settings_file.exists():
    raise FileNotFoundError("Could not open model registry")

with open(_settings_file, encoding="utf-8") as fd_registry:
    MODEL_REGISTRY: Dict[
        str, Dict[str, Union[str, Dict[str, Dict[str, str]]]]
    ] = yaml.load(fd_registry, Loader=yaml.SafeLoader)


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


def download_file(
    url: str,
    destination: Path,
    expected_sha256: Optional[str] = None,
    print_progress: bool = True,
) -> bool:
    """
    Download a file from URL to destination with progress reporting.

    Args:
        url: URL to download from
        destination: Local file path to save to
        expected_sha256: Optional SHA256 checksum for verification

    Returns:
        bool: True if download and verification successful
    """
    try:
        logger.info("Downloading %s to %s", url, destination)

        response = requests.get(url, stream=True, timeout=60)
        logger.debug("response: %s", response)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=25 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and print_progress:
                        percent = (downloaded / total_size) * 100
                        # pylint: disable=line-too-long
                        print(
                            f"\rDownload progress: {percent:.1f}% "
                            f"({downloaded/1024/1024:.1f}/{total_size/1024/1024:.1f} MB)",
                            end="",
                            flush=True,
                        )
            logger.info("Done downloading %s", url)

        # Verify checksum if provided
        if expected_sha256:
            if not verify_file_checksum(destination, expected_sha256):
                logger.error(
                    "Checksum verification failed for %s", destination
                )
                destination.unlink()  # Remove corrupted file
                return False
            logger.debug("Checksum verification passed for %s", destination)

        logger.info("Successfully downloaded %s", destination)
        return True

    except requests.HTTPError as e:
        logger.error("Failed to download %s: %s", url, e)
        if destination.exists():
            destination.unlink()  # Clean up partial download
        return False

    except Exception:
        logger.error("uncaught exception")
        raise


def assemble_model_fragments(
    fragment_paths: List[Path],
    output_path: Path,
    expected_sha256: Optional[str] = None,
) -> bool:
    """
    Assemble model fragments into a single file (equivalent
    to 'cat file* > output').

    Args:
        fragment_paths: List of paths to fragment files (in order)
        output_path: Path where assembled file should be written

    Returns:
        bool: True if assembly successful
    """
    try:
        logger.info(
            "Assembling %d fragments into %s", len(fragment_paths), output_path
        )

        with open(output_path, "wb") as output_file:
            for i, fragment_path in enumerate(fragment_paths):
                if not fragment_path.exists():
                    logger.error("Fragment %s does not exist", fragment_path)
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
            if not verify_file_checksum(output_path, expected_sha256):
                logger.error(
                    "Checksum verification failed for %s", output_path
                )
                output_path.unlink()  # Remove corrupted file
                return False
            logger.debug("Checksum verification passed for %s", output_path)

        logger.info("Successfully assembled model: %s", output_path)
        return True

    except OSError as e:
        logger.error("Failed to assemble fragments: %s", e)
        if output_path.exists():
            output_path.unlink()  # Clean up partial file
        return False


def download_model_fragments(
    fragment_urls: List[str],
    models_dir: Path,
    print_progress: bool = True,
) -> List[Path]:
    """
    Download all fragments for a split model.

    Args:
        fragment_urls: List of URLs to download fragments from
        models_dir: Directory to store fragments

    Returns:
        List[Path]: Paths to downloaded fragment files
    """
    fragment_paths: List[Path] = []

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
    if model_path.exists():
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
        logger.warning(
            "Model %s exists but failed checksum, re-downloading", model_name
        )
        model_path.unlink()

    model_info = MODEL_REGISTRY[model_name]

    # Handle fragmented models
    if "fragments" in model_info:
        fragment_urls: Dict[str, Dict[str, str]] = model_info[
            "fragments"
        ]  # type: ignore
        logger.info(
            "Downloading fragmented model %s (%d fragments)",
            model_name,
            len(fragment_urls),
        )

        logger.debug("fragment_urls = %s", fragment_urls)

        # Download all fragments
        fragment_paths: List[Path] = []
        for fragment_name, fragment_data in fragment_urls.items():
            url = MODEL_BASE_URI + "/" + MODEL_TAG + "/" + fragment_name
            if not download_file(
                url,
                models_dir / fragment_name,
                fragment_data["sha256"],
                print_progress=print_progress,
            ):
                raise RuntimeError(
                    f"Failed to download fragment: {fragment_name}"
                )
            fragment_paths.append(models_dir / fragment_name)

        # Assemble fragments into final model
        sha256 = model_info.get("sha256")
        if not isinstance(sha256, str):
            raise RuntimeError("Could not get sha256 for model assembly")
        if not assemble_model_fragments(fragment_paths, model_path, sha256):
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

    return model_path


def list_available_models() -> List[str]:
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
