"""Tests for photos web routes."""

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

from pumaguard.web_routes.photos import (
    register_photos_routes,
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
    """Create a test client with photos routes registered."""
    register_photos_routes(app, webui_mock)
    return app.test_client()


class TestGetPhotos:
    """Test the get_photos endpoint."""

    def test_get_photos_empty(self, client):
        """Test getting photos when directories are empty."""
        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()
        assert "photos" in data
        assert "total" in data
        assert data["photos"] == []
        assert data["total"] == 0

    def test_get_photos_with_images(self, client, temp_dirs):
        """Test getting photos with images in directories."""
        tmpdir1, tmpdir2 = temp_dirs

        # Create images in first directory
        for i in range(3):
            filepath = os.path.join(tmpdir1, f"image{i}.jpg")
            Path(filepath).write_text(f"image {i}", encoding="utf-8")

        # Create images in second directory
        for i in range(2):
            filepath = os.path.join(tmpdir2, f"photo{i}.png")
            Path(filepath).write_text(f"photo {i}", encoding="utf-8")

        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 5
        assert len(data["photos"]) == 5

    def test_get_photos_sorted_by_modified(self, client, temp_dirs):
        """Test that photos are sorted by modification time (newest first)."""
        tmpdir1, _ = temp_dirs

        # Create images with different timestamps
        for i in range(3):
            filepath = os.path.join(tmpdir1, f"image{i}.jpg")
            Path(filepath).write_text(f"image {i}", encoding="utf-8")
            time.sleep(0.01)

        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()

        # Should be sorted newest first
        modified_times = [photo["modified"] for photo in data["photos"]]
        assert modified_times == sorted(modified_times, reverse=True)

    def test_get_photos_includes_metadata(self, client, temp_dirs):
        """Test that photos include proper metadata."""
        tmpdir1, _ = temp_dirs
        test_data = "test image data"
        filepath = os.path.join(tmpdir1, "test.jpg")
        Path(filepath).write_text(test_data, encoding="utf-8")

        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()

        photo = data["photos"][0]
        assert photo["filename"] == "test.jpg"
        assert photo["path"] == filepath
        assert photo["directory"] == tmpdir1
        assert photo["size"] == len(test_data)
        assert "modified" in photo
        assert "created" in photo

    def test_get_photos_only_images(self, client, temp_dirs):
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
        Path(os.path.join(tmpdir1, "script.py")).write_text(
            "py", encoding="utf-8"
        )

        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()

        # Should only return 2 images
        assert data["total"] == 2
        filenames = [photo["filename"] for photo in data["photos"]]
        assert "image.jpg" in filenames
        assert "photo.png" in filenames

    def test_get_photos_various_extensions(self, client, temp_dirs):
        """Test all supported image extensions."""
        tmpdir1, _ = temp_dirs
        image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]

        for ext in image_exts:
            filepath = os.path.join(tmpdir1, f"image{ext}")
            Path(filepath).write_text("img", encoding="utf-8")

        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == len(image_exts)

    def test_get_photos_case_insensitive_extensions(self, client, temp_dirs):
        """Test case-insensitive extension matching."""
        tmpdir1, _ = temp_dirs

        # Create files with uppercase extensions
        Path(os.path.join(tmpdir1, "image.JPG")).write_text(
            "img", encoding="utf-8"
        )
        Path(os.path.join(tmpdir1, "photo.PNG")).write_text(
            "img", encoding="utf-8"
        )

        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 2

    def test_get_photos_ignores_nonexistent_directories(self, app):
        """Test that nonexistent directories don't cause errors."""
        webui = MagicMock()
        webui.image_directories = ["/nonexistent/path1"]
        webui.classification_directories = ["/nonexistent/path2"]
        register_photos_routes(app, webui)
        client = app.test_client()

        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()
        assert data["photos"] == []
        assert data["total"] == 0

    def test_get_photos_ignores_subdirectories(self, client, temp_dirs):
        """Test that subdirectories are not listed as photos."""
        tmpdir1, _ = temp_dirs

        # Create an image
        Path(os.path.join(tmpdir1, "image.jpg")).write_text(
            "img", encoding="utf-8"
        )

        # Create a subdirectory
        subdir = os.path.join(tmpdir1, "subdir")
        os.makedirs(subdir)

        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()

        # Should only include the image, not the subdirectory
        assert data["total"] == 1

    def test_get_photos_from_both_directory_types(self, client, temp_dirs):
        """Test photos from both image and classification directories."""
        tmpdir1, tmpdir2 = temp_dirs

        # Create image in watched directory
        Path(os.path.join(tmpdir1, "watched.jpg")).write_text(
            "watched", encoding="utf-8"
        )

        # Create image in classification directory
        Path(os.path.join(tmpdir2, "classified.jpg")).write_text(
            "classified", encoding="utf-8"
        )

        response = client.get("/api/photos")
        assert response.status_code == 200
        data = response.get_json()

        assert data["total"] == 2
        filenames = [photo["filename"] for photo in data["photos"]]
        assert "watched.jpg" in filenames
        assert "classified.jpg" in filenames


class TestGetPhoto:
    """Test the get_photo endpoint."""

    def test_get_photo_success(self, client, temp_dirs):
        """Test successfully retrieving a photo."""
        tmpdir1, _ = temp_dirs
        test_data = "test image data"
        filename = "test.jpg"
        filepath = os.path.join(tmpdir1, filename)
        Path(filepath).write_text(test_data, encoding="utf-8")

        response = client.get(f"/api/photos/{filename}")
        assert response.status_code == 200
        assert response.data.decode("utf-8") == test_data

    def test_get_photo_not_found(self, client):
        """Test 403 for nonexistent photo (no leak of file existence)."""
        response = client.get("/api/photos/nonexistent.jpg")
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Access denied"

    def test_get_photo_access_denied_outside_directories(self, client):
        """Test access denied for path outside allowed directories."""
        response = client.get("/api/photos/../../etc/passwd")
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Access denied"

    def test_get_photo_access_denied_non_image(self, client, temp_dirs):
        """Test access denied for non-image files."""
        tmpdir1, _ = temp_dirs
        filename = "script.py"
        filepath = os.path.join(tmpdir1, filename)
        Path(filepath).write_text("print('hello')", encoding="utf-8")

        response = client.get(f"/api/photos/{filename}")
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data

    def test_get_photo_from_classification_directory(self, client, temp_dirs):
        """Test retrieving photo from classification directory."""
        _, tmpdir2 = temp_dirs
        test_data = "classified image"
        filename = "classified.jpg"
        filepath = os.path.join(tmpdir2, filename)
        Path(filepath).write_text(test_data, encoding="utf-8")

        response = client.get(f"/api/photos/{filename}")
        assert response.status_code == 200
        assert response.data.decode("utf-8") == test_data

    def test_get_photo_with_debug_paths(self, client):
        """Test debug path information when enabled."""
        os.environ["PG_DEBUG_PATHS"] = "1"

        try:
            response = client.get("/api/photos/nonexistent.jpg")
            assert response.status_code in [403, 404]
            data = response.get_json()

            # Debug fields should be present
            if response.status_code == 403:
                assert "_tried_bases" in data or "_ext" in data
            elif response.status_code == 404:
                assert "_resolved" in data
        finally:
            if "PG_DEBUG_PATHS" in os.environ:
                del os.environ["PG_DEBUG_PATHS"]

    def test_get_photo_path_traversal_protection(self, client):
        """Test protection against path traversal attacks."""
        response = client.get("/api/photos/../../../etc/passwd")
        assert response.status_code == 403

    def test_get_photo_various_image_extensions(self, client, temp_dirs):
        """Test retrieving photos with various extensions."""
        tmpdir1, _ = temp_dirs
        image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]

        for ext in image_exts:
            filename = f"image{ext}"
            filepath = os.path.join(tmpdir1, filename)
            Path(filepath).write_text(f"image{ext}", encoding="utf-8")

            response = client.get(f"/api/photos/{filename}")
            assert response.status_code == 200


class TestDeletePhoto:
    """Test the delete_photo endpoint."""

    def test_delete_photo_success(self, client, temp_dirs):
        """Test successfully deleting a photo."""
        tmpdir1, _ = temp_dirs
        filename = "test.jpg"
        filepath = os.path.join(tmpdir1, filename)
        Path(filepath).write_text("test image", encoding="utf-8")

        # Verify file exists
        assert os.path.exists(filepath)

        response = client.delete(f"/api/photos/{filename}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "message" in data

        # Verify file was deleted
        assert not os.path.exists(filepath)

    def test_delete_photo_not_found(self, client):
        """Test 403 for nonexistent photo (no leak of file existence)."""
        response = client.delete("/api/photos/nonexistent.jpg")
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Access denied"

    def test_delete_photo_access_denied_outside_directories(self, client):
        """Test access denied for path outside allowed directories."""
        response = client.delete("/api/photos/../../etc/passwd")
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "Access denied"

    def test_delete_photo_access_denied_non_image(self, client, temp_dirs):
        """Test access denied for non-image files."""
        tmpdir1, _ = temp_dirs
        filename = "script.py"
        filepath = os.path.join(tmpdir1, filename)
        Path(filepath).write_text("print('hello')", encoding="utf-8")

        response = client.delete(f"/api/photos/{filename}")
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data

        # Verify file still exists (not deleted)
        assert os.path.exists(filepath)

    def test_delete_photo_from_classification_directory(
        self, client, temp_dirs
    ):
        """Test deleting photo from classification directory."""
        _, tmpdir2 = temp_dirs
        filename = "classified.jpg"
        filepath = os.path.join(tmpdir2, filename)
        Path(filepath).write_text("classified image", encoding="utf-8")

        # Verify file exists
        assert os.path.exists(filepath)

        response = client.delete(f"/api/photos/{filename}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify file was deleted
        assert not os.path.exists(filepath)

    def test_delete_photo_path_traversal_protection(self, client):
        """Test protection against path traversal attacks."""
        response = client.delete("/api/photos/../../../etc/passwd")
        assert response.status_code == 403

    def test_delete_photo_various_image_extensions(self, client, temp_dirs):
        """Test deleting photos with various extensions."""
        tmpdir1, _ = temp_dirs
        image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]

        for ext in image_exts:
            filename = f"image{ext}"
            filepath = os.path.join(tmpdir1, filename)
            Path(filepath).write_text(f"image{ext}", encoding="utf-8")

            response = client.delete(f"/api/photos/{filename}")
            assert response.status_code == 200
            assert not os.path.exists(filepath)

    def test_delete_photo_idempotent(self, client, temp_dirs):
        """Test that deleting same photo twice returns 403 second time."""
        tmpdir1, _ = temp_dirs
        filename = "test.jpg"
        filepath = os.path.join(tmpdir1, filename)
        Path(filepath).write_text("test image", encoding="utf-8")

        # First deletion should succeed
        response = client.delete(f"/api/photos/{filename}")
        assert response.status_code == 200

        # Second deletion returns 403 (file no longer in allowed dir)
        response = client.delete(f"/api/photos/{filename}")
        assert response.status_code == 403

    def test_delete_photo_with_subdirectory_path(self, client, temp_dirs):
        """Test deleting photo specified with subdirectory path."""
        tmpdir1, _ = temp_dirs

        # Create subdirectory with image
        subdir = os.path.join(tmpdir1, "subdir")
        os.makedirs(subdir)
        filename = "image.jpg"
        filepath = os.path.join(subdir, filename)
        Path(filepath).write_text("image in subdir", encoding="utf-8")

        # Try to delete with subdirectory path
        response = client.delete(f"/api/photos/subdir/{filename}")
        # Should either succeed or deny access depending on implementation
        assert response.status_code in [200, 403, 404]
