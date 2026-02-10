"""Tests for system time synchronization routes."""

# pylint: disable=redefined-outer-name
# pylint: disable=import-outside-toplevel
# Pytest fixtures intentionally redefine names

import json
from datetime import (
    datetime,
    timezone,
)
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest
from flask import (
    Flask,
)

from pumaguard.presets import (
    Settings,
)
from pumaguard.web_routes.system import (
    register_system_routes,
)
from pumaguard.web_ui import (
    WebUI,
)


@pytest.fixture
def mock_preset():
    """Create a mock Preset instance."""
    preset = MagicMock(spec=Settings)
    return preset


@pytest.fixture
def test_app(mock_preset):
    """Create a test Flask app with system routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    # Create a mock WebUI instance
    webui = MagicMock(spec=WebUI)
    webui.presets = mock_preset

    # Register system routes
    register_system_routes(app, webui)

    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client for the Flask app."""
    return test_app.test_client()


def test_get_system_time(test_client):
    """Test getting the current system time."""
    response = test_client.get("/api/system/time")

    assert response.status_code == 200

    data = json.loads(response.data)
    assert "timestamp" in data
    assert "iso" in data
    assert "local_iso" in data
    assert "timezone" in data
    assert data["timezone"] == "UTC"

    # Verify timestamp is reasonable (within last minute)
    now = datetime.now(timezone.utc).timestamp()
    assert abs(data["timestamp"] - now) < 60

    # Verify ISO format is valid
    parsed = datetime.fromisoformat(data["iso"].replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


@patch("pumaguard.web_routes.system._set_system_time")
def test_set_system_time_with_timestamp(mock_set_time, test_client):
    """Test setting system time using Unix timestamp."""
    mock_set_time.return_value = (True, "Time set successfully")

    test_timestamp = 1700000000.0
    response = test_client.put(
        "/api/system/time",
        data=json.dumps({"timestamp": test_timestamp}),
        content_type="application/json",
    )

    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["success"] is True
    assert "message" in data
    assert "new_time" in data

    # Verify the function was called
    mock_set_time.assert_called_once()
    call_args = mock_set_time.call_args[0]
    target_time = call_args[0]
    assert abs(target_time.timestamp() - test_timestamp) < 1


@patch("pumaguard.web_routes.system._set_system_time")
def test_set_system_time_with_iso(mock_set_time, test_client):
    """Test setting system time using ISO 8601 string."""
    mock_set_time.return_value = (True, "Time set successfully")

    test_iso = "2024-01-15T10:30:00Z"
    response = test_client.put(
        "/api/system/time",
        data=json.dumps({"iso": test_iso}),
        content_type="application/json",
    )

    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["success"] is True

    # Verify the function was called
    mock_set_time.assert_called_once()


@patch("pumaguard.web_routes.system._set_system_time")
def test_set_system_time_failure(mock_set_time, test_client):
    """Test handling of system time set failure."""
    mock_set_time.return_value = (False, "Permission denied")

    test_timestamp = 1700000000.0
    response = test_client.put(
        "/api/system/time",
        data=json.dumps({"timestamp": test_timestamp}),
        content_type="application/json",
    )

    assert response.status_code == 500

    data = json.loads(response.data)
    assert "error" in data
    assert "Permission denied" in data["error"]


def test_set_system_time_no_data(test_client):
    """Test setting system time without data."""
    response = test_client.put(
        "/api/system/time",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 400

    data = json.loads(response.data)
    assert "error" in data


def test_set_system_time_invalid_timestamp(test_client):
    """Test setting system time with invalid timestamp."""
    response = test_client.put(
        "/api/system/time",
        data=json.dumps({"timestamp": "invalid"}),
        content_type="application/json",
    )

    assert response.status_code == 400

    data = json.loads(response.data)
    assert "error" in data
    assert "Invalid timestamp format" in data["error"]


def test_set_system_time_invalid_iso(test_client):
    """Test setting system time with invalid ISO string."""
    response = test_client.put(
        "/api/system/time",
        data=json.dumps({"iso": "not-a-valid-date"}),
        content_type="application/json",
    )

    assert response.status_code == 400

    data = json.loads(response.data)
    assert "error" in data
    assert "Invalid ISO datetime format" in data["error"]


@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists")
@patch("pumaguard.web_routes.system.platform.system")
def test_set_system_time_linux_timedatectl_success(
    mock_platform, mock_cmd_exists, mock_run
):
    """Test Linux time setting with timedatectl success."""
    from pumaguard.web_routes.system import (
        _set_system_time,
    )

    mock_platform.return_value = "Linux"
    mock_cmd_exists.return_value = True

    # Mock successful timedatectl call
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    target_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    success, message = _set_system_time(target_time, "linux")

    assert success is True
    assert "timedatectl" in message


@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists")
@patch("pumaguard.web_routes.system.platform.system")
def test_set_system_time_linux_permission_denied(
    mock_platform, mock_cmd_exists, mock_run
):
    """Test Linux time setting with permission denied."""
    from pumaguard.web_routes.system import (
        _set_system_time,
    )

    mock_platform.return_value = "Linux"
    mock_cmd_exists.return_value = True

    # Mock permission denied
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Permission denied"
    mock_run.return_value = mock_result

    target_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    success, message = _set_system_time(target_time, "linux")

    assert success is False
    assert "Permission denied" in message


@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists")
def test_set_system_time_darwin_success(mock_cmd_exists, mock_run):
    """Test macOS time setting success."""
    from pumaguard.web_routes.system import (
        _set_system_time,
    )

    mock_cmd_exists.return_value = True

    # Mock successful date call
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    target_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    success, message = _set_system_time(target_time, "darwin")

    assert success is True
    assert "macOS" in message


def test_set_system_time_unsupported_platform():
    """Test time setting on unsupported platform."""
    from pumaguard.web_routes.system import (
        _set_system_time,
    )

    target_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    success, message = _set_system_time(target_time, "unknown_os")

    assert success is False
    assert "Unsupported platform" in message


@patch("pumaguard.web_routes.system.subprocess.run")
def test_command_exists_true(mock_run):
    """Test _command_exists returns True when command exists."""
    from pumaguard.web_routes.system import (
        _command_exists,
    )

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    assert _command_exists("date") is True


@patch("pumaguard.web_routes.system.subprocess.run")
def test_command_exists_false(mock_run):
    """Test _command_exists returns False when command doesn't exist."""
    from pumaguard.web_routes.system import (
        _command_exists,
    )

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_run.return_value = mock_result

    assert _command_exists("nonexistent") is False


@patch("pumaguard.web_routes.system.subprocess.run")
def test_command_exists_timeout(mock_run):
    """Test _command_exists handles timeout."""
    from pumaguard.web_routes.system import (
        _command_exists,
    )

    mock_run.side_effect = FileNotFoundError()

    assert _command_exists("some_command") is False
