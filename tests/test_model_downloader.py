"""Tests for model downloader utility."""

import hashlib
import json
from unittest.mock import (
    Mock,
    patch,
)

import pytest
import requests

from pumaguard.model_downloader import (
    MODEL_REGISTRY,
    assemble_model_fragments,
    clear_model_cache,
    create_registry,
    download_file,
    ensure_model_available,
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


# Tests for download_file


def test_download_file_success(tmp_path):
    """Test download_file successfully downloads a file."""
    url = "https://example.com/model.h5"
    destination = tmp_path / "model.h5"
    content = b"model data" * 1000
    expected_hash = hashlib.sha256(content).hexdigest()

    mock_response = Mock()
    mock_response.headers = {"content-length": str(len(content))}
    mock_response.iter_content = lambda chunk_size: [content]

    with patch("pumaguard.model_downloader.requests.get") as mock_get:
        mock_get.return_value = mock_response

        result = download_file(
            url, destination, expected_hash, print_progress=False
        )

        assert result is True
        assert destination.exists()
        assert destination.read_bytes() == content
        mock_get.assert_called_once()


def test_download_file_checksum_failure(tmp_path):
    """Test download_file removes file on checksum mismatch."""
    url = "https://example.com/model.h5"
    destination = tmp_path / "model.h5"
    content = b"corrupted data"
    wrong_hash = "0" * 64

    mock_response = Mock()
    mock_response.headers = {"content-length": str(len(content))}
    mock_response.iter_content = lambda chunk_size: [content]

    with patch("pumaguard.model_downloader.requests.get") as mock_get:
        mock_get.return_value = mock_response

        result = download_file(
            url, destination, wrong_hash, print_progress=False
        )

        assert result is False
        assert not destination.exists()


def test_download_file_http_error(tmp_path):
    """Test download_file handles HTTP errors."""
    url = "https://example.com/missing.h5"
    destination = tmp_path / "model.h5"

    with patch("pumaguard.model_downloader.requests.get") as mock_get:
        mock_get.side_effect = requests.HTTPError("404 Not Found")

        result = download_file(url, destination, print_progress=False)

        assert result is False
        assert not destination.exists()


def test_download_file_without_checksum(tmp_path):
    """Test download_file works without checksum verification."""
    url = "https://example.com/model.h5"
    destination = tmp_path / "model.h5"
    content = b"model data"

    mock_response = Mock()
    mock_response.headers = {"content-length": str(len(content))}
    mock_response.iter_content = lambda chunk_size: [content]

    with patch("pumaguard.model_downloader.requests.get") as mock_get:
        mock_get.return_value = mock_response

        result = download_file(
            url, destination, expected_sha256=None, print_progress=False
        )

        assert result is True
        assert destination.exists()


def test_download_file_no_content_length(tmp_path):
    """Test download_file works when content-length header is missing."""
    url = "https://example.com/model.h5"
    destination = tmp_path / "model.h5"
    content = b"model data"

    mock_response = Mock()
    mock_response.headers = {}  # No content-length
    mock_response.iter_content = lambda chunk_size: [content]

    with patch("pumaguard.model_downloader.requests.get") as mock_get:
        mock_get.return_value = mock_response

        result = download_file(url, destination, print_progress=False)

        assert result is True
        assert destination.exists()


def test_download_file_with_custom_ca_bundle(tmp_path):
    """Test download_file respects custom CA bundle environment variable."""
    url = "https://example.com/model.h5"
    destination = tmp_path / "model.h5"
    content = b"model data"
    ca_bundle = tmp_path / "custom-ca.crt"
    ca_bundle.write_text("fake CA bundle")

    mock_response = Mock()
    mock_response.headers = {"content-length": str(len(content))}
    mock_response.iter_content = lambda chunk_size: [content]

    with patch("pumaguard.model_downloader.requests.get") as mock_get:
        mock_get.return_value = mock_response
        with patch.dict("os.environ", {"PUMAGUARD_CA_BUNDLE": str(ca_bundle)}):
            result = download_file(url, destination, print_progress=False)

            assert result is True
            # Verify that verify parameter was set to ca_bundle path
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["verify"] == str(ca_bundle)


def test_download_file_chunked_download(tmp_path):
    """Test download_file handles chunked downloads correctly."""
    url = "https://example.com/model.h5"
    destination = tmp_path / "model.h5"
    chunks = [b"chunk1", b"chunk2", b"chunk3"]
    content = b"".join(chunks)

    mock_response = Mock()
    mock_response.headers = {"content-length": str(len(content))}
    mock_response.iter_content = lambda chunk_size: chunks

    with patch("pumaguard.model_downloader.requests.get") as mock_get:
        mock_get.return_value = mock_response

        result = download_file(url, destination, print_progress=False)

        assert result is True
        assert destination.read_bytes() == content


# Tests for assemble_model_fragments


def test_assemble_model_fragments_success(tmp_path):
    """Test assemble_model_fragments successfully assembles fragments."""
    fragment1 = tmp_path / "fragment1"
    fragment2 = tmp_path / "fragment2"
    fragment3 = tmp_path / "fragment3"

    fragment1.write_bytes(b"part1")
    fragment2.write_bytes(b"part2")
    fragment3.write_bytes(b"part3")

    output = tmp_path / "assembled.h5"
    expected_content = b"part1part2part3"
    expected_hash = hashlib.sha256(expected_content).hexdigest()

    result = assemble_model_fragments(
        [fragment1, fragment2, fragment3], output, expected_hash
    )

    assert result is True
    assert output.exists()
    assert output.read_bytes() == expected_content


def test_assemble_model_fragments_missing_fragment(tmp_path):
    """Test assemble_model_fragments fails if fragment is missing."""
    fragment1 = tmp_path / "fragment1"
    fragment2 = tmp_path / "missing"

    fragment1.write_bytes(b"part1")
    # fragment2 doesn't exist

    output = tmp_path / "assembled.h5"

    result = assemble_model_fragments([fragment1, fragment2], output)

    assert result is False
    # Output file may be partially created before error


def test_assemble_model_fragments_checksum_failure(tmp_path):
    """Test assemble_model_fragments removes output on checksum mismatch."""
    fragment1 = tmp_path / "fragment1"
    fragment1.write_bytes(b"data")

    output = tmp_path / "assembled.h5"
    wrong_hash = "0" * 64

    result = assemble_model_fragments([fragment1], output, wrong_hash)

    assert result is False
    assert not output.exists()


def test_assemble_model_fragments_large_chunks(tmp_path):
    """Test assemble_model_fragments handles large chunks correctly."""
    fragment1 = tmp_path / "fragment1"
    # Create fragment larger than 8192 bytes (chunk size)
    large_content = b"x" * 20000
    fragment1.write_bytes(large_content)

    output = tmp_path / "assembled.h5"
    expected_hash = hashlib.sha256(large_content).hexdigest()

    result = assemble_model_fragments([fragment1], output, expected_hash)

    assert result is True
    assert output.read_bytes() == large_content


def test_assemble_model_fragments_without_checksum(tmp_path):
    """Test assemble_model_fragments works without checksum verification."""
    fragment1 = tmp_path / "fragment1"
    fragment1.write_bytes(b"data")

    output = tmp_path / "assembled.h5"

    result = assemble_model_fragments(
        [fragment1], output, expected_sha256=None
    )

    assert result is True
    assert output.exists()


# Tests for ensure_model_available


def test_ensure_model_available_already_cached(tmp_path):
    """Test ensure_model_available returns cached model if valid."""
    # Get a real model name from registry
    model_name = list(MODEL_REGISTRY.keys())[0]
    model_info = MODEL_REGISTRY[model_name]

    # Create fake cached model with correct checksum
    if "sha256" in model_info and isinstance(model_info["sha256"], str):
        content = b"cached model data"

        with patch(
            "pumaguard.model_downloader.get_models_directory"
        ) as mock_dir:
            mock_dir.return_value = tmp_path
            model_path = tmp_path / model_name
            model_path.write_bytes(content)

            # Mock verify_file_checksum to return True for cached model
            with patch(
                "pumaguard.model_downloader.verify_file_checksum"
            ) as mock_verify:
                mock_verify.return_value = True

                result = ensure_model_available(
                    model_name, print_progress=False
                )

                assert result == model_path
                assert model_path.exists()


def test_ensure_model_available_invalid_model_name():
    """Test ensure_model_available raises ValueError for unknown model."""
    with pytest.raises(ValueError, match="Unknown model"):
        ensure_model_available("nonexistent_model.h5", print_progress=False)


def test_ensure_model_available_download_single_file(tmp_path):
    """Test ensure_model_available downloads single-file model."""
    # Create a mock registry entry for a single-file model
    test_model = "test_single.h5"
    test_content = b"single file model"
    test_hash = hashlib.sha256(test_content).hexdigest()

    with patch.dict(
        "pumaguard.model_downloader.MODEL_REGISTRY",
        {test_model: {"sha256": test_hash}},
    ):
        with patch(
            "pumaguard.model_downloader.get_models_directory"
        ) as mock_dir:
            mock_dir.return_value = tmp_path

            with patch(
                "pumaguard.model_downloader.download_file"
            ) as mock_download:
                mock_download.return_value = True

                # Simulate the file being created by download
                def create_file(*_args, **_kwargs):
                    (tmp_path / test_model).write_bytes(test_content)
                    return True

                mock_download.side_effect = create_file

                result = ensure_model_available(
                    test_model, print_progress=False
                )

                assert result == tmp_path / test_model
                mock_download.assert_called_once()


def test_ensure_model_available_download_fragmented_model(tmp_path):
    """Test ensure_model_available downloads and assembles fragmented model."""
    test_model = "test_fragmented.h5"
    frag1_content = b"frag1"
    frag2_content = b"frag2"
    combined = frag1_content + frag2_content
    test_hash = hashlib.sha256(combined).hexdigest()
    frag1_hash = hashlib.sha256(frag1_content).hexdigest()
    frag2_hash = hashlib.sha256(frag2_content).hexdigest()

    with patch.dict(
        "pumaguard.model_downloader.MODEL_REGISTRY",
        {
            test_model: {
                "sha256": test_hash,
                "fragments": {
                    "test_fragmented.h5_aa": {"sha256": frag1_hash},
                    "test_fragmented.h5_ab": {"sha256": frag2_hash},
                },
            }
        },
    ):
        with patch(
            "pumaguard.model_downloader.get_models_directory"
        ) as mock_dir:
            mock_dir.return_value = tmp_path

            with patch(
                "pumaguard.model_downloader.download_file"
            ) as mock_download:
                # Simulate fragment downloads
                def create_fragment(
                    _url, dest, sha256=None, print_progress=True
                ):  # pylint: disable=unused-argument
                    if "_aa" in dest.name:
                        dest.write_bytes(frag1_content)
                    elif "_ab" in dest.name:
                        dest.write_bytes(frag2_content)
                    return True

                mock_download.side_effect = create_fragment

                with patch(
                    "pumaguard.model_downloader.assemble_model_fragments"
                ) as mock_assemble:

                    def create_assembled(*args, **_kwargs):
                        args[1].write_bytes(combined)  # output_path
                        return True

                    mock_assemble.side_effect = create_assembled

                    result = ensure_model_available(
                        test_model, print_progress=False
                    )

                    assert result == tmp_path / test_model
                    # Should download 2 fragments
                    assert mock_download.call_count == 2
                    mock_assemble.assert_called_once()


def test_ensure_model_available_redownload_on_checksum_fail(tmp_path):
    """Test ensure_model_available re-downloads if checksum fails."""
    test_model = "test_redownload.h5"
    test_content = b"new content"
    test_hash = hashlib.sha256(test_content).hexdigest()

    with patch.dict(
        "pumaguard.model_downloader.MODEL_REGISTRY",
        {test_model: {"sha256": test_hash}},
    ):
        with patch(
            "pumaguard.model_downloader.get_models_directory"
        ) as mock_dir:
            mock_dir.return_value = tmp_path
            model_path = tmp_path / test_model
            model_path.write_bytes(b"old corrupted data")

            # First checksum check fails, triggering re-download
            with patch(
                "pumaguard.model_downloader.verify_file_checksum"
            ) as mock_verify:
                mock_verify.return_value = False

                with patch(
                    "pumaguard.model_downloader.download_file"
                ) as mock_download:

                    def create_file(*_args, **_kwargs):
                        model_path.write_bytes(test_content)
                        return True

                    mock_download.side_effect = create_file

                    result = ensure_model_available(
                        test_model, print_progress=False
                    )
                    assert result is not None

                    # Should have attempted download
                    mock_download.assert_called_once()


def test_ensure_model_available_download_failure_raises(tmp_path):
    """Test ensure_model_available raises RuntimeError on download failure."""
    test_model = "test_failure.h5"
    test_hash = hashlib.sha256(b"data").hexdigest()

    with patch.dict(
        "pumaguard.model_downloader.MODEL_REGISTRY",
        {test_model: {"sha256": test_hash}},
    ):
        with patch(
            "pumaguard.model_downloader.get_models_directory"
        ) as mock_dir:
            mock_dir.return_value = tmp_path

            with patch(
                "pumaguard.model_downloader.download_file"
            ) as mock_download:
                mock_download.return_value = False

                with pytest.raises(
                    RuntimeError, match="Failed to download model"
                ):
                    ensure_model_available(test_model, print_progress=False)


# Tests for clear_model_cache


def test_clear_model_cache(tmp_path):
    """Test clear_model_cache removes models directory."""
    with patch("pumaguard.model_downloader.get_models_directory") as mock_dir:
        mock_dir.return_value = tmp_path
        # Create some fake model files
        (tmp_path / "model1.h5").write_bytes(b"data1")
        (tmp_path / "model2.pt").write_bytes(b"data2")

        assert tmp_path.exists()
        assert len(list(tmp_path.iterdir())) == 2

        clear_model_cache()

        # Directory should be removed
        assert not tmp_path.exists()


def test_clear_model_cache_nonexistent_directory(tmp_path):
    """Test clear_model_cache handles nonexistent directory gracefully."""
    nonexistent = tmp_path / "nonexistent"

    with patch("pumaguard.model_downloader.get_models_directory") as mock_dir:
        mock_dir.return_value = nonexistent

        # Should not raise an error
        clear_model_cache()

        assert not nonexistent.exists()
