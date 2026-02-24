"""Tests for directory management routes."""

# pylint: disable=redefined-outer-name,unused-variable
# Pytest fixtures intentionally redefine names
# webui variable is part of fixture unpacking pattern

import json
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

from pumaguard.web_routes.directories import (
    register_directories_routes,
)
from pumaguard.web_ui import (
    WebUI,
)


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    dir1 = tmp_path / "images1"
    dir2 = tmp_path / "images2"
    dir3 = tmp_path / "output1"
    dir1.mkdir()
    dir2.mkdir()
    dir3.mkdir()
    return {
        "image1": str(dir1),
        "image2": str(dir2),
        "output1": str(dir3),
    }


@pytest.fixture
def test_app(temp_dirs):
    """Create a test Flask app with directory routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    # Create a mock WebUI instance
    webui = MagicMock(spec=WebUI)
    webui.image_directories = [temp_dirs["image1"]]
    webui.classification_directories = [temp_dirs["output1"]]
    webui.folder_manager = MagicMock()
    webui.watch_method = "os"

    register_directories_routes(app, webui)

    return app, webui


def test_get_directories(test_app, temp_dirs):
    """Test GET /api/directories returns watched directories."""
    app, webui = test_app
    client = app.test_client()

    response = client.get("/api/directories")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "directories" in data
    assert temp_dirs["image1"] in data["directories"]


def test_get_directories_empty(temp_dirs):  # pylint: disable=unused-argument
    """Test GET /api/directories with no directories."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    webui = MagicMock(spec=WebUI)
    webui.image_directories = []
    webui.classification_directories = []

    register_directories_routes(app, webui)
    client = app.test_client()

    response = client.get("/api/directories")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["directories"] == []


def test_get_classification_directories(test_app, temp_dirs):
    """Test GET /api/directories/classification returns output directories."""
    app, webui = test_app
    client = app.test_client()

    response = client.get("/api/directories/classification")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "directories" in data
    assert temp_dirs["output1"] in data["directories"]


def test_get_classification_directories_empty(temp_dirs):  # pylint: disable=unused-argument
    """Test GET /api/directories/classification with no directories."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    webui = MagicMock(spec=WebUI)
    webui.image_directories = []
    webui.classification_directories = []

    register_directories_routes(app, webui)
    client = app.test_client()

    response = client.get("/api/directories/classification")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["directories"] == []


def test_add_directory_success(test_app, temp_dirs):
    """Test POST /api/directories adds a new directory."""
    app, webui = test_app
    client = app.test_client()

    payload = {"directory": temp_dirs["image2"]}

    response = client.post(
        "/api/directories",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert temp_dirs["image2"] in data["directories"]

    # Verify directory was added
    assert temp_dirs["image2"] in webui.image_directories

    # Verify folder manager was called
    webui.folder_manager.register_folder.assert_called_once_with(
        temp_dirs["image2"], "os"
    )


def test_add_directory_already_exists(test_app, temp_dirs):
    """Test POST /api/directories with already existing directory."""
    app, webui = test_app
    client = app.test_client()

    # Directory already in image_directories
    payload = {"directory": temp_dirs["image1"]}

    response = client.post(
        "/api/directories",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True

    # Should not call register_folder if already exists
    webui.folder_manager.register_folder.assert_not_called()


def test_add_directory_no_directory_provided(test_app):
    """Test POST /api/directories with missing directory field."""
    app, webui = test_app
    client = app.test_client()

    payload = {}

    response = client.post(
        "/api/directories",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No directory provided"


def test_add_directory_null_directory(test_app):
    """Test POST /api/directories with null directory value."""
    app, webui = test_app
    client = app.test_client()

    payload = {"directory": None}

    response = client.post(
        "/api/directories",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No directory provided"


def test_add_directory_empty_string(test_app):
    """Test POST /api/directories with empty string directory."""
    app, webui = test_app
    client = app.test_client()

    payload = {"directory": ""}

    response = client.post(
        "/api/directories",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No directory provided"


def test_add_directory_no_json_body(test_app):
    """Test POST /api/directories with no JSON body."""
    app, webui = test_app
    client = app.test_client()

    response = client.post("/api/directories")

    # Flask returns 415 when no content-type is set
    assert response.status_code == 415


def test_add_directory_no_folder_manager(test_app, temp_dirs):
    """Test POST /api/directories when folder_manager is None."""
    app, webui = test_app
    webui.folder_manager = None
    client = app.test_client()

    payload = {"directory": temp_dirs["image2"]}

    response = client.post(
        "/api/directories",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert temp_dirs["image2"] in data["directories"]


def test_remove_directory_success(test_app, temp_dirs):
    """Test DELETE /api/directories/<index> removes directory."""
    app, webui = test_app
    client = app.test_client()

    # Ensure we have a directory to remove
    assert len(webui.image_directories) > 0

    response = client.delete("/api/directories/0")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    # Verify it was removed from the list
    assert temp_dirs["image1"] not in webui.image_directories


def test_remove_directory_invalid_index_negative(test_app):
    """Test DELETE /api/directories/<index> with negative index."""
    app, webui = test_app
    client = app.test_client()

    # Note: Flask routing doesn't match negative integers to <int:index>
    # so this returns 404 Not Found instead of reaching the handler
    response = client.delete("/api/directories/-1")

    assert response.status_code == 404


def test_remove_directory_invalid_index_too_large(test_app):
    """Test DELETE /api/directories/<index> with index out of range."""
    app, webui = test_app
    client = app.test_client()

    # Index larger than list size
    response = client.delete("/api/directories/999")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Invalid index"


def test_remove_directory_from_empty_list():
    """Test DELETE /api/directories/<index> when list is empty."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    webui = MagicMock(spec=WebUI)
    webui.image_directories = []

    register_directories_routes(app, webui)
    client = app.test_client()

    response = client.delete("/api/directories/0")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Invalid index"


def test_add_multiple_directories(test_app, temp_dirs):
    """Test adding multiple directories sequentially."""
    app, webui = test_app
    client = app.test_client()

    # Add first directory
    payload1 = {"directory": temp_dirs["image2"]}
    response1 = client.post(
        "/api/directories",
        data=json.dumps(payload1),
        content_type="application/json",
    )
    assert response1.status_code == 200

    # Create another temp directory
    new_dir = str(Path(temp_dirs["image1"]).parent / "images3")
    Path(new_dir).mkdir(exist_ok=True)

    # Add second directory
    payload2 = {"directory": new_dir}
    response2 = client.post(
        "/api/directories",
        data=json.dumps(payload2),
        content_type="application/json",
    )
    assert response2.status_code == 200
    data = json.loads(response2.data)

    # Should have original + 2 new directories
    assert len(data["directories"]) == 3


def test_remove_middle_directory(test_app, temp_dirs):
    """Test removing a directory from the middle of the list."""
    app, webui = test_app
    client = app.test_client()

    # Add two more directories
    dir2 = temp_dirs["image2"]
    new_dir = str(Path(temp_dirs["image1"]).parent / "images3")
    Path(new_dir).mkdir(exist_ok=True)

    webui.image_directories.append(dir2)
    webui.image_directories.append(new_dir)

    # Remove middle directory (index 1)
    initial_length = len(webui.image_directories)
    response = client.delete("/api/directories/1")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert len(data["directories"]) == initial_length - 1
    assert dir2 not in data["directories"]
