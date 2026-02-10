"""Tests for artifacts web routes."""

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

from pumaguard.web_routes.artifacts import (
    register_artifacts_routes,
)


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def temp_intermediate_dir():
    """Create a temporary directory for intermediate files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def webui_mock(temp_intermediate_dir):
    """Create a mock WebUI instance."""
    webui = MagicMock()
    webui.presets = MagicMock()
    webui.presets.intermediate_dir = temp_intermediate_dir
    return webui


@pytest.fixture
def client(app, webui_mock):
    """Create a test client with artifacts routes registered."""
    register_artifacts_routes(app, webui_mock)
    return app.test_client()


class TestListArtifacts:
    """Test the list_artifacts endpoint."""

    def test_list_artifacts_empty_directory(
        self, client, temp_intermediate_dir
    ):
        """Test listing artifacts when directory is empty."""
        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["artifacts"] == []
        assert data["total"] == 0
        assert data["directory"] == os.path.realpath(temp_intermediate_dir)

    def test_list_artifacts_nonexistent_directory(self, app, webui_mock):
        """Test listing artifacts when directory doesn't exist."""
        webui_mock.presets.intermediate_dir = "/nonexistent/directory"
        register_artifacts_routes(app, webui_mock)
        client = app.test_client()

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["artifacts"] == []
        assert data["total"] == 0

    def test_list_artifacts_with_image_files(
        self, client, temp_intermediate_dir
    ):
        """Test listing artifacts with image files."""
        # Create test image files
        img_files = ["test1.jpg", "test2.png", "test3.jpeg"]
        for filename in img_files:
            filepath = os.path.join(temp_intermediate_dir, filename)
            Path(filepath).write_text("fake image data", encoding="utf-8")

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 3
        assert len(data["artifacts"]) == 3

        filenames = [artifact["filename"] for artifact in data["artifacts"]]
        for filename in img_files:
            assert filename in filenames

        # Check that all are marked as images
        for artifact in data["artifacts"]:
            assert artifact["kind"] == "image"

    def test_list_artifacts_with_csv_files(
        self, client, temp_intermediate_dir
    ):
        """Test listing artifacts with CSV files."""
        csv_files = ["data1.csv", "results.csv"]
        for filename in csv_files:
            filepath = os.path.join(temp_intermediate_dir, filename)
            Path(filepath).write_text(
                "header1,header2\nval1,val2", encoding="utf-8"
            )

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 2

        for artifact in data["artifacts"]:
            assert artifact["kind"] == "csv"
            assert artifact["ext"] == ".csv"

    def test_list_artifacts_with_mixed_files(
        self, client, temp_intermediate_dir
    ):
        """Test listing artifacts with mixed file types."""
        files = {
            "image.jpg": "image",
            "image.png": "image",
            "data.csv": "csv",
            "notes.txt": "file",
            "script.py": "file",
        }

        for filename in files:
            filepath = os.path.join(temp_intermediate_dir, filename)
            Path(filepath).write_text("test data", encoding="utf-8")

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 5

        for artifact in data["artifacts"]:
            expected_kind = files[artifact["filename"]]
            assert artifact["kind"] == expected_kind

    def test_list_artifacts_filter_by_extension(
        self, client, temp_intermediate_dir
    ):
        """Test filtering artifacts by extension."""
        files = ["test.jpg", "test.png", "data.csv", "notes.txt"]
        for filename in files:
            filepath = os.path.join(temp_intermediate_dir, filename)
            Path(filepath).write_text("test data", encoding="utf-8")

        # Filter for jpg files
        response = client.get("/api/artifacts?ext=jpg")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["artifacts"][0]["filename"] == "test.jpg"

        # Filter for csv files
        response = client.get("/api/artifacts?ext=.csv")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["artifacts"][0]["filename"] == "data.csv"

    def test_list_artifacts_filter_multiple_extensions(
        self, client, temp_intermediate_dir
    ):
        """Test filtering artifacts by multiple extensions."""
        files = ["test1.jpg", "test2.png", "test3.gif", "data.csv"]
        for filename in files:
            filepath = os.path.join(temp_intermediate_dir, filename)
            Path(filepath).write_text("test data", encoding="utf-8")

        # Filter for jpg and png
        response = client.get("/api/artifacts?ext=jpg,png")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 2
        filenames = [artifact["filename"] for artifact in data["artifacts"]]
        assert "test1.jpg" in filenames
        assert "test2.png" in filenames

    def test_list_artifacts_with_limit(self, client, temp_intermediate_dir):
        """Test limiting the number of artifacts returned."""
        # Create 10 files
        for i in range(10):
            filepath = os.path.join(temp_intermediate_dir, f"file{i}.jpg")
            Path(filepath).write_text(f"data {i}", encoding="utf-8")

        # Request only 5
        response = client.get("/api/artifacts?limit=5")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 5
        assert len(data["artifacts"]) == 5

    def test_list_artifacts_sorted_by_modified_time(
        self, client, temp_intermediate_dir
    ):
        """Test artifacts sorted by modification time (newest first)."""
        # Create files with different modification times
        for i in range(3):
            filepath = os.path.join(temp_intermediate_dir, f"file{i}.jpg")
            Path(filepath).write_text(f"data {i}", encoding="utf-8")
            # Give a small delay to ensure different timestamps
            time.sleep(0.01)

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 3

        # Artifacts should be sorted by modified time (newest first)
        modified_times = [
            artifact["modified"] for artifact in data["artifacts"]
        ]
        assert modified_times == sorted(modified_times, reverse=True)

    def test_list_artifacts_includes_file_metadata(
        self, client, temp_intermediate_dir
    ):
        """Test that artifacts include proper metadata."""
        filepath = os.path.join(temp_intermediate_dir, "test.jpg")
        test_data = "test image data"
        Path(filepath).write_text(test_data, encoding="utf-8")

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1

        artifact = data["artifacts"][0]
        assert artifact["filename"] == "test.jpg"
        assert artifact["path"] == filepath
        assert artifact["ext"] == ".jpg"
        assert artifact["kind"] == "image"
        assert artifact["size"] == len(test_data)
        assert "modified" in artifact
        assert "created" in artifact

    def test_list_artifacts_ignores_subdirectories(
        self, client, temp_intermediate_dir
    ):
        """Test that subdirectories are not listed as artifacts."""
        # Create a file
        filepath = os.path.join(temp_intermediate_dir, "test.jpg")
        Path(filepath).write_text("test data", encoding="utf-8")

        # Create a subdirectory
        subdir = os.path.join(temp_intermediate_dir, "subdir")
        os.makedirs(subdir)

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        # Should only include the file, not the subdirectory
        assert data["total"] == 1
        assert data["artifacts"][0]["filename"] == "test.jpg"

    def test_list_artifacts_various_image_extensions(
        self, client, temp_intermediate_dir
    ):
        """Test that all supported image extensions are recognized."""
        image_exts = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
        for ext in image_exts:
            filepath = os.path.join(temp_intermediate_dir, f"test{ext}")
            Path(filepath).write_text("fake image", encoding="utf-8")

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == len(image_exts)

        for artifact in data["artifacts"]:
            assert artifact["kind"] == "image"

    def test_list_artifacts_case_insensitive_extensions(
        self, client, temp_intermediate_dir
    ):
        """Test that extension matching is case-insensitive."""
        files = ["test.JPG", "test.Png", "test.CSV"]
        for filename in files:
            filepath = os.path.join(temp_intermediate_dir, filename)
            Path(filepath).write_text("test data", encoding="utf-8")

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()

        kinds = {
            artifact["filename"]: artifact["kind"]
            for artifact in data["artifacts"]
        }
        assert kinds["test.JPG"] == "image"
        assert kinds["test.Png"] == "image"
        assert kinds["test.CSV"] == "csv"

    def test_list_artifacts_limit_greater_than_total(
        self, client, temp_intermediate_dir
    ):
        """Test that limit greater than total returns all artifacts."""
        # Create 3 files
        for i in range(3):
            filepath = os.path.join(temp_intermediate_dir, f"file{i}.jpg")
            Path(filepath).write_text(f"data {i}", encoding="utf-8")

        # Request 10 but only 3 exist
        response = client.get("/api/artifacts?limit=10")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 3
        assert len(data["artifacts"]) == 3

    def test_list_artifacts_filter_empty_extension_string(
        self, client, temp_intermediate_dir
    ):
        """Test filtering with empty extension string."""
        files = ["test.jpg", "test.png"]
        for filename in files:
            filepath = os.path.join(temp_intermediate_dir, filename)
            Path(filepath).write_text("test data", encoding="utf-8")

        # Filter with empty extension (should return all)
        response = client.get("/api/artifacts?ext=")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 2

    def test_list_artifacts_with_dot_files(
        self, client, temp_intermediate_dir
    ):
        """Test that hidden dot files are handled."""
        # Create a hidden file
        filepath = os.path.join(temp_intermediate_dir, ".hidden.jpg")
        Path(filepath).write_text("hidden data", encoding="utf-8")

        response = client.get("/api/artifacts")
        assert response.status_code == 200
        data = response.get_json()
        # Should still list the file
        assert data["total"] == 1
        assert data["artifacts"][0]["filename"] == ".hidden.jpg"
