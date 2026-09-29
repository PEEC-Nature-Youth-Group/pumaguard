"""
Tests for system administration routes (time sync
and service management).
"""

# pylint: disable=redefined-outer-name
# pylint: disable=import-outside-toplevel
# Pytest fixtures intentionally redefine names

import json
import os
import subprocess
import uuid
import zipfile
from datetime import (
    datetime,
    timezone,
)
from io import (
    BytesIO,
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
    _MANAGED_SERVICES,
    _get_service_status,
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


# ---------------------------------------------------------------------------
# _get_service_status unit tests
# ---------------------------------------------------------------------------


@patch("pumaguard.web_routes.system._command_exists", return_value=False)
def test_get_service_status_no_systemctl(mock_cmd):
    """Returns unavailable status when systemctl is not on PATH."""
    result = _get_service_status("hostapd")

    assert mock_cmd.called
    assert result["name"] == "hostapd"
    assert result["active"] is False
    assert result["enabled"] is False
    assert result["state"] == "unavailable"
    assert result["available"] is False


@patch("pumaguard.web_routes.system._command_exists", return_value=True)
@patch("pumaguard.web_routes.system.subprocess.run")
def test_get_service_status_active_enabled(mock_run, _mock_cmd):
    """
    Reports active=True and enabled=True when both systemctl calls succeed.
    """
    active_result = MagicMock()
    active_result.returncode = 0
    active_result.stdout = "active\n"

    enabled_result = MagicMock()
    enabled_result.returncode = 0
    enabled_result.stdout = "enabled\n"

    mock_run.side_effect = [active_result, enabled_result]

    result = _get_service_status("hostapd")

    assert result["name"] == "hostapd"
    assert result["active"] is True
    assert result["enabled"] is True
    assert result["state"] == "active"
    assert result["available"] is True


@patch("pumaguard.web_routes.system._command_exists", return_value=True)
@patch("pumaguard.web_routes.system.subprocess.run")
def test_get_service_status_inactive_disabled(mock_run, _mock_cmd):
    """
    Reports active=False and enabled=False for a stopped, disabled service.
    """
    active_result = MagicMock()
    active_result.returncode = 3  # systemctl exit code for inactive
    active_result.stdout = "inactive\n"

    enabled_result = MagicMock()
    enabled_result.returncode = 1  # systemctl exit code for disabled
    enabled_result.stdout = "disabled\n"

    mock_run.side_effect = [active_result, enabled_result]

    result = _get_service_status("dnsmasq")

    assert result["name"] == "dnsmasq"
    assert result["active"] is False
    assert result["enabled"] is False
    assert result["state"] == "inactive"
    assert result["available"] is True


@patch("pumaguard.web_routes.system._command_exists", return_value=True)
@patch("pumaguard.web_routes.system.subprocess.run")
def test_get_service_status_failed(mock_run, _mock_cmd):
    """Reports state='failed' when the service has crashed."""
    active_result = MagicMock()
    active_result.returncode = 3
    active_result.stdout = "failed\n"

    enabled_result = MagicMock()
    enabled_result.returncode = 0
    enabled_result.stdout = "enabled\n"

    mock_run.side_effect = [active_result, enabled_result]

    result = _get_service_status("hostapd")

    assert result["active"] is False
    assert result["state"] == "failed"


@patch("pumaguard.web_routes.system._command_exists", return_value=True)
@patch(
    "pumaguard.web_routes.system.subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="systemctl", timeout=5),
)
def test_get_service_status_timeout(_mock_run, _mock_cmd):
    """Returns state='timeout' when systemctl hangs."""
    result = _get_service_status("hostapd")

    assert result["active"] is False
    assert result["state"] == "timeout"
    assert result["available"] is True


# ---------------------------------------------------------------------------
# GET /api/system/services
# ---------------------------------------------------------------------------


@patch("pumaguard.web_routes.system._get_service_status")
def test_get_services_returns_both_services(mock_status, test_client):
    """GET /api/system/services returns a list with hostapd and dnsmasq."""
    mock_status.side_effect = lambda svc: {
        "name": svc,
        "active": True,
        "enabled": True,
        "state": "active",
        "available": True,
    }

    response = test_client.get("/api/system/services")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "services" in data
    names = {s["name"] for s in data["services"]}
    assert names == _MANAGED_SERVICES


@patch("pumaguard.web_routes.system._get_service_status")
def test_get_services_structure(mock_status, test_client):
    """Each service entry contains the expected keys."""
    mock_status.return_value = {
        "name": "hostapd",
        "active": True,
        "enabled": True,
        "state": "active",
        "available": True,
    }

    response = test_client.get("/api/system/services")

    assert response.status_code == 200
    data = json.loads(response.data)
    for service in data["services"]:
        assert "name" in service
        assert "active" in service
        assert "enabled" in service
        assert "state" in service
        assert "available" in service


@patch("pumaguard.web_routes.system._get_service_status")
def test_get_services_mixed_states(mock_status, test_client):
    """
    GET /api/system/services correctly reflects mixed active/inactive states.
    """

    def _side_effect(svc):
        if svc == "hostapd":
            return {
                "name": "hostapd",
                "active": True,
                "enabled": True,
                "state": "active",
                "available": True,
            }
        return {
            "name": "dnsmasq",
            "active": False,
            "enabled": True,
            "state": "failed",
            "available": True,
        }

    mock_status.side_effect = _side_effect

    response = test_client.get("/api/system/services")

    assert response.status_code == 200
    data = json.loads(response.data)
    by_name = {s["name"]: s for s in data["services"]}
    assert by_name["hostapd"]["active"] is True
    assert by_name["dnsmasq"]["active"] is False
    assert by_name["dnsmasq"]["state"] == "failed"


# ---------------------------------------------------------------------------
# POST /api/system/services/<name>/restart
# ---------------------------------------------------------------------------


@patch("pumaguard.web_routes.system._get_service_status")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
@patch("pumaguard.web_routes.system.subprocess.run")
def test_restart_service_success(
    mock_run, _mock_cmd, mock_status, test_client
):
    """POST restart returns 200 and the refreshed service status on success."""
    restart_result = MagicMock()
    restart_result.returncode = 0
    restart_result.stderr = ""
    mock_run.return_value = restart_result

    mock_status.return_value = {
        "name": "hostapd",
        "active": True,
        "enabled": True,
        "state": "active",
        "available": True,
    }

    response = test_client.post("/api/system/services/hostapd/restart")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "hostapd" in data["message"]
    assert data["service"]["name"] == "hostapd"
    assert data["service"]["active"] is True

    # Verify sudo systemctl restart was called with the right service name
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd == ["sudo", "/usr/bin/systemctl", "restart", "hostapd.service"]


@patch("pumaguard.web_routes.system._get_service_status")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
@patch("pumaguard.web_routes.system.subprocess.run")
def test_restart_dnsmasq_success(
    mock_run, _mock_cmd, mock_status, test_client
):
    """POST restart works for dnsmasq as well as hostapd."""
    restart_result = MagicMock()
    restart_result.returncode = 0
    restart_result.stderr = ""
    mock_run.return_value = restart_result

    mock_status.return_value = {
        "name": "dnsmasq",
        "active": True,
        "enabled": True,
        "state": "active",
        "available": True,
    }

    response = test_client.post("/api/system/services/dnsmasq/restart")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    cmd = mock_run.call_args[0][0]
    assert cmd == ["sudo", "/usr/bin/systemctl", "restart", "dnsmasq.service"]


def test_restart_service_unknown_name(test_client):
    """POST restart returns 400 for a service name not in the allow-list."""
    response = test_client.post("/api/system/services/sshd/restart")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "sshd" in data["error"]


def test_restart_service_path_traversal(test_client):
    """POST restart rejects names that look like path traversal attempts."""
    response = test_client.post(
        "/api/system/services/../../etc/passwd/restart"
    )
    # Flask's <string:> converter stops at '/' so this hits a 404, which is
    # also an acceptable rejection – the important thing is it never reaches
    # our handler with a dangerous name.
    assert response.status_code in (400, 404)


@patch("pumaguard.web_routes.system._command_exists", return_value=False)
def test_restart_service_no_systemctl(_mock_cmd, test_client):
    """POST restart returns 503 when systemctl is not available."""
    response = test_client.post("/api/system/services/hostapd/restart")

    assert response.status_code == 503
    data = json.loads(response.data)
    assert "error" in data
    assert "systemctl" in data["error"]


@patch("pumaguard.web_routes.system._command_exists", return_value=True)
@patch("pumaguard.web_routes.system.subprocess.run")
def test_restart_service_failure(mock_run, _mock_cmd, test_client):
    """POST restart returns 500 when systemctl exits non-zero."""
    restart_result = MagicMock()
    restart_result.returncode = 1
    restart_result.stderr = "Job for hostapd.service failed."
    restart_result.stdout = ""
    mock_run.return_value = restart_result

    response = test_client.post("/api/system/services/hostapd/restart")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert "hostapd" in data["error"]


@patch("pumaguard.web_routes.system._command_exists", return_value=True)
@patch(
    "pumaguard.web_routes.system.subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="systemctl", timeout=30),
)
def test_restart_service_timeout(_mock_run, _mock_cmd, test_client):
    """POST restart returns 504 when the systemctl call times out."""
    response = test_client.post("/api/system/services/hostapd/restart")

    assert response.status_code == 504
    data = json.loads(response.data)
    assert "error" in data


# ---------------------------------------------------------------------------
# GET /api/system/logs
# ---------------------------------------------------------------------------


def test_get_system_logs_invalid_lines(test_client):
    """Non-numeric 'lines' (with 'since' disabled) is rejected."""
    response = test_client.get(
        "/api/system/logs?since=&lines=not-a-number"
    )

    assert response.status_code == 503
    data = json.loads(response.data)
    assert "invalid value for lines" in data["error"]


def test_get_system_logs_non_positive_lines(test_client):
    """A non-positive 'lines' value is rejected."""
    response = test_client.get("/api/system/logs?since=&lines=0")

    assert response.status_code == 503
    data = json.loads(response.data)
    assert "positive integer" in data["error"]


@patch("pumaguard.web_routes.system.shutil.which", return_value=None)
def test_get_system_logs_journalctl_unavailable(_mock_which, test_client):
    """Returns 503 when journalctl is not on PATH."""
    response = test_client.get("/api/system/logs")

    assert response.status_code == 503
    data = json.loads(response.data)
    assert "journalctl is not available" in data["error"]


@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system.shutil.which", return_value="/usr/bin/journalctl")
def test_get_system_logs_default_scope_uses_since_and_unit(
    _mock_which, mock_run, test_client
):
    """Default request scopes to the pumaguard unit and a time window."""
    mock_run.return_value = MagicMock(
        returncode=0, stdout="line one\nline two\n", stderr=""
    )

    response = test_client.get("/api/system/logs")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["logs"] == ["line one", "line two"]
    assert data["line_count"] == 2
    assert data["scope"] == "unit"
    assert data["since"] == "1 hour ago"

    called_cmd = mock_run.call_args[0][0]
    assert "--since" in called_cmd
    assert "--unit" in called_cmd
    assert "pumaguard" in called_cmd


@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system.shutil.which", return_value="/usr/bin/journalctl")
def test_get_system_logs_scope_all_omits_unit_filter(
    _mock_which, mock_run, test_client
):
    """scope=all does not restrict logs to the pumaguard unit."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    response = test_client.get("/api/system/logs?scope=all")

    assert response.status_code == 200
    called_cmd = mock_run.call_args[0][0]
    assert "--unit" not in called_cmd


@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system.shutil.which", return_value="/usr/bin/journalctl")
def test_get_system_logs_explicit_lines_no_since(
    _mock_which, mock_run, test_client
):
    """since='' with a numeric lines value uses --lines instead of --since."""
    mock_run.return_value = MagicMock(returncode=0, stdout="a\n", stderr="")

    response = test_client.get("/api/system/logs?since=&lines=50")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["since"] is None
    assert data["lines_requested"] == "50"

    called_cmd = mock_run.call_args[0][0]
    assert "--lines" in called_cmd
    assert "50" in called_cmd
    assert "--since" not in called_cmd


@patch(
    "pumaguard.web_routes.system.subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="journalctl", timeout=30),
)
@patch("pumaguard.web_routes.system.shutil.which", return_value="/usr/bin/journalctl")
def test_get_system_logs_timeout(_mock_which, _mock_run, test_client):
    """A journalctl timeout surfaces as 504."""
    response = test_client.get("/api/system/logs")

    assert response.status_code == 504
    data = json.loads(response.data)
    assert "timed out" in data["error"].lower()


@patch(
    "pumaguard.web_routes.system.subprocess.run",
    side_effect=OSError("boom"),
)
@patch("pumaguard.web_routes.system.shutil.which", return_value="/usr/bin/journalctl")
def test_get_system_logs_unexpected_exception(_mock_which, _mock_run, test_client):
    """An unexpected exception surfaces as 500."""
    response = test_client.get("/api/system/logs")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "Failed to retrieve logs" in data["error"]


# ---------------------------------------------------------------------------
# POST /api/system/poweroff
# ---------------------------------------------------------------------------


@patch("pumaguard.web_routes.system._command_exists", return_value=False)
def test_poweroff_systemctl_unavailable(_mock_cmd, test_client):
    """Returns 503 when systemctl is not on PATH."""
    response = test_client.post("/api/system/poweroff")

    assert response.status_code == 503
    data = json.loads(response.data)
    assert "systemctl is not available" in data["error"]


@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_poweroff_success(_mock_cmd, mock_run, test_client):
    """A successful systemctl poweroff call returns 200."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    response = test_client.post("/api/system/poweroff")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True


@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_poweroff_failure(_mock_cmd, mock_run, test_client):
    """A non-zero return code surfaces the stderr detail as a 500."""
    mock_run.return_value = MagicMock(
        returncode=1, stdout="", stderr="not authorized"
    )

    response = test_client.post("/api/system/poweroff")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "not authorized" in data["error"]


@patch(
    "pumaguard.web_routes.system.subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="systemctl", timeout=30),
)
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_poweroff_timeout(_mock_cmd, _mock_run, test_client):
    """A timed-out systemctl call surfaces as 504."""
    response = test_client.post("/api/system/poweroff")

    assert response.status_code == 504
    data = json.loads(response.data)
    assert "Timed out" in data["error"]


@patch(
    "pumaguard.web_routes.system.subprocess.run",
    side_effect=OSError("boom"),
)
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_poweroff_unexpected_exception(_mock_cmd, _mock_run, test_client):
    """An unexpected exception surfaces as 500."""
    response = test_client.post("/api/system/poweroff")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "Failed to initiate poweroff" in data["error"]


# ---------------------------------------------------------------------------
# POST /api/system/sos-report
# ---------------------------------------------------------------------------


@patch("pumaguard.web_routes.system._command_exists", return_value=False)
def test_generate_sos_report_command_unavailable(_mock_cmd, test_client):
    """Returns 503 when the sos command is not on PATH."""
    response = test_client.post("/api/system/sos-report")

    assert response.status_code == 503
    data = json.loads(response.data)
    assert "sos is not available" in data["error"]


@patch(
    "pumaguard.web_routes.system.subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="sos", timeout=300),
)
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_generate_sos_report_timeout(_mock_cmd, _mock_run, test_client):
    """A timed-out sos invocation surfaces as 504."""
    response = test_client.post("/api/system/sos-report")

    assert response.status_code == 504
    data = json.loads(response.data)
    assert "timed out" in data["error"].lower()


@patch(
    "pumaguard.web_routes.system.subprocess.run",
    side_effect=OSError("boom"),
)
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_generate_sos_report_unexpected_exception(
    _mock_cmd, _mock_run, test_client
):
    """An unexpected exception surfaces as 500."""
    response = test_client.post("/api/system/sos-report")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "Failed to generate SOS report" in data["error"]


@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_generate_sos_report_nonzero_exit(_mock_cmd, mock_run, test_client):
    """A non-zero sos exit code surfaces the stderr detail as a 500."""
    mock_run.return_value = MagicMock(
        returncode=1, stdout="", stderr="disk full"
    )

    response = test_client.post("/api/system/sos-report")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "disk full" in data["error"]


@patch("pumaguard.web_routes.system.glob.glob", return_value=[])
@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_generate_sos_report_tarball_not_found(
    _mock_cmd, mock_run, _mock_glob, test_client
):
    """Success from sos but no tarball on disk surfaces as a 500."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    response = test_client.post("/api/system/sos-report")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "could not be located" in data["error"]


def _fake_glob_single_match(tarball_path):
    """Return a glob.glob stand-in that only matches *tarball_path*."""

    def _fake_glob(pattern):
        if pattern == "/tmp/sosreport*.tar.xz":
            return [tarball_path]
        return []

    return _fake_glob


@patch("pumaguard.web_routes.system.os.path.getmtime", return_value=0.0)
@patch("pumaguard.web_routes.system.os.path.isfile")
@patch("pumaguard.web_routes.system.glob.glob")
@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_generate_sos_report_success_with_checksum(
    _mock_cmd, mock_run, mock_glob, mock_isfile, _mock_getmtime, test_client
):
    """A successful run reports the tarball and checksum file names."""
    tarball_path = "/tmp/sosreport-testhost-2024-01-01-abc123.tar.xz"
    mock_glob.side_effect = _fake_glob_single_match(tarball_path)
    # Checksum path (tarball_path + ".sha256") exists; nothing else does.
    mock_isfile.side_effect = lambda p: p.endswith(".sha256")
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="", stderr=""),  # sos report
        MagicMock(returncode=0, stdout="", stderr=""),  # chmod
    ]

    response = test_client.post("/api/system/sos-report")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["filename"] == "sosreport-testhost-2024-01-01-abc123.tar.xz"
    assert data["path"] == tarball_path
    assert data["checksum_filename"] == (
        "sosreport-testhost-2024-01-01-abc123.tar.xz.sha256"
    )
    assert data["checksum_path"] == tarball_path + ".sha256"


@patch("pumaguard.web_routes.system.os.path.getmtime", return_value=0.0)
@patch("pumaguard.web_routes.system.os.path.isfile", return_value=False)
@patch("pumaguard.web_routes.system.glob.glob")
@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_generate_sos_report_success_without_checksum(
    _mock_cmd, mock_run, mock_glob, _mock_isfile, _mock_getmtime, test_client
):
    """When no checksum file exists the checksum fields are null."""
    tarball_path = "/tmp/sosreport-testhost-2024-01-01-def456.tar.xz"
    mock_glob.side_effect = _fake_glob_single_match(tarball_path)
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="", stderr=""),
        MagicMock(returncode=0, stdout="", stderr=""),
    ]

    response = test_client.post("/api/system/sos-report")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["checksum_filename"] is None
    assert data["checksum_path"] is None


@patch("pumaguard.web_routes.system.os.path.getmtime", return_value=0.0)
@patch("pumaguard.web_routes.system.os.path.isfile", return_value=False)
@patch("pumaguard.web_routes.system.glob.glob")
@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_generate_sos_report_chmod_failure(
    _mock_cmd, mock_run, mock_glob, _mock_isfile, _mock_getmtime, test_client
):
    """A chmod CalledProcessError surfaces as a 500 with stderr detail."""
    tarball_path = "/tmp/sosreport-testhost-2024-01-01-ghi789.tar.xz"
    mock_glob.side_effect = _fake_glob_single_match(tarball_path)
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="", stderr=""),
        subprocess.CalledProcessError(
            1, ["sudo", "chmod"], output="", stderr="not permitted"
        ),
    ]

    response = test_client.post("/api/system/sos-report")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "could not be made readable" in data["error"]
    assert "not permitted" in data["error"]


@patch("pumaguard.web_routes.system.os.path.getmtime", return_value=0.0)
@patch("pumaguard.web_routes.system.os.path.isfile", return_value=False)
@patch("pumaguard.web_routes.system.glob.glob")
@patch("pumaguard.web_routes.system.subprocess.run")
@patch("pumaguard.web_routes.system._command_exists", return_value=True)
def test_generate_sos_report_chmod_timeout(
    _mock_cmd, mock_run, mock_glob, _mock_isfile, _mock_getmtime, test_client
):
    """A chmod timeout surfaces as a 500 with a clear message."""
    tarball_path = "/tmp/sosreport-testhost-2024-01-01-jkl012.tar.xz"
    mock_glob.side_effect = _fake_glob_single_match(tarball_path)
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="", stderr=""),
        subprocess.TimeoutExpired(cmd=["sudo", "chmod"], timeout=10),
    ]

    response = test_client.post("/api/system/sos-report")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "timed out making it readable" in data["error"]


# ---------------------------------------------------------------------------
# GET /api/system/sos-report/download
# ---------------------------------------------------------------------------


@patch("pumaguard.web_routes.system.glob.glob", return_value=[])
def test_download_sos_report_none_found(_mock_glob, test_client):
    """Returns 404 when there is no report to download."""
    response = test_client.get("/api/system/sos-report/download")

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "No SOS report found" in data["error"]


def test_download_sos_report_rejects_path_outside_tmp(test_client):
    """An explicit path outside /tmp is rejected with 400."""
    response = test_client.get(
        "/api/system/sos-report/download?path=/etc/passwd"
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "Invalid file path" in data["error"]


def test_download_sos_report_explicit_path_not_found(test_client):
    """A well-formed /tmp path that doesn't exist returns 404."""
    missing_path = f"/tmp/sosreport-missing-{uuid.uuid4().hex}.tar.xz"

    response = test_client.get(
        f"/api/system/sos-report/download?path={missing_path}"
    )

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "File not found" in data["error"]


def test_download_sos_report_success_bundles_checksum(test_client):
    """The tarball and its checksum are bundled into a downloadable zip."""
    unique = uuid.uuid4().hex
    tarball_path = f"/tmp/sosreport-unittest-{unique}.tar.xz"
    checksum_path = tarball_path + ".sha256"

    with open(tarball_path, "wb") as fh:
        fh.write(b"fake tarball contents")
    with open(checksum_path, "w", encoding="utf-8") as fh:
        fh.write("deadbeef  sosreport-unittest.tar.xz\n")

    try:
        with patch(
            "pumaguard.web_routes.system.glob.glob",
            side_effect=_fake_glob_single_match(tarball_path),
        ):
            response = test_client.get("/api/system/sos-report/download")

        assert response.status_code == 200
        assert response.mimetype == "application/zip"

        with zipfile.ZipFile(BytesIO(response.data)) as zf:
            names = zf.namelist()
            assert os.path.basename(tarball_path) in names
            assert os.path.basename(checksum_path) in names
            assert (
                zf.read(os.path.basename(tarball_path))
                == b"fake tarball contents"
            )
    finally:
        os.remove(tarball_path)
        os.remove(checksum_path)


def test_download_sos_report_success_explicit_path_no_checksum(test_client):
    """An explicit path with no companion checksum still succeeds."""
    unique = uuid.uuid4().hex
    tarball_path = f"/tmp/sosreport-unittest-{unique}.tar.xz"

    with open(tarball_path, "wb") as fh:
        fh.write(b"more fake contents")

    try:
        response = test_client.get(
            f"/api/system/sos-report/download?path={tarball_path}"
        )

        assert response.status_code == 200
        with zipfile.ZipFile(BytesIO(response.data)) as zf:
            names = zf.namelist()
            assert names == [os.path.basename(tarball_path)]
    finally:
        os.remove(tarball_path)
