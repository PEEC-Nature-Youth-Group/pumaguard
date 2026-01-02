"""Tests for WiFi management routes."""

import json
import subprocess
from unittest.mock import (
    MagicMock,
    mock_open,
    patch,
)

import pytest
from flask import (
    Flask,
)

from pumaguard.web_routes.wifi import (
    register_wifi_routes,
)

# pylint: disable=redefined-outer-name
# Fixtures intentionally redefine names for pytest


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    flask_app = Flask(__name__)
    return flask_app


@pytest.fixture
def webui():
    """Create a mock WebUI instance."""
    return MagicMock()


@pytest.fixture
def client(app, webui):
    """Create a test client with registered routes."""
    register_wifi_routes(app, webui)
    return app.test_client()


class TestWifiScan:
    """Tests for WiFi network scanning."""

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_scan_success(self, mock_run, client):
        """Test successful WiFi scan."""
        # Mock the rescan command (returns nothing)
        rescan_result = MagicMock()
        rescan_result.stdout = ""

        # Mock the list command
        list_result = MagicMock()
        list_result.stdout = (
            "MyNetwork:85:WPA2:*\nOpenNetwork:60:::\nWeakNetwork:20:WPA:\n"
        )

        mock_run.side_effect = [rescan_result, list_result]

        response = client.get("/api/wifi/scan")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert "networks" in data
        networks = data["networks"]

        # Should have 3 networks
        assert len(networks) == 3

        # Check first network (strongest signal, connected)
        assert networks[0]["ssid"] == "MyNetwork"
        assert networks[0]["signal"] == 85
        assert networks[0]["security"] == "WPA2"
        assert networks[0]["secured"] is True
        assert networks[0]["connected"] is True

        # Check second network (open network)
        assert networks[1]["ssid"] == "OpenNetwork"
        assert networks[1]["signal"] == 60
        assert networks[1]["security"] == "Open"
        assert networks[1]["secured"] is False

        # Check third network (weak signal)
        assert networks[2]["ssid"] == "WeakNetwork"
        assert networks[2]["signal"] == 20

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_scan_timeout(self, mock_run, client):
        """Test WiFi scan timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("nmcli", 30)

        response = client.get("/api/wifi/scan")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data
        assert "timed out" in data["error"].lower()

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_scan_filters_empty_ssids(self, mock_run, client):
        """Test that empty SSIDs are filtered out."""
        rescan_result = MagicMock()
        rescan_result.stdout = ""

        list_result = MagicMock()
        list_result.stdout = (
            "MyNetwork:85:WPA2:\n"
            "--:60::\n"  # Empty SSID
            ":50::\n"  # No SSID
            "ValidNetwork:70:WPA:\n"
        )

        mock_run.side_effect = [rescan_result, list_result]

        response = client.get("/api/wifi/scan")

        assert response.status_code == 200
        data = json.loads(response.data)
        networks = data["networks"]

        # Should only have 2 valid networks
        assert len(networks) == 2
        assert networks[0]["ssid"] == "MyNetwork"
        assert networks[1]["ssid"] == "ValidNetwork"


class TestGetWifiMode:
    """Tests for getting current WiFi mode."""

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    @patch(
        "builtins.open", new_callable=mock_open, read_data="ssid=pumaguard\n"
    )
    def test_get_mode_ap(
        self, mock_file, mock_run, client
    ):  # pylint: disable=unused-argument
        """Test getting WiFi mode when in AP mode."""
        # Mock hostapd status check (active)
        hostapd_result = MagicMock()
        hostapd_result.stdout = "active"

        mock_run.return_value = hostapd_result

        response = client.get("/api/wifi/mode")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["mode"] == "ap"
        assert data["ssid"] == "pumaguard"
        assert data["connected"] is True

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_get_mode_client_connected(self, mock_run, client):
        """Test getting WiFi mode when connected as client."""
        # Mock hostapd status check (inactive)
        hostapd_result = MagicMock()
        hostapd_result.stdout = "inactive"

        # Mock nmcli connection show
        nmcli_result = MagicMock()
        nmcli_result.stdout = "802-11-wireless:wlan0:activated:MyHomeNetwork\n"

        mock_run.side_effect = [hostapd_result, nmcli_result]

        response = client.get("/api/wifi/mode")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["mode"] == "client"
        assert data["ssid"] == "MyHomeNetwork"
        assert data["connected"] is True

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_get_mode_client_disconnected(self, mock_run, client):
        """Test getting WiFi mode when not connected."""
        # Mock hostapd status check (inactive)
        hostapd_result = MagicMock()
        hostapd_result.stdout = "inactive"

        # Mock nmcli connection show (no active connections)
        nmcli_result = MagicMock()
        nmcli_result.stdout = ""

        mock_run.side_effect = [hostapd_result, nmcli_result]

        response = client.get("/api/wifi/mode")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["mode"] == "client"
        assert data["ssid"] is None
        assert data["connected"] is False


class TestSetWifiMode:
    """Tests for setting WiFi mode."""

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_set_ap_mode_with_password(self, mock_file, mock_run, client):
        """Test enabling AP mode with password."""
        mock_run.return_value = MagicMock()

        response = client.put(
            "/api/wifi/mode",
            json={
                "mode": "ap",
                "ssid": "TestNetwork",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["success"] is True
        assert "TestNetwork" in data["message"]

        # Verify hostapd config was written
        mock_file.assert_called_once()
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "ssid=TestNetwork" in written_content
        assert "wpa_passphrase=testpassword123" in written_content

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_set_ap_mode_open_network(self, mock_file, mock_run, client):
        """Test enabling AP mode without password (open network)."""
        mock_run.return_value = MagicMock()

        response = client.put(
            "/api/wifi/mode",
            json={"mode": "ap", "ssid": "OpenNetwork", "password": ""},
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["success"] is True

        # Verify hostapd config doesn't include password
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "wpa_passphrase" not in written_content

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_set_client_mode_with_password(self, mock_run, client):
        """Test connecting to WiFi network with password."""
        mock_run.return_value = MagicMock()

        response = client.put(
            "/api/wifi/mode",
            json={
                "mode": "client",
                "ssid": "MyNetwork",
                "password": "mypassword",
            },
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["success"] is True
        assert "MyNetwork" in data["message"]

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_set_client_mode_open_network(self, mock_run, client):
        """Test connecting to open WiFi network."""
        mock_run.return_value = MagicMock()

        response = client.put(
            "/api/wifi/mode", json={"mode": "client", "ssid": "OpenNetwork"}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["success"] is True

    def test_set_mode_invalid_mode(self, client):
        """Test setting invalid WiFi mode."""
        response = client.put(
            "/api/wifi/mode", json={"mode": "invalid", "ssid": "TestNetwork"}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_set_mode_missing_ssid(self, client):
        """Test setting mode without SSID."""
        response = client.put("/api/wifi/mode", json={"mode": "ap"})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "SSID" in data["error"]

    def test_set_mode_no_data(self, client):
        """Test setting mode without request data."""
        response = client.put("/api/wifi/mode")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


class TestForgetWifiNetwork:
    """Tests for forgetting WiFi networks."""

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_forget_network_success(self, mock_run, client):
        """Test successfully forgetting a network."""
        mock_run.return_value = MagicMock()

        response = client.post("/api/wifi/forget", json={"ssid": "OldNetwork"})

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["success"] is True
        assert "OldNetwork" in data["message"]

    def test_forget_network_missing_ssid(self, client):
        """Test forgetting network without SSID."""
        response = client.post("/api/wifi/forget", json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        # Empty JSON is caught by "No data provided" check
        assert data["error"] in ["No data provided", "SSID is required"]

    def test_forget_network_no_data(self, client):
        """Test forgetting network without request data."""
        response = client.post("/api/wifi/forget")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_forget_network_not_found(self, mock_run, client):
        """Test forgetting a network that doesn't exist."""
        mock_run.side_effect = subprocess.CalledProcessError(
            10,
            "nmcli",
            stderr="Error: unknown connection 'NonexistentNetwork'",
        )

        response = client.post(
            "/api/wifi/forget", json={"ssid": "NonexistentNetwork"}
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data
