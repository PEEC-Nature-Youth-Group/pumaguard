"""Tests for DHCP camera management routes."""

import json
from unittest.mock import (
    MagicMock,
)

import pytest
from flask import (
    Flask,
)

from pumaguard.presets import (
    Preset,
)
from pumaguard.web_routes.dhcp import (
    register_dhcp_routes,
)
from pumaguard.web_ui import (
    WebUI,
)

# pylint: disable=redefined-outer-name
# Pytest fixtures intentionally redefine names


@pytest.fixture
def mock_preset():
    """Create a mock Preset instance."""
    preset = MagicMock(spec=Preset)
    preset.cameras = []
    preset.save = MagicMock()
    return preset


@pytest.fixture
def test_app(mock_preset):
    """Create a test Flask app with DHCP routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    # Create a mock WebUI instance
    webui = MagicMock(spec=WebUI)
    webui.cameras = {}
    webui.plugs = {}
    webui.presets = mock_preset
    webui.presets.plugs = []
    webui.heartbeat = MagicMock()

    register_dhcp_routes(app, webui)

    return app, webui


def test_dhcp_event_add_camera(test_app):
    """Test adding a camera via DHCP event."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "action": "add",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "ip_address": "192.168.52.100",
        "hostname": "Microseven",
        "timestamp": "2024-01-15T10:30:00Z",
    }

    response = client.post(
        "/api/dhcp/event",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["message"] == "DHCP event processed"

    # Verify camera was added to webui.cameras
    assert "aa:bb:cc:dd:ee:ff" in webui.cameras
    camera = webui.cameras["aa:bb:cc:dd:ee:ff"]
    assert camera["hostname"] == "Microseven"
    assert camera["ip_address"] == "192.168.52.100"
    assert camera["status"] == "connected"

    # Verify settings were updated
    assert len(webui.presets.cameras) == 1
    webui.presets.save.assert_called()


def test_dhcp_event_old_camera(test_app):
    """Test renewing a camera lease via DHCP event."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "action": "old",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "ip_address": "192.168.52.100",
        "hostname": "Microseven",
        "timestamp": "2024-01-15T10:30:00Z",
    }

    response = client.post(
        "/api/dhcp/event",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"

    # Verify camera was added/updated
    assert "aa:bb:cc:dd:ee:ff" in webui.cameras
    assert webui.cameras["aa:bb:cc:dd:ee:ff"]["status"] == "connected"


def test_dhcp_event_delete_camera(test_app):
    """Test removing a camera via DHCP event."""
    app, webui = test_app
    client = app.test_client()

    # First add a camera
    webui.cameras["aa:bb:cc:dd:ee:ff"] = {
        "hostname": "Microseven",
        "ip_address": "192.168.52.100",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "connected",
    }

    # Now delete it
    payload = {
        "action": "del",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "ip_address": "192.168.52.100",
        "hostname": "Microseven",
        "timestamp": "2024-01-15T10:30:00Z",
    }

    response = client.post(
        "/api/dhcp/event",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"

    # Verify camera status was updated to disconnected
    assert "aa:bb:cc:dd:ee:ff" in webui.cameras
    assert webui.cameras["aa:bb:cc:dd:ee:ff"]["status"] == "disconnected"
    assert (
        webui.cameras["aa:bb:cc:dd:ee:ff"]["last_seen"]
        == "2024-01-15T10:30:00Z"
    )


def test_dhcp_event_missing_data(test_app):
    """Test DHCP event with missing JSON data."""
    app, _ = test_app
    client = app.test_client()

    response = client.post(
        "/api/dhcp/event",
        data="",
        content_type="application/json",
    )

    # The endpoint returns 500 when it can't parse the JSON
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data


def test_get_cameras(test_app):
    """Test getting list of all cameras."""
    app, webui = test_app
    client = app.test_client()

    # Add some cameras
    webui.cameras["aa:bb:cc:dd:ee:01"] = {
        "hostname": "Camera1",
        "ip_address": "192.168.52.101",
        "mac_address": "aa:bb:cc:dd:ee:01",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "connected",
    }
    webui.cameras["aa:bb:cc:dd:ee:02"] = {
        "hostname": "Camera2",
        "ip_address": "192.168.52.102",
        "mac_address": "aa:bb:cc:dd:ee:02",
        "last_seen": "2024-01-15T10:05:00Z",
        "status": "disconnected",
    }

    response = client.get("/api/dhcp/cameras")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["count"] == 2
    assert len(data["cameras"]) == 2

    # Verify camera data
    cameras = {cam["mac_address"]: cam for cam in data["cameras"]}
    assert "aa:bb:cc:dd:ee:01" in cameras
    assert cameras["aa:bb:cc:dd:ee:01"]["hostname"] == "Camera1"
    assert cameras["aa:bb:cc:dd:ee:02"]["status"] == "disconnected"


def test_get_camera_by_mac(test_app):
    """Test getting a specific camera by MAC address."""
    app, webui = test_app
    client = app.test_client()

    # Add a camera
    webui.cameras["aa:bb:cc:dd:ee:ff"] = {
        "hostname": "TestCamera",
        "ip_address": "192.168.52.100",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "connected",
    }

    response = client.get("/api/dhcp/cameras/aa:bb:cc:dd:ee:ff")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["hostname"] == "TestCamera"
    assert data["ip_address"] == "192.168.52.100"
    assert data["mac_address"] == "aa:bb:cc:dd:ee:ff"


def test_get_camera_not_found(test_app):
    """Test getting a camera that doesn't exist."""
    app, _ = test_app
    client = app.test_client()

    response = client.get("/api/dhcp/cameras/aa:bb:cc:dd:ee:99")

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Camera not found"


def test_add_camera_manually(test_app):
    """Test manually adding a camera via POST."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "hostname": "ManualCamera",
        "ip_address": "192.168.52.200",
        "mac_address": "aa:bb:cc:dd:ee:aa",
        "status": "connected",
    }

    response = client.post(
        "/api/dhcp/cameras",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["message"] == "Camera added successfully"
    assert data["camera"]["hostname"] == "ManualCamera"

    # Verify camera was added
    assert "aa:bb:cc:dd:ee:aa" in webui.cameras
    camera = webui.cameras["aa:bb:cc:dd:ee:aa"]
    assert camera["hostname"] == "ManualCamera"
    assert camera["ip_address"] == "192.168.52.200"
    assert camera["status"] == "connected"

    # Verify settings were updated
    assert len(webui.presets.cameras) == 1
    webui.presets.save.assert_called()


def test_add_camera_missing_fields(test_app):
    """Test adding a camera with missing required fields."""
    app, _webui = test_app
    client = app.test_client()

    payload = {
        "hostname": "IncompleteCamera",
        # Missing ip_address and mac_address
    }

    response = client.post(
        "/api/dhcp/cameras",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Missing required fields" in data["error"]


def test_add_camera_default_status(test_app):
    """Test adding a camera with default status."""
    app, _webui = test_app
    client = app.test_client()

    payload = {
        "hostname": "DefaultStatusCam",
        "ip_address": "192.168.52.201",
        "mac_address": "aa:bb:cc:dd:ee:bb",
        # No status provided
    }

    response = client.post(
        "/api/dhcp/cameras",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["camera"]["status"] == "connected"  # Default status


def test_clear_cameras(test_app):
    """Test clearing all camera records."""
    app, webui = test_app
    client = app.test_client()

    # Add some cameras first
    webui.cameras["aa:bb:cc:dd:ee:01"] = {
        "hostname": "Camera1",
        "ip_address": "192.168.52.101",
        "mac_address": "aa:bb:cc:dd:ee:01",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "connected",
    }
    webui.cameras["aa:bb:cc:dd:ee:02"] = {
        "hostname": "Camera2",
        "ip_address": "192.168.52.102",
        "mac_address": "aa:bb:cc:dd:ee:02",
        "last_seen": "2024-01-15T10:05:00Z",
        "status": "connected",
    }

    response = client.delete("/api/dhcp/cameras")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "2" in data["message"]

    # Verify cameras were cleared
    assert len(webui.cameras) == 0
    assert webui.presets.cameras == []
    webui.presets.save.assert_called()


def test_check_heartbeat_success(test_app):
    """Test manual heartbeat check endpoint."""
    app, webui = test_app
    client = app.test_client()

    # Add test cameras
    webui.cameras["aa:bb:cc:dd:ee:01"] = {
        "hostname": "Camera1",
        "ip_address": "192.168.52.101",
        "mac_address": "aa:bb:cc:dd:ee:01",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "connected",
    }
    webui.cameras["aa:bb:cc:dd:ee:02"] = {
        "hostname": "Camera2",
        "ip_address": "192.168.52.102",
        "mac_address": "aa:bb:cc:dd:ee:02",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "disconnected",
    }

    # Mock heartbeat check results
    webui.heartbeat.check_now.return_value = {
        "aa:bb:cc:dd:ee:01": True,
        "aa:bb:cc:dd:ee:02": False,
    }

    response = client.post("/api/dhcp/cameras/heartbeat")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["message"] == "Heartbeat check completed"
    assert "cameras" in data

    # Verify camera status in response
    cameras = data["cameras"]
    assert len(cameras) == 2
    assert cameras["aa:bb:cc:dd:ee:01"]["reachable"] is True
    assert cameras["aa:bb:cc:dd:ee:01"]["hostname"] == "Camera1"
    assert cameras["aa:bb:cc:dd:ee:02"]["reachable"] is False
    assert cameras["aa:bb:cc:dd:ee:02"]["hostname"] == "Camera2"

    webui.heartbeat.check_now.assert_called_once()


def test_check_heartbeat_no_cameras(test_app):
    """Test heartbeat check with no cameras."""
    app, webui = test_app
    client = app.test_client()

    webui.heartbeat.check_now.return_value = {}

    response = client.post("/api/dhcp/cameras/heartbeat")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["cameras"] == {}


def test_check_heartbeat_error(test_app):
    """Test heartbeat check with error."""
    app, webui = test_app
    client = app.test_client()

    webui.heartbeat.check_now.side_effect = Exception("Heartbeat failed")

    response = client.post("/api/dhcp/cameras/heartbeat")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Failed to perform heartbeat check"


def test_clear_cameras_empty(test_app):
    """Test clearing cameras when there are none."""
    app, _webui = test_app
    client = app.test_client()

    response = client.delete("/api/dhcp/cameras")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Cleared 0 camera record(s)" in data["message"]


# ============= Plug Tests =============


def test_dhcp_event_add_plug(test_app):
    """Test adding a plug via DHCP event."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "action": "add",
        "mac_address": "11:22:33:44:55:66",
        "ip_address": "192.168.52.150",
        "hostname": "shellyplugsg4-abcdef",
        "timestamp": "2024-01-15T10:30:00Z",
    }

    response = client.post(
        "/api/dhcp/event",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["message"] == "DHCP event processed"
    assert data["data"]["device_type"] == "plug"

    # Verify plug was added to webui.plugs
    assert "11:22:33:44:55:66" in webui.plugs
    plug = webui.plugs["11:22:33:44:55:66"]
    assert plug["hostname"] == "shellyplugsg4-abcdef"
    assert plug["ip_address"] == "192.168.52.150"
    assert plug["status"] == "connected"

    # Verify settings were updated
    assert len(webui.presets.plugs) == 1
    webui.presets.save.assert_called()


def test_dhcp_event_old_plug(test_app):
    """Test renewing a plug lease via DHCP event."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "action": "old",
        "mac_address": "11:22:33:44:55:66",
        "ip_address": "192.168.52.150",
        "hostname": "ShellyPlugS-Gen4",
        "timestamp": "2024-01-15T10:30:00Z",
    }

    response = client.post(
        "/api/dhcp/event",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"

    # Verify plug was added/updated
    assert "11:22:33:44:55:66" in webui.plugs
    assert webui.plugs["11:22:33:44:55:66"]["status"] == "connected"


def test_dhcp_event_delete_plug(test_app):
    """Test removing a plug via DHCP event."""
    app, webui = test_app
    client = app.test_client()

    # First add a plug
    webui.plugs["11:22:33:44:55:66"] = {
        "hostname": "shellyplug-test",
        "ip_address": "192.168.52.150",
        "mac_address": "11:22:33:44:55:66",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "connected",
    }

    # Now delete it
    payload = {
        "action": "del",
        "mac_address": "11:22:33:44:55:66",
        "ip_address": "192.168.52.150",
        "hostname": "shellyplug-test",
        "timestamp": "2024-01-15T10:30:00Z",
    }

    response = client.post(
        "/api/dhcp/event",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"

    # Verify plug status was updated to disconnected
    assert "11:22:33:44:55:66" in webui.plugs
    assert webui.plugs["11:22:33:44:55:66"]["status"] == "disconnected"
    assert (
        webui.plugs["11:22:33:44:55:66"]["last_seen"] == "2024-01-15T10:30:00Z"
    )


def test_get_plugs(test_app):
    """Test getting list of all plugs."""
    app, webui = test_app
    client = app.test_client()

    # Add some plugs
    webui.plugs["11:22:33:44:55:01"] = {
        "hostname": "Plug1",
        "ip_address": "192.168.52.151",
        "mac_address": "11:22:33:44:55:01",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "connected",
    }
    webui.plugs["11:22:33:44:55:02"] = {
        "hostname": "Plug2",
        "ip_address": "192.168.52.152",
        "mac_address": "11:22:33:44:55:02",
        "last_seen": "2024-01-15T10:05:00Z",
        "status": "disconnected",
    }

    response = client.get("/api/dhcp/plugs")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["count"] == 2
    assert len(data["plugs"]) == 2

    # Verify plug data
    plugs = {plug["mac_address"]: plug for plug in data["plugs"]}
    assert "11:22:33:44:55:01" in plugs
    assert plugs["11:22:33:44:55:01"]["hostname"] == "Plug1"
    assert plugs["11:22:33:44:55:02"]["status"] == "disconnected"


def test_get_plug_by_mac(test_app):
    """Test getting a specific plug by MAC address."""
    app, webui = test_app
    client = app.test_client()

    # Add a plug
    webui.plugs["11:22:33:44:55:66"] = {
        "hostname": "TestPlug",
        "ip_address": "192.168.52.150",
        "mac_address": "11:22:33:44:55:66",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "connected",
    }

    response = client.get("/api/dhcp/plugs/11:22:33:44:55:66")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["plug"]["hostname"] == "TestPlug"
    assert data["plug"]["ip_address"] == "192.168.52.150"
    assert data["plug"]["mac_address"] == "11:22:33:44:55:66"


def test_get_plug_not_found(test_app):
    """Test getting a plug that doesn't exist."""
    app, _ = test_app
    client = app.test_client()

    response = client.get("/api/dhcp/plugs/11:22:33:44:55:99")

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Plug not found"


def test_add_plug_manually(test_app):
    """Test manually adding a plug via POST."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "hostname": "ManualPlug",
        "ip_address": "192.168.52.200",
        "mac_address": "11:22:33:44:55:aa",
        "status": "connected",
    }

    response = client.post(
        "/api/dhcp/plugs",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["message"] == "Plug added successfully"
    assert data["plug"]["hostname"] == "ManualPlug"

    # Verify plug was added
    assert "11:22:33:44:55:aa" in webui.plugs
    plug = webui.plugs["11:22:33:44:55:aa"]
    assert plug["hostname"] == "ManualPlug"
    assert plug["ip_address"] == "192.168.52.200"
    assert plug["status"] == "connected"

    # Verify settings were updated
    assert len(webui.presets.plugs) == 1
    webui.presets.save.assert_called()


def test_add_plug_missing_fields(test_app):
    """Test adding a plug with missing required fields."""
    app, _webui = test_app
    client = app.test_client()

    payload = {
        "hostname": "IncompletePlug",
        # Missing ip_address and mac_address
    }

    response = client.post(
        "/api/dhcp/plugs",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "Missing required fields" in data["error"]


def test_add_plug_default_status(test_app):
    """Test adding a plug with default status."""
    app, _webui = test_app
    client = app.test_client()

    payload = {
        "hostname": "DefaultStatusPlug",
        "ip_address": "192.168.52.201",
        "mac_address": "11:22:33:44:55:bb",
        # No status provided
    }

    response = client.post(
        "/api/dhcp/plugs",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["plug"]["status"] == "connected"  # Default status


def test_clear_plugs(test_app):
    """Test clearing all plug records."""
    app, webui = test_app
    client = app.test_client()

    # Add some plugs first
    webui.plugs["11:22:33:44:55:01"] = {
        "hostname": "Plug1",
        "ip_address": "192.168.52.151",
        "mac_address": "11:22:33:44:55:01",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "connected",
    }
    webui.plugs["11:22:33:44:55:02"] = {
        "hostname": "Plug2",
        "ip_address": "192.168.52.152",
        "mac_address": "11:22:33:44:55:02",
        "last_seen": "2024-01-15T10:05:00Z",
        "status": "connected",
    }

    response = client.delete("/api/dhcp/plugs")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "2" in data["message"]

    # Verify plugs were cleared
    assert len(webui.plugs) == 0
    assert webui.presets.plugs == []
    webui.presets.save.assert_called()


def test_clear_plugs_empty(test_app):
    """Test clearing plugs when there are none."""
    app, _webui = test_app
    client = app.test_client()

    response = client.delete("/api/dhcp/plugs")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert "Cleared 0 plug record(s)" in data["message"]


def test_dhcp_event_unknown_device(test_app):
    """Test DHCP event with unknown device (not camera or plug)."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "action": "add",
        "mac_address": "99:88:77:66:55:44",
        "ip_address": "192.168.52.199",
        "hostname": "UnknownDevice",
        "timestamp": "2024-01-15T10:30:00Z",
    }

    response = client.post(
        "/api/dhcp/event",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["data"]["device_type"] == "unknown"

    # Verify device was not added to cameras or plugs
    assert "99:88:77:66:55:44" not in webui.cameras
    assert "99:88:77:66:55:44" not in webui.plugs
