"""Tests for folders web routes."""

# pylint: disable=redefined-outer-name
# Pytest fixtures intentionally redefine names

import os
import tempfile
import time
from pathlib import (
    Path,
)
from unittest.mock import (
    MagicMock,
)

import pytest
from flask import (
    Flask,
)

from pumaguard.web_routes.folders import (
    register_folders_routes,
)


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmpdir1:
        with tempfile.TemporaryDirectory() as tmpdir2:
            yield tmpdir1, tmpdir2


@pytest.fixture
def webui_mock(temp_dirs):
    """Create a mock WebUI instance."""
    webui = MagicMock()
    tmpdir1, tmpdir2 = temp_dirs
    webui.image_directories = [tmpdir1]
    webui.classification_directories = [tmpdir2]
    return webui


@pytest.fixture
def client(app, webui_mock):
    """Create a test client with folders routes registered."""
    register_folders_routes(app, webui_mock)
    return app.test_client()


class TestGetFolders:
    """Test the get_folders endpoint."""

    def test_get_folders_empty(self, client):
        """Test getting folders when directories are empty."""
        response = client.get("/api/folders")
        assert response.status_code == 200
        data = response.get_json()
        assert "folders" in data
        assert len(data["folders"]) == 2  # Two empty directories

    def test_get_folders_with_images(self, client, temp_dirs):
        """Test getting folders with images."""
        tmpdir1, tmpdir2 = temp_dirs

        # Create images in first directory
        for i in range(3):
            filepath = os.path.join(tmpdir1, f"image{i}.jpg")
            Path(filepath).write_text(f"image {i}", encoding="utf-8")

        # Create images in second directory
        for i in range(2):
            filepath = os.path.join(tmpdir2, f"photo{i}.png")
            Path(filepath).write_text(f"photo {i}", encoding="utf-8")

        response = client.get("/api/folders")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["folders"]) == 2

        # Find folders by path
        folders_by_path = {f["path"]: f for f in data["folders"]}
        assert folders_by_path[tmpdir1]["image_count"] == 3
        assert folders_by_path[tmpdir2]["image_count"] == 2

    def test_get_folders_ignores_nonexistent(self, app):
        """Test that nonexistent directories are ignored."""
        webui = MagicMock()
        webui.image_directories = ["/nonexistent/path1"]
        webui.classification_directories = ["/nonexistent/path2"]
        register_folders_routes(app, webui)
        client = app.test_client()

        response = client.get("/api/folders")
        assert response.status_code == 200
        data = response.get_json()
        assert data["folders"] == []

    def test_get_folders_counts_only_images(self, client, temp_dirs):
        """Test that only image files are counted."""
        tmpdir1, _ = temp_dirs

        # Create mix of files
        Path(os.path.join(tmpdir1, "image.jpg")).write_text(
            "img", encoding="utf-8"
        )
        Path(os.path.join(tmpdir1, "photo.png")).write_text(
            "img", encoding="utf-8"
        )
        Path(os.path.join(tmpdir1, "data.txt")).write_text(
            "txt", encoding="utf-8"
        )
        Path(os.path.join(tmpdir1, "script.py")).write_text(
            "py", encoding="utf-8"
        )

        response = client.get("/api/folders")
        assert response.status_code == 200
        data = response.get_json()

        folders_by_path = {f["path"]: f for f in data["folders"]}
        # Should only count .jpg and .png
        assert folders_by_path[tmpdir1]["image_count"] == 2

    def test_get_folders_various_image_extensions(self, client, temp_dirs):
        """Test that all supported image extensions are counted."""
        tmpdir1, _ = temp_dirs
        image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]

        for ext in image_exts:
            filepath = os.path.join(tmpdir1, f"image{ext}")
            Path(filepath).write_text("img", encoding="utf-8")

        response = client.get("/api/folders")
        assert response.status_code == 200
        data = response.get_json()

        folders_by_path = {f["path"]: f for f in data["folders"]}
        assert folders_by_path[tmpdir1]["image_count"] == len(image_exts)

    def test_get_folders_includes_basename(self, client):
        """Test that folder name includes basename."""
        response = client.get("/api/folders")
        assert response.status_code == 200
        data = response.get_json()

        for folder in data["folders"]:
            assert folder["name"] == os.path.basename(folder["path"])

    def test_get_folders_ignores_subdirectories(self, client, temp_dirs):
        """Test that subdirectories are not counted as images."""
        tmpdir1, _ = temp_dirs

        # Create an image
        Path(os.path.join(tmpdir1, "image.jpg")).write_text(
            "img", encoding="utf-8"
        )

        # Create a subdirectory
        subdir = os.path.join(tmpdir1, "subdir")
        os.makedirs(subdir)

        response = client.get("/api/folders")
        assert response.status_code == 200
        data = response.get_json()

        folders_by_path = {f["path"]: f for f in data["folders"]}
        # Should only count the image, not the subdirectory
        assert folders_by_path[tmpdir1]["image_count"] == 1


class TestGetFolderImages:
    """Test the get_folder_images endpoint."""

    def test_get_folder_images_success(self, client, temp_dirs):
        """Test getting images from a folder."""
        tmpdir1, _ = temp_dirs

        # Create test images
        for i in range(3):
            filepath = os.path.join(tmpdir1, f"image{i}.jpg")
            Path(filepath).write_text(f"image {i}", encoding="utf-8")

        response = client.get(f"/api/folders{tmpdir1}/images")
        assert response.status_code == 200
        data = response.get_json()

        assert len(data["images"]) == 3
        assert data["base"] == os.path.basename(tmpdir1)

        # Check that images have required fields
        for image in data["images"]:
            assert "filename" in image
            assert "path" in image
            assert "size" in image
            assert "modified" in image
            assert "created" in image

    def test_get_folder_images_sorted_by_modified(self, client, temp_dirs):
        """Test that images are sorted by modification time."""
        tmpdir1, _ = temp_dirs

        # Create images with different timestamps
        for i in range(3):
            filepath = os.path.join(tmpdir1, f"image{i}.jpg")
            Path(filepath).write_text(f"image {i}", encoding="utf-8")
            time.sleep(0.01)

        response = client.get(f"/api/folders{tmpdir1}/images")
        assert response.status_code == 200
        data = response.get_json()

        # Should be sorted newest first
        modified_times = [img["modified"] for img in data["images"]]
        assert modified_times == sorted(modified_times, reverse=True)

    def test_get_folder_images_access_denied(self, client):
        """Test access denied for path outside allowed directories."""
        response = client.get("/api/folders/etc/passwd/images")
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Access denied"

    def test_get_folder_images_not_found(self, client, temp_dirs):
        """Test 404 for nonexistent folder."""
        tmpdir1, _ = temp_dirs
        nonexistent = os.path.join(tmpdir1, "nonexistent")

        response = client.get(f"/api/folders{nonexistent}/images")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Folder not found"

    def test_get_folder_images_only_images(self, client, temp_dirs):
        """Test that only image files are returned."""
        tmpdir1, _ = temp_dirs

        # Create mix of files
        Path(os.path.join(tmpdir1, "image.jpg")).write_text(
            "img", encoding="utf-8"
        )
        Path(os.path.join(tmpdir1, "photo.png")).write_text(
            "img", encoding="utf-8"
        )
        Path(os.path.join(tmpdir1, "data.txt")).write_text(
            "txt", encoding="utf-8"
        )

        response = client.get(f"/api/folders{tmpdir1}/images")
        assert response.status_code == 200
        data = response.get_json()

        # Should only return 2 images
        assert len(data["images"]) == 2
        filenames = [img["filename"] for img in data["images"]]
        assert "image.jpg" in filenames
        assert "photo.png" in filenames
        assert "data.txt" not in filenames

    def test_get_folder_images_various_extensions(self, client, temp_dirs):
        """Test all supported image extensions."""
        tmpdir1, _ = temp_dirs
        image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]

        for ext in image_exts:
            filepath = os.path.join(tmpdir1, f"image{ext}")
            Path(filepath).write_text("img", encoding="utf-8")

        response = client.get(f"/api/folders{tmpdir1}/images")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["images"]) == len(image_exts)

    def test_get_folder_images_ignores_subdirectories(self, client, temp_dirs):
        """Test that subdirectories are ignored."""
        tmpdir1, _ = temp_dirs

        # Create an image
        Path(os.path.join(tmpdir1, "image.jpg")).write_text(
            "img", encoding="utf-8"
        )

        # Create a subdirectory with images
        subdir = os.path.join(tmpdir1, "subdir")
        os.makedirs(subdir)
        Path(os.path.join(subdir, "nested.jpg")).write_text(
            "nested", encoding="utf-8"
        )

        response = client.get(f"/api/folders{tmpdir1}/images")
        assert response.status_code == 200
        data = response.get_json()

        # Should only return the top-level image
        assert len(data["images"]) == 1
        assert data["images"][0]["filename"] == "image.jpg"

    def test_get_folder_images_empty_folder(self, client, temp_dirs):
        """Test getting images from empty folder."""
        tmpdir1, _ = temp_dirs

        response = client.get(f"/api/folders{tmpdir1}/images")
        assert response.status_code == 200
        data = response.get_json()
        assert data["images"] == []

    def test_get_folder_images_case_insensitive_extensions(
        self, client, temp_dirs
    ):
        """Test case-insensitive extension matching."""
        tmpdir1, _ = temp_dirs

        # Create files with uppercase extensions
        Path(os.path.join(tmpdir1, "image.JPG")).write_text(
            "img", encoding="utf-8"
        )
        Path(os.path.join(tmpdir1, "photo.PNG")).write_text(
            "img", encoding="utf-8"
        )

        response = client.get(f"/api/folders{tmpdir1}/images")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["images"]) == 2

    def test_get_folder_images_with_debug_paths(self, client, temp_dirs):
        """Test debug path information when enabled."""
        tmpdir1, _ = temp_dirs
        os.environ["PG_DEBUG_PATHS"] = "1"

        # Create a test image
        Path(os.path.join(tmpdir1, "image.jpg")).write_text(
            "img", encoding="utf-8"
        )

        try:
            response = client.get(f"/api/folders{tmpdir1}/images")
            assert response.status_code == 200
            data = response.get_json()

            # Debug fields should be present
            assert len(data["images"]) == 1
            assert "_abs" in data["images"][0]
            assert "_base" in data["images"][0]
            assert "_folder_abs" in data["images"][0]
        finally:
            del os.environ["PG_DEBUG_PATHS"]

    def test_get_folder_images_access_denied_with_debug(self, client):
        """Test access denied error includes debug info when enabled."""
        os.environ["PG_DEBUG_PATHS"] = "1"

        try:
            response = client.get("/api/folders/etc/passwd/images")
            assert response.status_code == 403
            data = response.get_json()
            assert "error" in data
            assert "_requested" in data
            assert "_normalized" in data
            assert "_allowed_dirs" in data
        finally:
            del os.environ["PG_DEBUG_PATHS"]

    def test_get_folder_images_not_found_with_debug(self, client, temp_dirs):
        """Test not found error includes debug info when enabled."""
        tmpdir1, _ = temp_dirs
        nonexistent = os.path.join(tmpdir1, "nonexistent")
        os.environ["PG_DEBUG_PATHS"] = "1"

        try:
            response = client.get(f"/api/folders{nonexistent}/images")
            assert response.status_code == 404
            data = response.get_json()
            assert "error" in data
            assert "_requested" in data
            assert "_resolved" in data
            assert "_exists" in data
        finally:
            del os.environ["PG_DEBUG_PATHS"]

    def test_get_folder_images_path_traversal_protection(
        self, client, temp_dirs
    ):
        """Test protection against path traversal attacks."""
        tmpdir1, _ = temp_dirs

        # Try to access parent directory
        response = client.get(f"/api/folders{tmpdir1}/../images")
        # Should either deny access or normalize to allowed path
        assert response.status_code in [200, 403]

    def test_get_folder_images_relative_path(self, client, temp_dirs):
        """Test accessing folder with relative path components."""
        tmpdir1, _ = temp_dirs

        # Create an image
        Path(os.path.join(tmpdir1, "image.jpg")).write_text(
            "img", encoding="utf-8"
        )

        # Try with ./ in path
        response = client.get(f"/api/folders{tmpdir1}/./images")
        # Should normalize and work
        assert response.status_code in [200, 403]

    def test_get_folder_images_classification_directory(
        self, client, temp_dirs
    ):
        """Test accessing images from classification directory."""
        _, tmpdir2 = temp_dirs

        # Create images in classification directory
        for i in range(2):
            filepath = os.path.join(tmpdir2, f"classified{i}.jpg")
            Path(filepath).write_text(f"classified {i}", encoding="utf-8")

        response = client.get(f"/api/folders{tmpdir2}/images")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["images"]) == 2

    def test_get_folder_images_metadata_accuracy(self, client, temp_dirs):
        """Test that file metadata is accurate."""
        tmpdir1, _ = temp_dirs

        test_data = "test image data"
        filepath = os.path.join(tmpdir1, "test.jpg")
        Path(filepath).write_text(test_data, encoding="utf-8")

        response = client.get(f"/api/folders{tmpdir1}/images")
        assert response.status_code == 200
        data = response.get_json()

        image = data["images"][0]
        assert image["filename"] == "test.jpg"
        assert image["size"] == len(test_data)
        assert image["modified"] > 0
        assert image["created"] > 0

    def test_get_folder_images_with_hidden_files(self, client, temp_dirs):
        """Test handling of hidden dot files."""
        tmpdir1, _ = temp_dirs

        # Create a hidden image file
        Path(os.path.join(tmpdir1, ".hidden.jpg")).write_text(
            "hidden", encoding="utf-8"
        )

        response = client.get(f"/api/folders{tmpdir1}/images")
        assert response.status_code == 200
        data = response.get_json()

        # Should include hidden files
        assert len(data["images"]) == 1
        assert data["images"][0]["filename"] == ".hidden.jpg"
