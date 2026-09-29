"""Tests for the WiFi client configuration routes (web_routes/wifi.py)."""

# pylint: disable=redefined-outer-name
# Pytest fixtures intentionally redefine names
# pylint: disable=protected-access

import subprocess
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
from pumaguard.web_routes.wifi import (
    _build_wpa_conf,
    _get_current_ssid,
    _get_ip_address,
    _get_signal_percent,
    _iface_exists,
    _restart_wpa_supplicant,
    _scan_networks,
    _write_wpa_conf,
    apply_wifi_networks_from_settings,
    register_wifi_routes,
)
from pumaguard.web_ui import (
    WebUI,
)


def _completed(returncode=0, stdout="", stderr=""):
    """Build a subprocess.CompletedProcess for mocking subprocess.run."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


@pytest.fixture
def mock_preset():
    """Create a mock Preset instance."""
    preset = MagicMock(spec=Settings)
    preset.wifi_networks = []
    preset.save = MagicMock()
    return preset


@pytest.fixture
def test_app(mock_preset):
    """Create a test Flask app with wifi routes registered."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    webui = MagicMock(spec=WebUI)
    webui.presets = mock_preset

    register_wifi_routes(app, webui)

    return app, webui


# ---------------------------------------------------------------------------
# Helpers: _iface_exists / _get_current_ssid / _get_ip_address /
# _get_signal_percent
# ---------------------------------------------------------------------------


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_iface_exists_true(mock_run):
    """Interface is reported present when the command succeeds."""
    mock_run.return_value = _completed(returncode=0)
    assert _iface_exists() is True


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_iface_exists_false(mock_run):
    """Interface is reported absent when the command fails."""
    mock_run.return_value = _completed(returncode=1)
    assert _iface_exists() is False


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_current_ssid_connected(mock_run):
    """SSID is parsed out of `iw dev wifi1 link` output when connected."""
    mock_run.return_value = _completed(
        returncode=0, stdout="Connected to aa:bb:cc\n\tSSID: HomeNet\n"
    )
    assert _get_current_ssid() == "HomeNet"


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_current_ssid_not_connected(mock_run):
    """Returns None when the adapter reports 'Not connected'."""
    mock_run.return_value = _completed(returncode=0, stdout="Not connected.")
    assert _get_current_ssid() is None


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_current_ssid_command_failure(mock_run):
    """Returns None when the underlying command fails."""
    mock_run.return_value = _completed(returncode=1, stdout="")
    assert _get_current_ssid() is None


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_current_ssid_no_match(mock_run):
    """Returns None when output doesn't contain an SSID line."""
    mock_run.return_value = _completed(returncode=0, stdout="garbage output")
    assert _get_current_ssid() is None


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_ip_address_success(mock_run):
    """IPv4 address is parsed from `ip -4 addr show` output."""
    mock_run.return_value = _completed(
        returncode=0,
        stdout="inet 192.168.1.42/24 brd 192.168.1.255 scope global wifi1",
    )
    assert _get_ip_address() == "192.168.1.42"


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_ip_address_command_failure(mock_run):
    """Returns None when the command fails."""
    mock_run.return_value = _completed(returncode=1)
    assert _get_ip_address() is None


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_ip_address_no_match(mock_run):
    """Returns None when no inet address line is present."""
    mock_run.return_value = _completed(returncode=0, stdout="no addr here")
    assert _get_ip_address() is None


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_signal_percent_mid_range(mock_run):
    """A -70 dBm signal maps to 60%."""
    mock_run.return_value = _completed(
        returncode=0, stdout="signal: -70 dBm"
    )
    assert _get_signal_percent() == 60


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_signal_percent_clamped_high(mock_run):
    """Signals stronger than -50 dBm clamp to 100%."""
    mock_run.return_value = _completed(
        returncode=0, stdout="signal: -30 dBm"
    )
    assert _get_signal_percent() == 100


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_signal_percent_clamped_low(mock_run):
    """Signals weaker than -100 dBm clamp to 0%."""
    mock_run.return_value = _completed(
        returncode=0, stdout="signal: -120 dBm"
    )
    assert _get_signal_percent() == 0


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_signal_percent_command_failure(mock_run):
    """Returns None when the command fails."""
    mock_run.return_value = _completed(returncode=1)
    assert _get_signal_percent() is None


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_get_signal_percent_no_match(mock_run):
    """Returns None when no signal line can be parsed."""
    mock_run.return_value = _completed(returncode=0, stdout="nothing here")
    assert _get_signal_percent() is None


# ---------------------------------------------------------------------------
# _build_wpa_conf
# ---------------------------------------------------------------------------


def test_build_wpa_conf_secured_network():
    """A network with a psk gets a psk line, not key_mgmt=NONE."""
    conf = _build_wpa_conf(
        [{"ssid": "HomeNet", "psk": "supersecret", "priority": 5}]
    )
    assert 'ssid="HomeNet"' in conf
    assert 'psk="supersecret"' in conf
    assert "key_mgmt=NONE" not in conf
    assert "priority=5" in conf


def test_build_wpa_conf_open_network():
    """A network without a psk is rendered as an open (key_mgmt=NONE) net."""
    conf = _build_wpa_conf([{"ssid": "OpenNet"}])
    assert 'ssid="OpenNet"' in conf
    assert "key_mgmt=NONE" in conf
    assert 'psk="' not in conf
    # Default priority is 0 when not specified.
    assert "priority=0" in conf


def test_build_wpa_conf_multiple_networks():
    """Multiple networks each get their own network={} block."""
    conf = _build_wpa_conf(
        [
            {"ssid": "NetA", "psk": "pw1"},
            {"ssid": "NetB", "psk": "pw2"},
        ]
    )
    assert conf.count("network={") == 2
    assert 'ssid="NetA"' in conf
    assert 'ssid="NetB"' in conf


# ---------------------------------------------------------------------------
# _write_wpa_conf / _restart_wpa_supplicant
# ---------------------------------------------------------------------------


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_write_wpa_conf_success(mock_run):
    """Successful write returns (True, "")."""
    mock_run.return_value = _completed(returncode=0)
    ok, err = _write_wpa_conf([{"ssid": "NetA", "psk": "pw"}])
    assert ok is True
    assert not err
    mock_run.assert_called_once()


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_write_wpa_conf_failure(mock_run):
    """Non-zero return code yields a generic, UI-safe error message."""
    mock_run.return_value = _completed(
        returncode=1, stderr="permission denied"
    )
    ok, err = _write_wpa_conf([{"ssid": "NetA"}])
    assert ok is False
    assert err == "Failed to write WiFi configuration."


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_write_wpa_conf_exception(mock_run):
    """Exceptions raised by subprocess.run are caught and reported."""
    mock_run.side_effect = OSError("boom")
    ok, err = _write_wpa_conf([{"ssid": "NetA"}])
    assert ok is False
    assert err == "Failed to write WiFi configuration."


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_restart_wpa_supplicant_success(mock_run):
    """Successful restart returns (True, "")."""
    mock_run.return_value = _completed(returncode=0)
    ok, err = _restart_wpa_supplicant()
    assert ok is True
    assert not err


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_restart_wpa_supplicant_failure(mock_run):
    """Non-zero return code yields a generic, UI-safe error message."""
    mock_run.return_value = _completed(returncode=1, stderr="no such unit")
    ok, err = _restart_wpa_supplicant()
    assert ok is False
    assert err == "Failed to restart WiFi service."


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_restart_wpa_supplicant_exception(mock_run):
    """Exceptions raised by subprocess.run are caught and reported."""
    mock_run.side_effect = OSError("boom")
    ok, err = _restart_wpa_supplicant()
    assert ok is False
    assert err == "Failed to restart WiFi service."


# ---------------------------------------------------------------------------
# _scan_networks
# ---------------------------------------------------------------------------


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_scan_networks_parses_and_sorts(mock_run):
    """Networks are parsed with security/signal info and sorted by signal."""
    scan_output = (
        "BSS 00:11:22:33:44:55(on wifi1)\n"
        "\tSSID: HomeNet\n"
        "\tsignal: -60.00 dBm\n"
        "\tRSN:\t * Version: 1\n"
        "BSS 66:77:88:99:aa:bb(on wifi1)\n"
        "\tSSID: OfficeNet\n"
        "\tsignal: -75.00 dBm\n"
        "\tWPA:\t * Version: 1\n"
        "BSS cc:dd:ee:ff:00:11(on wifi1)\n"
        "\tSSID: OpenNet\n"
        "\tsignal: -90.00 dBm\n"
    )
    mock_run.side_effect = [
        _completed(returncode=0),  # sudo ip link set wifi1 up
        _completed(returncode=0),  # iw dev wifi1 scan flush
        _completed(returncode=0, stdout=scan_output),  # iw dev wifi1 scan
    ]

    networks = _scan_networks()

    assert [n["ssid"] for n in networks] == [
        "HomeNet",
        "OfficeNet",
        "OpenNet",
    ]
    home = next(n for n in networks if n["ssid"] == "HomeNet")
    assert home["signal"] == 80
    assert home["security"] == "WPA2"
    assert home["secured"] is True

    office = next(n for n in networks if n["ssid"] == "OfficeNet")
    assert office["signal"] == 50
    assert office["security"] == "WPA"
    assert office["secured"] is True

    open_net = next(n for n in networks if n["ssid"] == "OpenNet")
    assert open_net["signal"] == 20
    assert open_net["security"] == "Open"
    assert open_net["secured"] is False


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_scan_networks_dedups_keeping_stronger_signal(mock_run):
    """Duplicate SSIDs collapse to the entry with the higher signal."""
    scan_output = (
        "BSS 00:11:22:33:44:55(on wifi1)\n"
        "\tSSID: DupNet\n"
        "\tsignal: -80.00 dBm\n"
        "BSS 66:77:88:99:aa:bb(on wifi1)\n"
        "\tSSID: DupNet\n"
        "\tsignal: -50.00 dBm\n"
        "\tRSN:\t * Version: 1\n"
    )
    mock_run.side_effect = [
        _completed(returncode=0),
        _completed(returncode=0),
        _completed(returncode=0, stdout=scan_output),
    ]

    networks = _scan_networks()

    assert len(networks) == 1
    assert networks[0]["ssid"] == "DupNet"
    assert networks[0]["signal"] == 100
    assert networks[0]["security"] == "WPA2"
    assert networks[0]["secured"] is True


@patch("pumaguard.web_routes.wifi.subprocess.run")
def test_scan_networks_scan_failure_returns_empty(mock_run):
    """A failed `iw scan` command yields an empty list, not an exception."""
    mock_run.side_effect = [
        _completed(returncode=0),
        _completed(returncode=0),
        _completed(returncode=1, stderr="device or resource busy"),
    ]

    assert _scan_networks() == []


# ---------------------------------------------------------------------------
# apply_wifi_networks_from_settings
# ---------------------------------------------------------------------------


def test_apply_wifi_networks_no_networks_is_noop():
    """Nothing is written/restarted if there are no persisted networks."""
    webui = MagicMock(spec=WebUI)
    webui.presets = MagicMock(spec=Settings)
    webui.presets.wifi_networks = []

    with patch(
        "pumaguard.web_routes.wifi._write_wpa_conf"
    ) as mock_write, patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant"
    ) as mock_restart:
        apply_wifi_networks_from_settings(webui)

    mock_write.assert_not_called()
    mock_restart.assert_not_called()


def test_apply_wifi_networks_success():
    """Persisted networks are written and the service restarted."""
    webui = MagicMock(spec=WebUI)
    webui.presets = MagicMock(spec=Settings)
    networks = [{"ssid": "HomeNet", "psk": "pw"}]
    webui.presets.wifi_networks = networks

    with patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(True, ""),
    ) as mock_write, patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant",
        return_value=(True, ""),
    ) as mock_restart:
        apply_wifi_networks_from_settings(webui)

    mock_write.assert_called_once_with(networks)
    mock_restart.assert_called_once()


def test_apply_wifi_networks_write_failure_skips_restart():
    """If writing the config fails, the service is not restarted."""
    webui = MagicMock(spec=WebUI)
    webui.presets = MagicMock(spec=Settings)
    webui.presets.wifi_networks = [{"ssid": "HomeNet"}]

    with patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(False, "write failed"),
    ), patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant"
    ) as mock_restart:
        apply_wifi_networks_from_settings(webui)

    mock_restart.assert_not_called()


def test_apply_wifi_networks_restart_failure_does_not_raise():
    """If the restart fails, the function logs and returns without error."""
    webui = MagicMock(spec=WebUI)
    webui.presets = MagicMock(spec=Settings)
    webui.presets.wifi_networks = [{"ssid": "HomeNet"}]

    with patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(True, ""),
    ), patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant",
        return_value=(False, "restart failed"),
    ):
        apply_wifi_networks_from_settings(webui)  # should not raise


# ---------------------------------------------------------------------------
# GET /api/wifi/mode
# ---------------------------------------------------------------------------


def test_get_wifi_mode_not_present(test_app):
    """Reports present=False when the adapter is not plugged in."""
    app, _webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=False
    ):
        response = client.get("/api/wifi/mode")

    assert response.status_code == 200
    data = response.get_json()
    assert data == {
        "present": False,
        "connected": False,
        "ssid": None,
        "ip_address": None,
        "signal": None,
        "interface": "wifi1",
    }


def test_get_wifi_mode_connected(test_app):
    """Reports connection details when associated with a network."""
    app, _webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=True
    ), patch(
        "pumaguard.web_routes.wifi._get_current_ssid",
        return_value="HomeNet",
    ), patch(
        "pumaguard.web_routes.wifi._get_ip_address",
        return_value="192.168.1.5",
    ), patch(
        "pumaguard.web_routes.wifi._get_signal_percent", return_value=75
    ):
        response = client.get("/api/wifi/mode")

    assert response.status_code == 200
    data = response.get_json()
    assert data == {
        "present": True,
        "connected": True,
        "ssid": "HomeNet",
        "ip_address": "192.168.1.5",
        "signal": 75,
        "interface": "wifi1",
    }


def test_get_wifi_mode_present_not_connected(test_app):
    """Signal is not looked up at all when there is no current SSID."""
    app, _webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=True
    ), patch(
        "pumaguard.web_routes.wifi._get_current_ssid", return_value=None
    ), patch(
        "pumaguard.web_routes.wifi._get_ip_address", return_value=None
    ), patch(
        "pumaguard.web_routes.wifi._get_signal_percent"
    ) as mock_signal:
        response = client.get("/api/wifi/mode")

    assert response.status_code == 200
    data = response.get_json()
    assert data["connected"] is False
    assert data["ssid"] is None
    assert data["signal"] is None
    mock_signal.assert_not_called()


# ---------------------------------------------------------------------------
# GET /api/wifi/scan
# ---------------------------------------------------------------------------


def test_scan_wifi_interface_not_present(test_app):
    """Returns 503 when the USB adapter is not plugged in."""
    app, _webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=False
    ):
        response = client.get("/api/wifi/scan")

    assert response.status_code == 503
    assert "error" in response.get_json()


def test_scan_wifi_annotates_connected_network(test_app):
    """The currently-associated SSID is flagged as connected in results."""
    app, _webui = test_app
    client = app.test_client()

    scanned = [
        {
            "ssid": "HomeNet",
            "signal": 80,
            "security": "WPA2",
            "secured": True,
        },
        {
            "ssid": "OfficeNet",
            "signal": 50,
            "security": "Open",
            "secured": False,
        },
    ]

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=True
    ), patch(
        "pumaguard.web_routes.wifi._get_current_ssid",
        return_value="HomeNet",
    ), patch(
        "pumaguard.web_routes.wifi._scan_networks", return_value=scanned
    ):
        response = client.get("/api/wifi/scan")

    assert response.status_code == 200
    data = response.get_json()
    by_ssid = {n["ssid"]: n for n in data["networks"]}
    assert by_ssid["HomeNet"]["connected"] is True
    assert by_ssid["OfficeNet"]["connected"] is False


# ---------------------------------------------------------------------------
# POST /api/wifi/mode
# ---------------------------------------------------------------------------


def test_set_wifi_mode_no_data(test_app):
    """Empty JSON body is rejected with 400."""
    app, _webui = test_app
    client = app.test_client()

    response = client.post("/api/wifi/mode", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_set_wifi_mode_missing_ssid(test_app):
    """A blank/missing ssid is rejected with 400."""
    app, _webui = test_app
    client = app.test_client()

    response = client.post("/api/wifi/mode", json={"ssid": "   "})

    assert response.status_code == 400
    assert "ssid is required" in response.get_json()["error"]


def test_set_wifi_mode_adds_new_network(test_app):
    """A brand new SSID is appended with the next-highest priority."""
    app, webui = test_app
    webui.presets.wifi_networks = []
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(True, ""),
    ) as mock_write, patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant",
        return_value=(True, ""),
    ):
        response = client.post(
            "/api/wifi/mode",
            json={"ssid": "NewNet", "password": "secret123"},
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "NewNet" in data["message"]

    written_networks = mock_write.call_args[0][0]
    assert written_networks == [
        {"ssid": "NewNet", "psk": "secret123", "priority": 0}
    ]
    assert webui.presets.wifi_networks == written_networks
    webui.presets.save.assert_called_once()


def test_set_wifi_mode_updates_existing_network(test_app):
    """An existing SSID has its password updated in place."""
    app, webui = test_app
    webui.presets.wifi_networks = [
        {"ssid": "NewNet", "psk": "old", "priority": 3}
    ]
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(True, ""),
    ) as mock_write, patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant",
        return_value=(True, ""),
    ):
        response = client.post(
            "/api/wifi/mode",
            json={"ssid": "NewNet", "password": "updated"},
        )

    assert response.status_code == 200
    written_networks = mock_write.call_args[0][0]
    assert written_networks == [
        {"ssid": "NewNet", "psk": "updated", "priority": 3}
    ]


def test_set_wifi_mode_write_failure(test_app):
    """A config-write failure surfaces as 500 and skips persistence."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(False, "Failed to write WiFi configuration."),
    ), patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant"
    ) as mock_restart:
        response = client.post(
            "/api/wifi/mode", json={"ssid": "NewNet", "password": "pw"}
        )

    assert response.status_code == 500
    data = response.get_json()
    assert data["success"] is False
    mock_restart.assert_not_called()
    webui.presets.save.assert_not_called()


def test_set_wifi_mode_restart_failure(test_app):
    """A service-restart failure surfaces as 500 and skips persistence."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(True, ""),
    ), patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant",
        return_value=(False, "Failed to restart WiFi service."),
    ):
        response = client.post(
            "/api/wifi/mode", json={"ssid": "NewNet", "password": "pw"}
        )

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    webui.presets.save.assert_not_called()


def test_set_wifi_mode_persistence_failure_not_fatal(test_app):
    """If saving settings fails after a successful reconnect, still 200."""
    app, webui = test_app
    webui.presets.save.side_effect = OSError("disk full")
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(True, ""),
    ), patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant",
        return_value=(True, ""),
    ):
        response = client.post(
            "/api/wifi/mode", json={"ssid": "NewNet", "password": "pw"}
        )

    assert response.status_code == 200
    assert response.get_json()["success"] is True


# ---------------------------------------------------------------------------
# POST /api/wifi/forget
# ---------------------------------------------------------------------------


def test_forget_wifi_network_no_data(test_app):
    """Empty JSON body is rejected with 400."""
    app, _webui = test_app
    client = app.test_client()

    response = client.post("/api/wifi/forget", json={})

    assert response.status_code == 400


def test_forget_wifi_network_missing_ssid(test_app):
    """A blank/missing ssid is rejected with 400."""
    app, _webui = test_app
    client = app.test_client()

    response = client.post("/api/wifi/forget", json={"ssid": ""})

    assert response.status_code == 400


def test_forget_wifi_network_not_found(test_app):
    """Requesting an unknown SSID returns a generic 404."""
    app, webui = test_app
    webui.presets.wifi_networks = [{"ssid": "Other"}]
    client = app.test_client()

    response = client.post("/api/wifi/forget", json={"ssid": "Missing"})

    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "Missing" not in data["message"]


def test_forget_wifi_network_success_with_iface_present(test_app):
    """Removes the network, rewrites config, and restarts the service."""
    app, webui = test_app
    webui.presets.wifi_networks = [{"ssid": "NetA"}, {"ssid": "NetB"}]
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=True
    ), patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(True, ""),
    ) as mock_write, patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant",
        return_value=(True, ""),
    ) as mock_restart:
        response = client.post("/api/wifi/forget", json={"ssid": "NetA"})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert webui.presets.wifi_networks == [{"ssid": "NetB"}]
    mock_write.assert_called_once_with([{"ssid": "NetB"}])
    mock_restart.assert_called_once()
    webui.presets.save.assert_called_once()


def test_forget_wifi_network_skips_system_calls_when_iface_absent(test_app):
    """The persisted list is still updated even if the adapter is unplugged."""
    app, webui = test_app
    webui.presets.wifi_networks = [{"ssid": "NetA"}]
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=False
    ), patch(
        "pumaguard.web_routes.wifi._write_wpa_conf"
    ) as mock_write, patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant"
    ) as mock_restart:
        response = client.post("/api/wifi/forget", json={"ssid": "NetA"})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    mock_write.assert_not_called()
    mock_restart.assert_not_called()
    assert webui.presets.wifi_networks == []
    webui.presets.save.assert_called_once()


def test_forget_wifi_network_write_failure(test_app):
    """A config-write failure surfaces as 500 and skips persistence."""
    app, webui = test_app
    webui.presets.wifi_networks = [{"ssid": "NetA"}]
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=True
    ), patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(False, "Failed to write WiFi configuration."),
    ), patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant"
    ) as mock_restart:
        response = client.post("/api/wifi/forget", json={"ssid": "NetA"})

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    mock_restart.assert_not_called()
    webui.presets.save.assert_not_called()


def test_forget_wifi_network_restart_failure(test_app):
    """A service-restart failure surfaces as 500 and skips persistence."""
    app, webui = test_app
    webui.presets.wifi_networks = [{"ssid": "NetA"}]
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=True
    ), patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(True, ""),
    ), patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant",
        return_value=(False, "Failed to restart WiFi service."),
    ):
        response = client.post("/api/wifi/forget", json={"ssid": "NetA"})

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    webui.presets.save.assert_not_called()


def test_forget_wifi_network_persistence_failure_not_fatal(test_app):
    """If saving settings fails after a successful removal, still 200."""
    app, webui = test_app
    webui.presets.wifi_networks = [{"ssid": "NetA"}]
    webui.presets.save.side_effect = OSError("disk full")
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.wifi._iface_exists", return_value=True
    ), patch(
        "pumaguard.web_routes.wifi._write_wpa_conf",
        return_value=(True, ""),
    ), patch(
        "pumaguard.web_routes.wifi._restart_wpa_supplicant",
        return_value=(True, ""),
    ):
        response = client.post("/api/wifi/forget", json={"ssid": "NetA"})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
