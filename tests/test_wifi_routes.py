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
    detect_wireless_interface,
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
    with patch(
        "pumaguard.web_routes.wifi.detect_wifi_management_tool"
    ) as mock_tool:
        mock_tool.return_value = "wpa_cli"
        register_wifi_routes(app, webui)
    return app.test_client()


class TestWifiScan:
    """Tests for WiFi network scanning."""

    @patch("pumaguard.web_routes.wifi.time.sleep")
    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_scan_success(self, mock_run, mock_sleep, client):  # pylint: disable=unused-argument
        """Test successful WiFi scan."""

        # Mock wpa_cli scan trigger
        scan_trigger = MagicMock()
        scan_trigger.stdout = "OK\n"

        # Mock scan_results with stable results (for polling loop)
        # The loop needs at least 3 iterations with same count to exit
        stable_result = MagicMock()
        stable_result.stdout = (
            "bssid / frequency / signal level / flags / ssid\n"
            "00:11:22:33:44:55\t2437\t-55\t[WPA2-PSK-CCMP][ESS]\tMyNetwork\n"
            "AA:BB:CC:DD:EE:FF\t2462\t-70\t[ESS]\tOpenNetwork\n"
            "11:22:33:44:55:66\t2412\t-80\t[WPA-EAP-TKIP][ESS]\tWeakNetwork\n"
        )

        # Mock wpa_cli status for current connection
        status_result = MagicMock()
        status_result.stdout = "wpa_state=COMPLETED\nssid=MyNetwork\n"

        # Provide default for any additional polling calls
        def mock_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if "scan_results" in cmd:
                return stable_result
            if "status" in cmd:
                return status_result
            return MagicMock(stdout="")

        mock_run.side_effect = mock_subprocess

        response = client.get("/api/wifi/scan")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert "networks" in data
        networks = data["networks"]

        # Should have 3 networks, sorted by signal strength
        assert len(networks) == 3

        # Check first network (strongest signal, connected)
        assert networks[0]["ssid"] == "MyNetwork"
        assert networks[0]["signal"] == 90  # -55 dBm = 90%
        assert networks[0]["security"] == "WPA2"
        assert networks[0]["secured"] is True
        assert networks[0]["connected"] is True

        # Check second network (open network)
        assert networks[1]["ssid"] == "OpenNetwork"
        assert networks[1]["signal"] == 60  # -70 dBm = 60%
        assert networks[1]["security"] == "Open"
        assert networks[1]["secured"] is False
        assert networks[1]["connected"] is False

        # Check third network (weak signal)
        assert networks[2]["ssid"] == "WeakNetwork"
        assert networks[2]["signal"] == 40  # -80 dBm = 40%
        assert networks[2]["security"] == "WPA"
        assert networks[2]["secured"] is True

    @patch("pumaguard.web_routes.wifi.time.sleep")
    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_scan_timeout(self, mock_run, mock_sleep, client):  # pylint: disable=unused-argument
        """Test WiFi scan timeout."""
        # Mock wpa_cli scan trigger that times out
        mock_run.side_effect = subprocess.TimeoutExpired("wpa_cli", 30)

        response = client.get("/api/wifi/scan")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data
        assert "timed out" in data["error"].lower()

    @patch("pumaguard.web_routes.wifi.time.sleep")
    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_scan_filters_empty_ssids(self, mock_run, mock_sleep, client):  # pylint: disable=unused-argument
        """Test that empty SSIDs are filtered out."""

        # Mock scan_results with empty SSIDs
        stable_result = MagicMock()
        stable_result.stdout = (
            "bssid / frequency / signal level / flags / ssid\n"
            "00:11:22:33:44:55\t2437\t-55\t[WPA2-PSK-CCMP][ESS]\tMyNetwork\n"
            "AA:BB:CC:DD:EE:FF\t2462\t-70\t[ESS]\t\n"  # Empty SSID
            "11:22:33:44:55:66\t2412\t-60\t[WPA-PSK-CCMP][ESS]\tValidNetwork\n"
        )

        # Mock wpa_cli status
        status_result = MagicMock()
        status_result.stdout = "wpa_state=DISCONNECTED\n"

        def mock_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if "scan_results" in cmd:
                return stable_result
            if "status" in cmd:
                return status_result
            return MagicMock(stdout="OK\n")

        mock_run.side_effect = mock_subprocess

        response = client.get("/api/wifi/scan")

        assert response.status_code == 200
        data = json.loads(response.data)
        networks = data["networks"]

        # Should only have 2 valid networks (empty SSID filtered out)
        assert len(networks) == 2
        assert networks[0]["ssid"] == "MyNetwork"
        assert networks[1]["ssid"] == "ValidNetwork"

    @patch("pumaguard.web_routes.wifi.time.sleep")
    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_scan_handles_duplicates(self, mock_run, mock_sleep, client):  # pylint: disable=unused-argument
        """Test that duplicate SSIDs are filtered (keeping strongest)."""

        # Mock scan_results with duplicate SSID (different BSSID)
        stable_result = MagicMock()
        stable_result.stdout = (
            "bssid / frequency / signal level / flags / ssid\n"
            "00:11:22:33:44:55\t2437\t-55\t[WPA2-PSK-CCMP][ESS]\tMyNetwork\n"
            "00:11:22:33:44:66\t2462\t-80\t[WPA2-PSK-CCMP][ESS]\tMyNetwork\n"
        )

        # Mock wpa_cli status
        status_result = MagicMock()
        status_result.stdout = "wpa_state=DISCONNECTED\n"

        def mock_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if "scan_results" in cmd:
                return stable_result
            if "status" in cmd:
                return status_result
            return MagicMock(stdout="OK\n")

        mock_run.side_effect = mock_subprocess

        response = client.get("/api/wifi/scan")

        assert response.status_code == 200
        data = json.loads(response.data)
        networks = data["networks"]

        # Should only have 1 network (duplicate filtered, first seen kept)
        assert len(networks) == 1
        assert networks[0]["ssid"] == "MyNetwork"

    @patch("pumaguard.web_routes.wifi.time.sleep")
    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_scan_with_nmcli(self, mock_run, mock_sleep, client):  # pylint: disable=unused-argument
        """Test WiFi scan using NetworkManager (nmcli)."""
        # Create a new client with nmcli as the wifi tool
        app = Flask(__name__)
        webui = MagicMock()

        with patch(
            "pumaguard.web_routes.wifi.detect_wifi_management_tool"
        ) as mock_tool:
            mock_tool.return_value = "nmcli"
            register_wifi_routes(app, webui)

        test_client = app.test_client()

        # Mock nmcli rescan (returns nothing)
        rescan_result = MagicMock()
        rescan_result.stdout = ""

        # Mock nmcli list output
        list_result = MagicMock()
        list_result.stdout = (
            "MyNetwork:85:WPA2:yes\nOpenNetwork:60::no\nSecureNet:75:WPA2:no\n"
        )

        def mock_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if "rescan" in cmd:
                return rescan_result
            if "list" in cmd:
                return list_result
            return MagicMock(stdout="")

        mock_run.side_effect = mock_subprocess

        response = test_client.get("/api/wifi/scan")

        assert response.status_code == 200
        data = json.loads(response.data)
        networks = data["networks"]

        # Should have 3 networks, sorted by signal strength
        assert len(networks) == 3

        # Check first network (strongest signal, connected)
        assert networks[0]["ssid"] == "MyNetwork"
        assert networks[0]["signal"] == 85
        assert networks[0]["security"] == "WPA2"
        assert networks[0]["secured"] is True
        assert networks[0]["connected"] is True

        # Check second network (second strongest)
        assert networks[1]["ssid"] == "SecureNet"
        assert networks[1]["signal"] == 75
        assert networks[1]["security"] == "WPA2"
        assert networks[1]["secured"] is True
        assert networks[1]["connected"] is False

        # Check third network (weakest signal, open)
        assert networks[2]["ssid"] == "OpenNetwork"
        assert networks[2]["signal"] == 60
        assert networks[2]["security"] == "Open"
        assert networks[2]["secured"] is False
        assert networks[2]["connected"] is False


class TestGetWifiMode:
    """Tests for getting current WiFi mode."""

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    @patch(
        "builtins.open", new_callable=mock_open, read_data="ssid=pumaguard\n"
    )
    def test_get_mode_ap(self, mock_file, mock_run, client):  # pylint: disable=unused-argument
        """Test getting WiFi mode when in AP mode."""
        # Mock systemctl is-active hostapd (active)
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
        # Mock systemctl is-active hostapd (inactive)
        hostapd_result = MagicMock()
        hostapd_result.stdout = "inactive"

        # Mock wpa_cli status (connected)
        wpa_status = MagicMock()
        wpa_status.stdout = "wpa_state=COMPLETED\nssid=MyHomeNetwork\n"

        mock_run.side_effect = [hostapd_result, wpa_status]

        response = client.get("/api/wifi/mode")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["mode"] == "client"
        assert data["ssid"] == "MyHomeNetwork"
        assert data["connected"] is True

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_get_mode_client_connected_nmcli(self, mock_run, client):
        """Test getting WiFi mode when connected as client using nmcli."""
        # Create a new client with nmcli as the wifi tool
        app = Flask(__name__)
        webui = MagicMock()

        with patch(
            "pumaguard.web_routes.wifi.detect_wifi_management_tool"
        ) as mock_tool:
            mock_tool.return_value = "nmcli"
            register_wifi_routes(app, webui)

        test_client = app.test_client()

        # Mock systemctl is-active hostapd (inactive)
        hostapd_result = MagicMock()
        hostapd_result.stdout = "inactive"

        # Mock nmcli connection show --active (connected)
        nmcli_result = MagicMock()
        nmcli_result.stdout = "yes:MyHomeNetwork\n"

        mock_run.side_effect = [hostapd_result, nmcli_result]

        response = test_client.get("/api/wifi/mode")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["mode"] == "client"
        assert data["ssid"] == "MyHomeNetwork"
        assert data["connected"] is True

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_get_mode_client_disconnected(self, mock_run, client):
        """Test getting WiFi mode when not connected."""
        # Mock systemctl is-active hostapd (inactive)
        hostapd_result = MagicMock()
        hostapd_result.stdout = "inactive"

        # Mock wpa_cli status (disconnected)
        wpa_status = MagicMock()
        wpa_status.stdout = "wpa_state=DISCONNECTED\n"

        mock_run.side_effect = [hostapd_result, wpa_status]

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
        # Mock wpa_passphrase output with a PSK
        mock_wpa_result = MagicMock()
        mock_wpa_result.stdout = """network={
\tssid="TestNetwork"
\t#psk="testpassword123"
\tpsk=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
}
"""
        mock_run.return_value = mock_wpa_result

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
        assert (
            "wpa_psk=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
            in written_content
        )
        assert "wpa=2" in written_content

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
        assert "wpa=" not in written_content

    @patch("pumaguard.web_routes.wifi.time.sleep")
    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_set_client_mode_with_password(self, mock_run, mock_sleep, client):  # pylint: disable=unused-argument
        """Test connecting to WiFi network with password."""
        call_count = [0]

        def mock_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            call_count[0] += 1

            # wpa_cli list_networks
            if "list_networks" in cmd:
                result = MagicMock()
                result.stdout = "network id / ssid / bssid / flags\n"
                return result
            # wpa_cli add_network
            if "add_network" in cmd:
                result = MagicMock()
                result.stdout = "0\n"
                return result
            # wpa_cli status
            if "status" in cmd:
                result = MagicMock()
                result.stdout = "wpa_state=COMPLETED\nssid=MyNetwork\n"
                return result
            # All other commands
            return MagicMock(stdout="OK\n")

        mock_run.side_effect = mock_subprocess

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

    @patch("pumaguard.web_routes.wifi.time.sleep")
    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_set_client_mode_open_network(self, mock_run, mock_sleep, client):  # pylint: disable=unused-argument
        """Test connecting to open WiFi network."""

        def mock_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])

            # wpa_cli list_networks
            if "list_networks" in cmd:
                result = MagicMock()
                result.stdout = "network id / ssid / bssid / flags\n"
                return result
            # wpa_cli add_network
            if "add_network" in cmd:
                result = MagicMock()
                result.stdout = "0\n"
                return result
            # wpa_cli status
            if "status" in cmd:
                result = MagicMock()
                result.stdout = "wpa_state=COMPLETED\nssid=OpenNetwork\n"
                return result
            # All other commands
            return MagicMock(stdout="OK\n")

        mock_run.side_effect = mock_subprocess

        response = client.put(
            "/api/wifi/mode", json={"mode": "client", "ssid": "OpenNetwork"}
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["success"] is True
        assert "OpenNetwork" in data["message"]

    @patch("pumaguard.web_routes.wifi.time.sleep")
    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_set_client_mode_with_existing_networks(
        self, mock_run, mock_sleep, client
    ):  # pylint: disable=unused-argument
        """Test connecting when there are existing saved networks."""

        def mock_subprocess(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])

            # wpa_cli list_networks
            if "list_networks" in cmd:
                result = MagicMock()
                result.stdout = (
                    "network id / ssid / bssid / flags\n"
                    "0\tOldNetwork1\tany\t[CURRENT]\n"
                    "1\tOldNetwork2\tany\t\n"
                )
                return result
            # wpa_cli add_network
            if "add_network" in cmd:
                result = MagicMock()
                result.stdout = "2\n"
                return result
            # wpa_cli status
            if "status" in cmd:
                result = MagicMock()
                result.stdout = "wpa_state=COMPLETED\nssid=NewNetwork\n"
                return result
            # All other commands
            return MagicMock(stdout="OK\n")

        mock_run.side_effect = mock_subprocess

        response = client.put(
            "/api/wifi/mode",
            json={
                "mode": "client",
                "ssid": "NewNetwork",
                "password": "newpass",
            },
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
        # Mock wpa_cli list_networks
        list_result = MagicMock()
        list_result.stdout = (
            "network id / ssid / bssid / flags\n"
            "0\tOldNetwork\tany\t\n"
            "1\tAnotherNetwork\tany\t[CURRENT]\n"
        )

        # Mock remove_network and save_config
        remove_result = MagicMock()
        save_result = MagicMock()

        mock_run.side_effect = [list_result, remove_result, save_result]

        response = client.post("/api/wifi/forget", json={"ssid": "OldNetwork"})

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["success"] is True
        assert "OldNetwork" in data["message"]

    @patch("pumaguard.web_routes.wifi.subprocess.run")
    def test_forget_network_not_found(self, mock_run, client):
        """Test forgetting a network that doesn't exist."""
        # Mock wpa_cli list_networks with no matching SSID
        list_result = MagicMock()
        list_result.stdout = (
            "network id / ssid / bssid / flags\n0\tDifferentNetwork\tany\t\n"
        )

        mock_run.return_value = list_result

        response = client.post(
            "/api/wifi/forget", json={"ssid": "NonexistentNetwork"}
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_forget_network_missing_ssid(self, client):
        """Test forgetting network without SSID."""
        response = client.post("/api/wifi/forget", json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_forget_network_no_data(self, client):
        """Test forgetting network without request data."""
        response = client.post("/api/wifi/forget")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


class TestWirelessInterfaceDetection:
    """Tests for wireless interface detection."""

    @patch("pumaguard.web_routes.wifi.os.path.exists")
    @patch("pumaguard.web_routes.wifi.os.listdir")
    def test_detect_single_wireless_interface(self, mock_listdir, mock_exists):
        """Test detection of a single wireless interface."""
        # Mock /sys/class/net directory
        mock_listdir.return_value = ["lo", "eth0", "wlan0", "docker0"]

        # Mock wireless directory existence check
        def exists_side_effect(path):
            if path == "/sys/class/net":
                return True
            if "wlan0/wireless" in path:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        result = detect_wireless_interface()
        assert result == "wlan0"

    @patch("pumaguard.web_routes.wifi.os.path.exists")
    @patch("pumaguard.web_routes.wifi.os.listdir")
    def test_detect_multiple_wireless_interfaces(
        self, mock_listdir, mock_exists
    ):
        """Test detection when multiple wireless interfaces exist."""
        # Mock /sys/class/net directory with multiple wireless interfaces
        mock_listdir.return_value = ["lo", "eth0", "wlan0", "wlan1", "docker0"]

        # Mock wireless directory existence check
        def exists_side_effect(path):
            if path == "/sys/class/net":
                return True
            if "wlan0/wireless" in path or "wlan1/wireless" in path:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        result = detect_wireless_interface()
        # Should return the first one found
        assert result == "wlan0"

    @patch("pumaguard.web_routes.wifi.os.path.exists")
    @patch("pumaguard.web_routes.wifi.os.listdir")
    def test_detect_no_wireless_interface(self, mock_listdir, mock_exists):
        """Test detection when no wireless interface exists."""
        # Mock /sys/class/net directory with only wired interfaces
        mock_listdir.return_value = ["lo", "eth0", "docker0"]

        # Mock wireless directory existence check
        def exists_side_effect(path):
            if path == "/sys/class/net":
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        result = detect_wireless_interface()
        assert result is None

    @patch("pumaguard.web_routes.wifi.os.path.exists")
    @patch("pumaguard.web_routes.wifi.os.listdir")
    def test_detect_non_standard_interface_name(
        self, mock_listdir, mock_exists
    ):
        """Test detection with non-standard interface names."""
        # Some systems use wlp3s0 or similar names
        mock_listdir.return_value = ["lo", "eth0", "wlp3s0", "docker0"]

        # Mock wireless directory existence check
        def exists_side_effect(path):
            if path == "/sys/class/net":
                return True
            if "wlp3s0/wireless" in path:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        result = detect_wireless_interface()
        assert result == "wlp3s0"

    @patch("pumaguard.web_routes.wifi.os.path.exists")
    def test_detect_missing_sys_directory(self, mock_exists):
        """Test detection when /sys/class/net doesn't exist."""
        mock_exists.return_value = False

        result = detect_wireless_interface()
        assert result is None

    @patch("pumaguard.web_routes.wifi.os.path.exists")
    @patch("pumaguard.web_routes.wifi.os.listdir")
    def test_detect_filters_virtual_interfaces(
        self, mock_listdir, mock_exists
    ):
        """Test that virtual/bridge interfaces are filtered out."""
        # Mock directory with various interface types
        mock_listdir.return_value = [
            "lo",
            "eth0",
            "wlan0",
            "docker0",
            "veth1234",
            "br-abc123",
        ]

        # Mock wireless directory existence check
        def exists_side_effect(path):
            if path == "/sys/class/net":
                return True
            if "wlan0/wireless" in path:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        result = detect_wireless_interface()
        assert result == "wlan0"
