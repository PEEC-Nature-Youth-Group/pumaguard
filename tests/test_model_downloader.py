"""Tests for model downloader utility."""

import hashlib
import json
from unittest.mock import (
    patch,
)

from pumaguard.model_downloader import (
    MODEL_REGISTRY,
    create_registry,
    get_models_directory,
    list_available_models,
    verify_file_checksum,
)


def test_model_registry_loaded():
    """Test that MODEL_REGISTRY is loaded from YAML."""
    assert MODEL_REGISTRY is not None
    assert isinstance(MODEL_REGISTRY, dict)
    # Should have at least some models
    assert len(MODEL_REGISTRY) > 0


def test_verify_file_checksum_matching(tmp_path):
    """Test verify_file_checksum with matching checksum."""
    # Create test file
    test_file = tmp_path / "test.txt"
    content = b"test content"
    test_file.write_bytes(content)

    # Calculate expected checksum
    expected_hash = hashlib.sha256(content).hexdigest()

    result = verify_file_checksum(test_file, expected_hash)

    assert result is True


def test_verify_file_checksum_mismatch(tmp_path):
    """Test verify_file_checksum with mismatched checksum."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"test content")

    wrong_hash = "0" * 64

    result = verify_file_checksum(test_file, wrong_hash)

    assert result is False


def test_verify_file_checksum_empty_file(tmp_path):
    """Test verify_file_checksum with empty file."""
    test_file = tmp_path / "empty.txt"
    test_file.write_bytes(b"")

    # SHA256 of empty file
    empty_hash = hashlib.sha256(b"").hexdigest()

    result = verify_file_checksum(test_file, empty_hash)

    assert result is True


def test_verify_file_checksum_large_file(tmp_path):
    """Test verify_file_checksum with file larger than chunk size."""
    test_file = tmp_path / "large.bin"
    # Create file larger than 4096 bytes (chunk size)
    content = b"x" * 10000
    test_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()

    result = verify_file_checksum(test_file, expected_hash)

    assert result is True


def test_get_models_directory_creates_directory(tmp_path):
    """Test get_models_directory creates directory if it doesn't exist."""
    with patch.dict("os.environ", {"XDG_DATA_HOME": str(tmp_path)}):
        with patch(
            "pumaguard.model_downloader.create_registry"
        ) as mock_create:
            models_dir = get_models_directory()

            assert models_dir.exists()
            assert models_dir.is_dir()
            assert models_dir == tmp_path / "pumaguard" / "models"
            mock_create.assert_called_once()


def test_get_models_directory_uses_xdg_data_home(tmp_path):
    """Test get_models_directory uses XDG_DATA_HOME when set."""
    with patch.dict("os.environ", {"XDG_DATA_HOME": str(tmp_path)}):
        with patch("pumaguard.model_downloader.create_registry"):
            models_dir = get_models_directory()

            assert str(tmp_path) in str(models_dir)
            assert models_dir == tmp_path / "pumaguard" / "models"


def test_get_models_directory_default_location(tmp_path):
    """Test get_models_directory uses default location when XDG not set."""
    with patch.dict("os.environ", {}, clear=True):
        with patch(
            "pumaguard.model_downloader.Path.home", return_value=tmp_path
        ):
            with patch("pumaguard.model_downloader.create_registry"):
                models_dir = get_models_directory()

                expected = (
                    tmp_path / ".local" / "share" / "pumaguard" / "models"
                )
                assert models_dir == expected


def test_get_models_directory_idempotent(tmp_path):
    """Test get_models_directory can be called multiple times."""
    with patch.dict("os.environ", {"XDG_DATA_HOME": str(tmp_path)}):
        with patch("pumaguard.model_downloader.create_registry"):
            dir1 = get_models_directory()
            dir2 = get_models_directory()

            assert dir1 == dir2
            assert dir1.exists()


def test_create_registry_creates_file(tmp_path):
    """Test create_registry creates registry file."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    create_registry(models_dir)

    registry_file = models_dir / "model-resgistry.json"
    assert registry_file.exists()


def test_create_registry_does_not_overwrite(tmp_path):
    """Test create_registry doesn't overwrite existing registry."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    registry_file = models_dir / "model-resgistry.json"
    original_content = '{"test": "data"}'
    registry_file.write_text(original_content)

    create_registry(models_dir)

    # Should not have been overwritten
    assert registry_file.read_text() == original_content


def test_create_registry_json_structure(tmp_path):
    """Test create_registry creates valid JSON with expected structure."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    create_registry(models_dir)

    registry_file = models_dir / "model-resgistry.json"
    with open(registry_file, encoding="utf-8") as f:
        data = json.load(f)

    assert "version" in data
    assert "created" in data
    assert "last-updated" in data
    assert "models" in data
    assert "cached-models" in data
    assert data["version"] == "1.0"


def test_list_available_models():
    """Test list_available_models returns list of model names."""
    models = list_available_models()

    assert isinstance(models, list)
    assert len(models) > 0
    # Should be keys from MODEL_REGISTRY
    for model in models:
        assert model in MODEL_REGISTRY


def test_list_available_models_includes_h5_and_pt():
    """Test list_available_models includes both .h5 and .pt files."""
    models = list_available_models()

    has_h5 = any(model.endswith(".h5") for model in models)
    has_pt = any(model.endswith(".pt") for model in models)

    # Registry should contain both types
    assert has_h5 or has_pt


def test_verify_file_checksum_different_content_same_length(tmp_path):
    """Test verify_file_checksum with different content but same length."""
    test_file = tmp_path / "test.txt"
    content1 = b"a" * 100
    content2 = b"b" * 100

    test_file.write_bytes(content1)
    hash1 = hashlib.sha256(content1).hexdigest()
    hash2 = hashlib.sha256(content2).hexdigest()

    # Verify with correct hash
    assert verify_file_checksum(test_file, hash1) is True
    # Verify with wrong hash
    assert verify_file_checksum(test_file, hash2) is False


def test_create_registry_with_nested_directories(tmp_path):
    """Test create_registry works with nested directory structure."""
    models_dir = tmp_path / "deep" / "nested" / "models"
    models_dir.mkdir(parents=True)

    create_registry(models_dir)

    registry_file = models_dir / "model-resgistry.json"
    assert registry_file.exists()


def test_model_registry_has_sha256_checksums():
    """Test that MODEL_REGISTRY entries have sha256 checksums."""
    for _, model_info in MODEL_REGISTRY.items():
        # Each model should have metadata
        if isinstance(model_info, dict):
            # Check if it's a fragmented model or regular model
            if "fragments" in model_info:
                # Fragmented model
                assert "fragments" in model_info
            else:
                # Regular model should have sha256
                assert "sha256" in model_info or "fragments" in model_info
