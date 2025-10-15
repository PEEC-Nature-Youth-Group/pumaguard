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
MODEL_REGISTRY: Dict[str, Dict[str, Union[str, Dict[str, Dict[str, str]]]]] = {
    "puma_101425_efficientnetv2s.h5": {
        # pylint: disable=line-too-long
        "sha256": "48e2026d5da0cb2100b3d4306936925bb490f1e76e134646060c876ef5d127b0",
        "fragments": {
            "puma_101425_efficientnetv2s.h5_aa": {
                # pylint: disable=line-too-long
                "sha256": "7431170b2724a760a2d8b5451d9023c254f8bc4ad90fe550a76284b7c89362ea",
            },
            "puma_101425_efficientnetv2s.h5_ab": {
                # pylint: disable=line-too-long
                "sha256": "69c9b0e1f70c64cf9d2d548ab72eae772b94be6a39e5e690a65ff94ea72bef5a",
            },
            "puma_101425_efficientnetv2s.h5_ac": {
                # pylint: disable=line-too-long
                "sha256": "37d22e4c01de7ca30b748d6a1be46620a1685e47b37a051d98217ad2c8af68db",
            },
            "puma_101425_efficientnetv2s.h5_ad": {
                # pylint: disable=line-too-long
                "sha256": "cb1cf243494b8735014f42549991daf115fabe1beea5b58e4f6996b84b800de8",
            },
            "puma_101425_efficientnetv2s.h5_ae": {
                # pylint: disable=line-too-long
                "sha256": "77c9c5466a676b4370d1518a424f861f07df4773b1f0a538041e3896adbee65d",
            },
            "puma_101425_efficientnetv2s.h5_af": {
                # pylint: disable=line-too-long
                "sha256": "8f6362aede94a1523515fe9a9c78bc8376002c69b93596b0303d592f60cc5625",
            },
            "puma_101425_efficientnetv2s.h5_ag": {
                # pylint: disable=line-too-long
                "sha256": "511a0b6586dc28219f9e66992e48af0f2ae0528bc0666b2bee6d7f01042dfe0c",
            },
            "puma_101425_efficientnetv2s.h5_ah": {
                # pylint: disable=line-too-long
                "sha256": "5de7c756660c2a9b28853efab95dbde6bb1ca6715c4dff81abb768b05dd9a409",
            },
            "puma_101425_efficientnetv2s.h5_ai": {
                # pylint: disable=line-too-long
                "sha256": "2dd99904ad761605d8fc4ee9ad47ac26bbc1e3f5b12ca14c16c6dd969bb85772",
            },
            "puma_101425_efficientnetv2s.h5_aj": {
                # pylint: disable=line-too-long
                "sha256": "b1882e985355995361f8d0083f411502e3adef9e28c55207b4ac751355a0b0bf",
            },
            "puma_101425_efficientnetv2s.h5_ak": {
                # pylint: disable=line-too-long
                "sha256": "8cf7149311e0f54d664e099660a4bba0dd686fd5ad5937a77d95e4a5c275756e",
            },
            "puma_101425_efficientnetv2s.h5_al": {
                # pylint: disable=line-too-long
                "sha256": "89b691ead316d6b0910e7dd4116d737412c7ede29fd0eaf4052b09a417c23968",
            },
            "puma_101425_efficientnetv2s.h5_am": {
                # pylint: disable=line-too-long
                "sha256": "7a4ee577afd44e153cc9a4ba8cb1126591730d86137c15e6f95ed8ee6d1148ff",
            },
        },
    },
    "puma_cls_efficientnetv2s.h5": {
        "fragments": {
            "puma_cls_efficientnetv2s.h5_aa": {
                # pylint: disable=line-too-long
                "sha256": "46f31aef332ff86b2462316b530c4809bcd2232195ddbf22a1762158b1d3ffec",
            },
            "puma_cls_efficientnetv2s.h5_ab": {
                # pylint: disable=line-too-long
                "sha256": "81ba26fc90febff2d8c7136bb870c21c88fee485c515705981d9f41856188b55",
            },
            "puma_cls_efficientnetv2s.h5_ac": {
                # pylint: disable=line-too-long
                "sha256": "a9a498cd34948763b412bb202bc2f80b14a575b08360c2b4314eb7abacc07bf5",
            },
        },
        # pylint: disable=line-too-long
        "sha256": "de1d9ee617796b7aa9f9eba4b2527f94cb4e41c9a5ca1482cb2923f796aec8a2",
    },
    "puma_cls_efficientnetv2s_balanced.h5": {
        "fragments": {
            "puma_cls_efficientnetv2s_balanced.h5_aa": {
                # pylint: disable=line-too-long
                "sha256": "6a83f123438b9bfce408c8ffa5512326209ffd40559b54443b57265fb255b031",
            },
            "puma_cls_efficientnetv2s_balanced.h5_ab": {
                # pylint: disable=line-too-long
                "sha256": "48ccda0b7423b91abbcfadd21c79986e5a08a0a7ed1efc37c3a62c022e6c1095",
            },
            "puma_cls_efficientnetv2s_balanced.h5_ac": {
                # pylint: disable=line-too-long
                "sha256": "f57a02a2197cf4ec77a2980e030ba752903210d2b4755eab9b6e52a4fa18aaef",
            },
            "puma_cls_efficientnetv2s_balanced.h5_ad": {
                # pylint: disable=line-too-long
                "sha256": "c851f784a44e787ffa8af76b156281a59dfdc4869ab2ee01dc674641fa30ef9b",
            },
            "puma_cls_efficientnetv2s_balanced.h5_ae": {
                # pylint: disable=line-too-long
                "sha256": "9201635ca69a685d40d3363ae337a66db2f8e5a5784e21001796e058cb8ac456",
            },
            "puma_cls_efficientnetv2s_balanced.h5_af": {
                # pylint: disable=line-too-long
                "sha256": "ceca5eb868e07323cbf6de05fdfd2d65cced9cd5beb2bb4a3e229eee3bd2b095",
            },
            "puma_cls_efficientnetv2s_balanced.h5_ag": {
                # pylint: disable=line-too-long
                "sha256": "fb6ac1542d1cfd1f9afe831bde458e3ac046072d656fe5a1238fb58fbcc2c9c3",
            },
            "puma_cls_efficientnetv2s_balanced.h5_ah": {
                # pylint: disable=line-too-long
                "sha256": "95971f4c85a7f8dc3828c1debbe930ecef8ad1fc3e877421fa1d2fb557d6ca87",
            },
            "puma_cls_efficientnetv2s_balanced.h5_ai": {
                # pylint: disable=line-too-long
                "sha256": "caab8db040ac0d6d0e8c63fc26622ab9d3c8bfd574ed4a209f1accde79f32fe4",
            },
            "puma_cls_efficientnetv2s_balanced.h5_aj": {
                # pylint: disable=line-too-long
                "sha256": "826fafb20fd38e5c94e363b9896b1618f38fd5c56c36d42c852f4d594cc05cc7",
            },
            "puma_cls_efficientnetv2s_balanced.h5_ak": {
                # pylint: disable=line-too-long
                "sha256": "1558f805d4c16449b67533e36e7aff42568c859b6e87e374572e40e5460fe773",
            },
            "puma_cls_efficientnetv2s_balanced.h5_al": {
                # pylint: disable=line-too-long
                "sha256": "d4aa525c255579a701fbf9e85b8fe3dac42abacb7f8b8d57e58c79bd4e5a240c",
            },
            "puma_cls_efficientnetv2s_balanced.h5_am": {
                # pylint: disable=line-too-long
                "sha256": "938a3d929e4732ba799901cc37d65f80162018c3dfd4236e2d3a22f29a3e18e7",
            },
        },
        # pylint: disable=line-too-long
        "sha256": "c43e6505f9d987b9f624b2a5129a6baa3dd165f5c51989911fcc5e36002b1839",
    },
    "yolov8s.pt": {
        # pylint: disable=line-too-long
        "sha256": "1f47a78bf100391c2a140b7ac73a1caae18c32779be7d310658112f7ac9aa78a",
    },
    "yolov8s_balanced.pt": {
        # pylint: disable=line-too-long
        "sha256": "1f47a78bf100391c2a140b7ac73a1caae18c32779be7d310658112f7ac9aa78a",
    },
    "yolov8s_101425.pt": {
        # pylint: disable=line-too-long
        "sha256": "1f47a78bf100391c2a140b7ac73a1caae18c32779be7d310658112f7ac9aa78a",
    },
}


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


def list_available_models() -> Dict[str, str]:
    """
    List all available models in the registry.

    Returns:
        Dict: Mapping of model names to their URLs
    """
    return {
        name: info["url"]
        for name, info in MODEL_REGISTRY.items()
        if "url" in info and isinstance(info["url"], str)
    }


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
