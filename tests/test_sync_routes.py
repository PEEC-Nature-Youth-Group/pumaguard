"""Tests for sync routes (checksums and batch downloads)."""

# pylint: disable=redefined-outer-name,unused-variable
# Pytest fixtures intentionally redefine names; some fixture returns are unused

import hashlib
import io
import json
import zipfile
from unittest.mock import (
    MagicMock,
)

import pytest
from flask import (
    Flask,
)

from pumaguard.web_routes.sync import (
    register_sync_routes,
)
from pumaguard.web_ui import (
    WebUI,
)


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories with test files."""
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "output"
    image_dir.mkdir()
    output_dir.mkdir()

    # Create test files
    file1 = image_dir / "image1.jpg"
    file2 = image_dir / "image2.jpg"
    file3 = output_dir / "classified1.jpg"

    file1.write_bytes(b"fake image data 1")
    file2.write_bytes(b"fake image data 2")
    file3.write_bytes(b"fake classified data")

    return {
        "image_dir": str(image_dir),
        "output_dir": str(output_dir),
        "file1": str(file1),
        "file2": str(file2),
        "file3": str(file3),
    }


@pytest.fixture
def test_app(temp_dirs):
    """Create a test Flask app with sync routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    # Create a mock WebUI instance
    webui = MagicMock(spec=WebUI)
    webui.image_directories = [temp_dirs["image_dir"]]
    webui.classification_directories = [temp_dirs["output_dir"]]

    register_sync_routes(app, webui)

    return app, webui


def calculate_checksum(filepath):
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def test_calculate_checksums_matching(test_app, temp_dirs):
    """Test POST /api/sync/checksums with matching checksums."""
    app, webui = test_app
    client = app.test_client()

    # Calculate actual checksum
    file1_checksum = calculate_checksum(temp_dirs["file1"])

    payload = {"files": {temp_dirs["file1"]: file1_checksum}}

    response = client.post(
        "/api/sync/checksums",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "files_to_download" in data
    assert len(data["files_to_download"]) == 0  # Checksums match
    assert data["total"] == 0


def test_calculate_checksums_mismatch(test_app, temp_dirs):
    """Test POST /api/sync/checksums with mismatched checksums."""
    app, webui = test_app
    client = app.test_client()

    # Use wrong checksum
    wrong_checksum = "0" * 64

    payload = {"files": {temp_dirs["file1"]: wrong_checksum}}

    response = client.post(
        "/api/sync/checksums",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["files_to_download"]) == 1
    assert data["total"] == 1

    # Verify file info
    file_info = data["files_to_download"][0]
    assert file_info["path"] == temp_dirs["file1"]
    assert "checksum" in file_info
    assert "size" in file_info
    assert "modified" in file_info


def test_calculate_checksums_bad_request(
    test_app, temp_dirs
):  # pylint: disable=unused-argument
    """Test POST /api/sync/checksums with multiple files."""
    app, webui = test_app
    client = app.test_client()

    file1_checksum = calculate_checksum(temp_dirs["file1"])
    wrong_checksum = "0" * 64

    payload = {
        "files": {
            temp_dirs["file1"]: file1_checksum,  # Matches
            temp_dirs["file2"]: wrong_checksum,  # Doesn't match
        }
    }

    response = client.post(
        "/api/sync/checksums",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["files_to_download"]) == 1  # Only file2
    assert data["total"] == 1


def test_calculate_checksums_no_files_provided(test_app):
    """Test POST /api/sync/checksums with no files."""
    app, webui = test_app
    client = app.test_client()

    payload = {}

    response = client.post(
        "/api/sync/checksums",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No files provided"


def test_calculate_checksums_empty_files_dict(test_app):
    """Test POST /api/sync/checksums with empty files dict."""
    app, webui = test_app
    client = app.test_client()

    payload = {"files": {}}

    response = client.post(
        "/api/sync/checksums",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["files_to_download"]) == 0
    assert data["total"] == 0


def test_calculate_checksums_no_json_body(test_app):
    """Test POST /api/sync/checksums with no JSON body."""
    app, webui = test_app
    client = app.test_client()

    response = client.post("/api/sync/checksums")

    # Flask returns 415 when no content-type is set
    assert response.status_code == 415


def test_calculate_checksums_nonexistent_file(test_app):
    """Test POST /api/sync/checksums with nonexistent file."""
    app, webui = test_app
    client = app.test_client()

    payload = {"files": {"/nonexistent/file.jpg": "abc123"}}

    response = client.post(
        "/api/sync/checksums",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    # Nonexistent files should be ignored
    assert len(data["files_to_download"]) == 0


def test_calculate_checksums_path_traversal_attack(
    test_app, temp_dirs
):  # pylint: disable=unused-argument
    """Test POST /api/sync/checksums prevents path traversal."""
    app, webui = test_app
    client = app.test_client()

    # Try to access file outside allowed directories
    outside_file = "/etc/passwd"

    payload = {"files": {outside_file: "abc123"}}

    response = client.post(
        "/api/sync/checksums",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    # Should not return files outside allowed directories
    assert len(data["files_to_download"]) == 0


def test_calculate_checksums_no_files(
    test_app, temp_dirs
):  # pylint: disable=unused-argument
    """Test POST /api/sync/checksums with relative paths."""
    app, webui = test_app
    client = app.test_client()

    # Use relative path
    relative_path = "image1.jpg"
    wrong_checksum = "0" * 64

    payload = {"files": {relative_path: wrong_checksum}}

    response = client.post(
        "/api/sync/checksums",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    # Should find file in allowed directories
    assert len(data["files_to_download"]) == 1


def test_download_single_file(test_app, temp_dirs):
    """Test POST /api/sync/download with single file."""
    app, webui = test_app
    client = app.test_client()

    payload = {"files": [temp_dirs["file1"]]}

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    # Should return file directly
    assert response.data == b"fake image data 1"


def test_download_multiple_files_as_zip(test_app, temp_dirs):
    """Test POST /api/sync/download with multiple files returns zip."""
    app, webui = test_app
    client = app.test_client()

    payload = {"files": [temp_dirs["file1"], temp_dirs["file2"]]}

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.mimetype == "application/zip"

    # Verify it's a valid zip file
    zip_data = io.BytesIO(response.data)
    with zipfile.ZipFile(zip_data, "r") as zf:
        namelist = zf.namelist()
        assert "image1.jpg" in namelist
        assert "image2.jpg" in namelist

        # Verify content
        assert zf.read("image1.jpg") == b"fake image data 1"
        assert zf.read("image2.jpg") == b"fake image data 2"


def test_download_no_files_provided(test_app):
    """Test POST /api/sync/download with no files."""
    app, webui = test_app
    client = app.test_client()

    payload = {}

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No files provided"


def test_download_empty_files_list(test_app):
    """Test POST /api/sync/download with empty files list."""
    app, webui = test_app
    client = app.test_client()

    payload = {"files": []}

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No valid files to download"


def test_download_nonexistent_file(test_app):
    """Test POST /api/sync/download with nonexistent file."""
    app, webui = test_app
    client = app.test_client()

    payload = {"files": ["/nonexistent/file.jpg"]}

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No valid files to download"


def test_download_path_traversal_attack(test_app):
    """Test POST /api/sync/download prevents path traversal."""
    app, webui = test_app
    client = app.test_client()

    # Try to access file outside allowed directories
    payload = {"files": ["/etc/passwd"]}

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No valid files to download"


def test_download_mixed_valid_invalid_files(test_app, temp_dirs):
    """Test POST /api/sync/download with mix of valid and invalid files."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "files": [
            temp_dirs["file1"],  # Valid
            "/nonexistent/file.jpg",  # Invalid
        ]
    }

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    # Should return single valid file directly
    assert response.data == b"fake image data 1"


def test_download_relative_path(
    test_app, temp_dirs
):  # pylint: disable=unused-argument
    """Test POST /api/sync/download with relative path."""
    app, webui = test_app
    client = app.test_client()

    payload = {"files": ["image1.jpg"]}

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    # Should find file in allowed directories
    assert response.data == b"fake image data 1"


def test_download_from_classification_directory(test_app, temp_dirs):
    """Test POST /api/sync/download from classification directory."""
    app, webui = test_app
    client = app.test_client()

    payload = {"files": [temp_dirs["file3"]]}

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.data == b"fake classified data"


def test_download_no_json_body(test_app):
    """Test POST /api/sync/download with no JSON body."""
    app, webui = test_app
    client = app.test_client()

    response = client.post("/api/sync/download")

    # Flask returns 415 when no content-type is set
    assert response.status_code == 415


def test_calculate_checksums_classification_directory(test_app, temp_dirs):
    """Test POST /api/sync/checksums with classification files."""
    app, webui = test_app
    client = app.test_client()

    wrong_checksum = "0" * 64

    payload = {"files": {temp_dirs["file3"]: wrong_checksum}}

    response = client.post(
        "/api/sync/checksums",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["files_to_download"]) == 1


def test_download_zip_with_three_files(test_app, temp_dirs):
    """Test POST /api/sync/download with three files creates proper zip."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "files": [
            temp_dirs["file1"],
            temp_dirs["file2"],
            temp_dirs["file3"],
        ]
    }

    response = client.post(
        "/api/sync/download",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.mimetype == "application/zip"

    # Verify all three files are in zip
    zip_data = io.BytesIO(response.data)
    with zipfile.ZipFile(zip_data, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 3
        assert "image1.jpg" in namelist
        assert "image2.jpg" in namelist
        assert "classified1.jpg" in namelist
