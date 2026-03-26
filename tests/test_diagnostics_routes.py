"""Tests for diagnostics routes."""

# pylint: disable=redefined-outer-name,unused-variable,protected-access
# Pytest fixtures intentionally redefine names, webui often unused
# Tests access protected members like _get_local_ip for mocking

import json
import time
from pathlib import (
    Path,
)
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest
from flask import (
    Flask,
)

import pumaguard
from pumaguard.web_routes.diagnostics import (
    _parse_sensors_text,
    register_diagnostics_routes,
)
from pumaguard.web_ui import (
    WebUI,
)


@pytest.fixture
def test_app():
    """Create a test Flask app with diagnostics routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    # Create a mock WebUI instance
    webui = MagicMock(spec=WebUI)
    webui.image_directories = ["/path/to/images1", "/path/to/images2"]
    webui.host = "0.0.0.0"
    webui.port = 5000
    webui.flutter_dir = "/path/to/flutter"
    webui.build_dir = MagicMock()
    webui.build_dir.exists.return_value = True
    webui.build_dir.__str__.return_value = "/path/to/flutter/build/web"
    webui.mdns_enabled = True
    webui.mdns_name = "pumaguard"
    webui.start_time = time.time() - 3600  # 1 hour ago
    webui._get_local_ip = MagicMock(return_value="192.168.1.100")

    register_diagnostics_routes(app, webui)

    return app, webui


def test_get_status_basic(test_app):
    """Test GET /api/status returns basic status information."""
    app, webui = test_app
    client = app.test_client()

    response = client.get("/api/status")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "running"
    assert data["version"] == pumaguard.__version__
    assert data["directories_count"] == 2
    assert data["host"] == "192.168.1.100"
    assert data["port"] == 5000
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 3600  # At least 1 hour


def test_get_status_with_headers(test_app):
    """Test GET /api/status includes request headers."""
    app, webui = test_app
    client = app.test_client()

    response = client.get(
        "/api/status",
        headers={
            "Origin": "http://example.com",
            "Host": "pumaguard.local:5000",
        },
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["request_origin"] == "http://example.com"
    assert data["request_host"] == "pumaguard.local:5000"


def test_get_status_no_origin_header(test_app):
    """Test GET /api/status when Origin header is missing."""
    app, webui = test_app
    client = app.test_client()

    response = client.get("/api/status")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["request_origin"] == "No Origin header"


def test_get_status_no_host_header(test_app):
    """Test GET /api/status when Host header is missing."""
    app, webui = test_app
    client = app.test_client()

    # Note: Flask test client always adds Host header, so we test the fallback
    response = client.get("/api/status")

    assert response.status_code == 200
    data = json.loads(response.data)
    # Host header will be present in test, but we verify the field exists
    assert "request_host" in data


def test_get_status_uptime_increases(test_app):
    """Test that uptime increases over time."""
    app, webui = test_app
    client = app.test_client()

    # First request
    response1 = client.get("/api/status")
    data1 = json.loads(response1.data)
    uptime1 = data1["uptime_seconds"]

    # Wait a moment
    time.sleep(0.1)

    # Second request
    response2 = client.get("/api/status")
    data2 = json.loads(response2.data)
    uptime2 = data2["uptime_seconds"]

    # Uptime should have increased (or at least stayed the same)
    assert uptime2 >= uptime1


def test_get_diagnostic_full_info(test_app):
    """Test GET /api/diagnostic returns comprehensive diagnostic info."""
    app, webui = test_app
    client = app.test_client()

    mock_log_file = MagicMock()
    mock_log_file.exists.return_value = True
    mock_log_file.__str__.return_value = (
        "/home/user/.cache/pumaguard/pumaguard.log"
    )

    mock_log_dir = MagicMock()
    mock_log_dir.__truediv__.return_value = mock_log_file

    with patch(
        "pumaguard.web_routes.diagnostics.get_xdg_cache_home"
    ) as mock_xdg:
        mock_xdg.return_value.__truediv__.return_value = mock_log_dir

        response = client.get("/api/diagnostic")

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify server section
    assert "server" in data
    assert data["server"]["host"] == "0.0.0.0"
    assert data["server"]["port"] == 5000
    assert data["server"]["flutter_dir"] == "/path/to/flutter"
    assert data["server"]["build_dir"] == "/path/to/flutter/build/web"
    assert data["server"]["build_exists"] is True
    assert data["server"]["mdns_enabled"] is True
    assert data["server"]["mdns_name"] == "pumaguard"
    assert data["server"]["mdns_url"] == "http://pumaguard.local:5000"
    assert data["server"]["local_ip"] == "192.168.1.100"


def test_get_diagnostic_mdns_disabled(test_app):
    """Test GET /api/diagnostic when mDNS is disabled."""
    app, webui = test_app
    webui.mdns_enabled = False
    client = app.test_client()

    mock_log_file = MagicMock()
    mock_log_file.exists.return_value = True
    mock_log_file.__str__.return_value = (
        "/home/user/.cache/pumaguard/pumaguard.log"
    )

    mock_log_dir = MagicMock()
    mock_log_dir.__truediv__.return_value = mock_log_file

    with patch(
        "pumaguard.web_routes.diagnostics.get_xdg_cache_home"
    ) as mock_xdg:
        mock_xdg.return_value.__truediv__.return_value = mock_log_dir

        response = client.get("/api/diagnostic")

    assert response.status_code == 200
    data = json.loads(response.data)

    # mDNS fields should be None when disabled
    assert data["server"]["mdns_enabled"] is False
    assert data["server"]["mdns_name"] is None
    assert data["server"]["mdns_url"] is None


def test_get_diagnostic_build_not_exists(test_app):
    """Test GET /api/diagnostic when build directory doesn't exist."""
    app, webui = test_app
    webui.build_dir.exists.return_value = False
    client = app.test_client()

    mock_log_file = MagicMock()
    mock_log_file.exists.return_value = True
    mock_log_file.__str__.return_value = (
        "/home/user/.cache/pumaguard/pumaguard.log"
    )

    mock_log_dir = MagicMock()
    mock_log_dir.__truediv__.return_value = mock_log_file

    with patch(
        "pumaguard.web_routes.diagnostics.get_xdg_cache_home"
    ) as mock_xdg:
        mock_xdg.return_value.__truediv__.return_value = mock_log_dir

        response = client.get("/api/diagnostic")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["server"]["build_exists"] is False


def test_get_diagnostic_request_info(test_app):
    """Test GET /api/diagnostic includes request information."""
    app, webui = test_app
    client = app.test_client()

    mock_log_file = MagicMock()
    mock_log_file.exists.return_value = True
    mock_log_file.__str__.return_value = (
        "/home/user/.cache/pumaguard/pumaguard.log"
    )

    mock_log_dir = MagicMock()
    mock_log_dir.__truediv__.return_value = mock_log_file

    with patch(
        "pumaguard.web_routes.diagnostics.get_xdg_cache_home"
    ) as mock_xdg:
        mock_xdg.return_value.__truediv__.return_value = mock_log_dir

        response = client.get(
            "/api/diagnostic",
            headers={
                "Origin": "http://192.168.1.100:5000",
                "Referer": "http://192.168.1.100:5000/",
                "User-Agent": "Mozilla/5.0",
            },
        )

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify request section
    assert "request" in data
    assert "url" in data["request"]
    assert "base_url" in data["request"]
    assert "host" in data["request"]
    assert data["request"]["origin"] == "http://192.168.1.100:5000"
    assert data["request"]["referer"] == "http://192.168.1.100:5000/"
    assert data["request"]["user_agent"] == "Mozilla/5.0"


def test_get_diagnostic_missing_headers(test_app):
    """Test GET /api/diagnostic with missing request headers."""
    app, webui = test_app
    client = app.test_client()

    mock_log_file = MagicMock()
    mock_log_file.exists.return_value = True
    mock_log_file.__str__.return_value = (
        "/home/user/.cache/pumaguard/pumaguard.log"
    )

    mock_log_dir = MagicMock()
    mock_log_dir.__truediv__.return_value = mock_log_file

    with patch(
        "pumaguard.web_routes.diagnostics.get_xdg_cache_home"
    ) as mock_xdg:
        mock_xdg.return_value.__truediv__.return_value = mock_log_dir

        response = client.get("/api/diagnostic")

    assert response.status_code == 200
    data = json.loads(response.data)

    # Should have N/A for missing headers
    assert "request" in data
    # Some headers provided by test client, verify structure exists
    assert "origin" in data["request"]
    assert "referer" in data["request"]
    assert "user_agent" in data["request"]


def test_get_diagnostic_expected_behavior(test_app):
    """Test GET /api/diagnostic includes expected behavior guidance."""
    app, webui = test_app
    client = app.test_client()

    mock_log_file = MagicMock()
    mock_log_file.exists.return_value = True
    mock_log_file.__str__.return_value = (
        "/home/user/.cache/pumaguard/pumaguard.log"
    )

    mock_log_dir = MagicMock()
    mock_log_dir.__truediv__.return_value = mock_log_file

    with patch(
        "pumaguard.web_routes.diagnostics.get_xdg_cache_home"
    ) as mock_xdg:
        mock_xdg.return_value.__truediv__.return_value = mock_log_dir

        response = client.get("/api/diagnostic")

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify expected_behavior section
    assert "expected_behavior" in data
    assert "flutter_app_should_detect" in data["expected_behavior"]
    assert "api_calls_should_go_to" in data["expected_behavior"]


def test_get_diagnostic_troubleshooting_tips(test_app):
    """Test GET /api/diagnostic includes troubleshooting tips."""
    app, webui = test_app
    client = app.test_client()

    mock_log_file = MagicMock()
    mock_log_file.exists.return_value = True
    mock_log_file.__str__.return_value = (
        "/home/user/.cache/pumaguard/pumaguard.log"
    )

    mock_log_dir = MagicMock()
    mock_log_dir.__truediv__.return_value = mock_log_file

    with patch(
        "pumaguard.web_routes.diagnostics.get_xdg_cache_home"
    ) as mock_xdg:
        mock_xdg.return_value.__truediv__.return_value = mock_log_dir

        response = client.get("/api/diagnostic")

    assert response.status_code == 200
    data = json.loads(response.data)

    # Verify troubleshooting section
    assert "troubleshooting" in data
    assert "if_api_calls_go_to_localhost" in data["troubleshooting"]
    assert "if_page_doesnt_load" in data["troubleshooting"]
    assert "if_cors_errors" in data["troubleshooting"]


def test_get_diagnostic_log_file_path(test_app):
    """Test GET /api/diagnostic includes log file information."""
    app, webui = test_app
    client = app.test_client()

    mock_log_file = MagicMock()
    mock_log_file.exists.return_value = True
    mock_log_file.__str__.return_value = (
        "/home/user/.cache/pumaguard/pumaguard.log"
    )

    mock_log_dir = MagicMock()
    mock_log_dir.__truediv__.return_value = mock_log_file

    with patch(
        "pumaguard.web_routes.diagnostics.get_xdg_cache_home"
    ) as mock_xdg:
        mock_xdg.return_value.__truediv__.return_value = mock_log_dir

        response = client.get("/api/diagnostic")

    assert response.status_code == 200
    data = json.loads(response.data)

    assert "log_file" in data["server"]
    assert "log_file_exists" in data["server"]


def test_get_diagnostic_log_file_missing(test_app):
    """Test GET /api/diagnostic when log file doesn't exist."""
    app, webui = test_app
    client = app.test_client()

    mock_log_file = MagicMock()
    mock_log_file.exists.return_value = False
    mock_log_file.__str__.return_value = (
        "/home/user/.cache/pumaguard/pumaguard.log"
    )

    mock_log_dir = MagicMock()
    mock_log_dir.__truediv__.return_value = mock_log_file

    with patch(
        "pumaguard.web_routes.diagnostics.get_xdg_cache_home"
    ) as mock_xdg:
        mock_xdg.return_value.__truediv__.return_value = mock_log_dir

        response = client.get("/api/diagnostic")

    assert response.status_code == 200
    data = json.loads(response.data)

    assert data["server"]["log_file_exists"] is False


def test_get_status_zero_directories(test_app):
    """Test GET /api/status with no watched directories."""
    app, webui = test_app
    webui.image_directories = []
    client = app.test_client()

    response = client.get("/api/status")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["directories_count"] == 0


def test_get_status_just_started(test_app):
    """Test GET /api/status immediately after start."""
    app, webui = test_app
    webui.start_time = time.time()  # Just started
    client = app.test_client()

    response = client.get("/api/status")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["uptime_seconds"] >= 0
    assert data["uptime_seconds"] < 2  # Should be very small


# ---------------------------------------------------------------------------
# Sensors current endpoint tests
# ---------------------------------------------------------------------------


def test_get_sensors_current_not_available(test_app):
    """Test GET /api/sensors/current when sensors command is not installed."""
    app, _ = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.diagnostics._command_exists", return_value=False
    ):
        response = client.get("/api/sensors/current")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["available"] is False
    assert data["sensors"] == {}


def test_get_sensors_current_returns_data(test_app):
    """Test GET /api/sensors/current returns parsed sensor data."""
    app, _ = test_app
    client = app.test_client()

    sensors_json = {
        "coretemp-isa-0000": {
            "Adapter": "ISA adapter",
            "Core 0": {"temp2_input": 71.0, "temp2_max": 100.0},
        }
    }

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(sensors_json)

    with patch(
        "pumaguard.web_routes.diagnostics._command_exists", return_value=True
    ):
        with patch(
            "pumaguard.web_routes.diagnostics.subprocess.run",
            return_value=mock_result,
        ):
            response = client.get("/api/sensors/current")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["available"] is True
    assert "timestamp" in data
    assert "sensors" in data
    assert "coretemp-isa-0000" in data["sensors"]


def test_get_sensors_current_command_fails(test_app):
    """Test GET /api/sensors/current when sensors command returns non-zero."""
    app, _ = test_app
    client = app.test_client()

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "sensors: command not found"
    mock_result.stdout = ""

    with patch(
        "pumaguard.web_routes.diagnostics._command_exists", return_value=True
    ):
        with patch(
            "pumaguard.web_routes.diagnostics.subprocess.run",
            return_value=mock_result,
        ):
            response = client.get("/api/sensors/current")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["available"] is True
    assert "error" in data


# ---------------------------------------------------------------------------
# Sensors history endpoint tests
# ---------------------------------------------------------------------------


def test_get_sensors_history_not_available(test_app):
    """Test GET /api/sensors/history when journalctl or sensors is missing."""
    app, _ = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.diagnostics._command_exists", return_value=False
    ):
        response = client.get("/api/sensors/history")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["available"] is False
    assert data["readings"] == []


def test_get_sensors_history_journalctl_fails(test_app):
    """Test GET /api/sensors/history when journalctl returns non-zero."""
    app, _ = test_app
    client = app.test_client()

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "journalctl: access denied"
    mock_result.stdout = ""

    with patch(
        "pumaguard.web_routes.diagnostics._command_exists", return_value=True
    ):
        with patch(
            "pumaguard.web_routes.diagnostics.subprocess.run",
            return_value=mock_result,
        ):
            response = client.get("/api/sensors/history")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["available"] is True
    assert "error" in data


def test_get_sensors_history_with_temp_json_fixture(test_app):
    """Test GET /api/sensors/history using the temp.json journal fixture.

    temp.json contains 19 newline-delimited JSON objects representing one
    complete lm-sensors.service run captured via ``journalctl --output=json``.
    Lines 2–17 are _TRANSPORT=stdout entries sharing a single
    _SYSTEMD_INVOCATION_ID.  The sensors output covers four chips but only
    two have temperature readings:

    - cpu_thermal-virtual-0  →  temp1: +45.8 °C
    - rp1_adc-isa-0000       →  temp1: +50.2 °C

    pwmfan-isa-0000 (fan only) and rpi_volt-isa-0000 (voltage only) must be
    absent from the result because _parse_sensors_text filters them out.
    """
    app, _ = test_app
    client = app.test_client()

    fixture_path = (
        Path(__file__).parent / "fixtures" / "lm_sensors_journal.json"
    )
    fixture_content = fixture_path.read_text(encoding="utf-8")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = fixture_content
    mock_result.stderr = ""

    with patch(
        "pumaguard.web_routes.diagnostics._command_exists", return_value=True
    ):
        with patch(
            "pumaguard.web_routes.diagnostics.subprocess.run",
            return_value=mock_result,
        ):
            response = client.get("/api/sensors/history")

    assert response.status_code == 200
    data = json.loads(response.data)

    assert data["available"] is True

    readings = data["readings"]
    assert len(readings) == 1

    reading = readings[0]

    # Timestamp must be a valid ISO-8601 UTC string
    # __REALTIME_TIMESTAMP 1774494300404618 µs → 2026-03-26T03:05:00Z
    assert "timestamp" in reading
    ts = reading["timestamp"]
    assert ts == "2026-03-26T03:05:00Z", f"Unexpected timestamp: {ts!r}"

    sensors = reading["sensors"]

    # cpu_thermal-virtual-0 must be present with temp1 = 45.8 °C
    assert (
        "cpu_thermal-virtual-0" in sensors
    ), f"Expected cpu_thermal-virtual-0 in sensors, got: {list(sensors)}"
    assert sensors["cpu_thermal-virtual-0"]["temp1"]["temp_input"] == 45.8

    # rp1_adc-isa-0000 must be present with temp1 = 50.2 °C
    assert (
        "rp1_adc-isa-0000" in sensors
    ), f"Expected rp1_adc-isa-0000 in sensors, got: {list(sensors)}"
    assert sensors["rp1_adc-isa-0000"]["temp1"]["temp_input"] == 50.2

    # Fan-only chip must be absent
    assert (
        "pwmfan-isa-0000" not in sensors
    ), "pwmfan-isa-0000 should be filtered out (no temperature sensors)"

    # Voltage-only chip must be absent
    assert (
        "rpi_volt-isa-0000" not in sensors
    ), "rpi_volt-isa-0000 should be filtered out (no temperature sensors)"


def test_get_sensors_history_default_hours(test_app):
    """Test GET /api/sensors/history defaults to 1 hour when ?hours= absent."""
    app, _ = test_app
    client = app.test_client()

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch(
        "pumaguard.web_routes.diagnostics._command_exists", return_value=True
    ):
        with patch(
            "pumaguard.web_routes.diagnostics.subprocess.run",
            return_value=mock_result,
        ):
            response = client.get("/api/sensors/history")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["hours"] == 1


def test_get_sensors_history_hours_param(test_app):
    """Test GET /api/sensors/history accepts ?hours= and clamps to [1, 168]."""
    app, _ = test_app
    client = app.test_client()

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch(
        "pumaguard.web_routes.diagnostics._command_exists", return_value=True
    ):
        with patch(
            "pumaguard.web_routes.diagnostics.subprocess.run",
            return_value=mock_result,
        ):
            # Valid value within range
            response = client.get("/api/sensors/history?hours=6")
            data = json.loads(response.data)
            assert data["hours"] == 6

            # Value below minimum → clamped to 1
            response = client.get("/api/sensors/history?hours=0")
            data = json.loads(response.data)
            assert data["hours"] == 1

            # Value above maximum → clamped to 168
            response = client.get("/api/sensors/history?hours=9999")
            data = json.loads(response.data)
            assert data["hours"] == 168

            # Non-numeric value → falls back to default 1
            response = client.get("/api/sensors/history?hours=bad")
            data = json.loads(response.data)
            assert data["hours"] == 1


# ---------------------------------------------------------------------------
# _parse_sensors_text unit tests
# ---------------------------------------------------------------------------


def test_parse_sensors_text_empty():
    """_parse_sensors_text returns an empty dict for an empty string."""
    result = _parse_sensors_text("")
    assert result == {}


def test_parse_sensors_text_temp_only():
    """_parse_sensors_text returns only chips that have temperature readings.

    This uses the exact multi-chip sensors text produced by joining the
    MESSAGE fields from temp.json, which covers all four Pi chip types.
    Only the two chips with °C readings must appear in the result.
    """
    sensors_text = (
        "pwmfan-isa-0000\n"
        "Adapter: ISA adapter\n"
        "fan1:           0 RPM\n"
        "cpu_thermal-virtual-0\n"
        "Adapter: Virtual device\n"
        "temp1:        +45.8\xb0C\n"
        "rpi_volt-isa-0000\n"
        "Adapter: ISA adapter\n"
        "in0:              N/A\n"
        "rp1_adc-isa-0000\n"
        "Adapter: ISA adapter\n"
        "in1:         949.00 mV\n"
        "in2:           2.55 V\n"
        "in3:           1.35 V\n"
        "in4:           1.38 V\n"
        "temp1:        +50.2\xb0C\n"
    )

    result = _parse_sensors_text(sensors_text)

    # Only temperature-bearing chips survive
    assert set(result.keys()) == {"cpu_thermal-virtual-0", "rp1_adc-isa-0000"}

    assert result["cpu_thermal-virtual-0"]["temp1"]["temp_input"] == 45.8
    assert result["rp1_adc-isa-0000"]["temp1"]["temp_input"] == 50.2

    # Fan-only and voltage-only chips must be absent
    assert "pwmfan-isa-0000" not in result
    assert "rpi_volt-isa-0000" not in result


def test_parse_sensors_text_no_blank_separator():
    """_parse_sensors_text handles Pi-style output: no blank lines between.

    On the Raspberry Pi, ``sensors`` emits chip sections back-to-back
    without a blank line separating them.  The parser must correctly
    associate sensor value lines with the nearest preceding chip header
    even when there is no blank-line reset between sections.
    """
    # Two chips, no blank line between them — Pi output style
    sensors_text = (
        "cpu_thermal-virtual-0\n"
        "Adapter: Virtual device\n"
        "temp1:        +45.8\xb0C\n"
        "rp1_adc-isa-0000\n"
        "Adapter: ISA adapter\n"
        "temp1:        +50.2\xb0C\n"
    )

    result = _parse_sensors_text(sensors_text)

    assert "cpu_thermal-virtual-0" in result
    assert "rp1_adc-isa-0000" in result
    assert result["cpu_thermal-virtual-0"]["temp1"]["temp_input"] == 45.8
    assert result["rp1_adc-isa-0000"]["temp1"]["temp_input"] == 50.2
