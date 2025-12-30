"""Tests for camera heartbeat monitoring."""

# pylint: disable=redefined-outer-name
# pylint: disable=protected-access
# Pytest fixtures intentionally redefine names
# Tests need to access protected members for verification

import time
from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

import pytest

from pumaguard.camera_heartbeat import CameraHeartbeat
from pumaguard.presets import Preset
from pumaguard.web_ui import WebUI


@pytest.fixture
def mock_webui():
    """Create a mock WebUI instance with test cameras."""
    presets = MagicMock(spec=Preset)
    presets.cameras = []
    presets.save = MagicMock()
    webui = MagicMock(spec=WebUI)
    webui.presets = presets
    webui.cameras = {
        "aa:bb:cc:dd:ee:01": {
            "hostname": "TestCamera1",
            "ip_address": "192.168.52.101",
            "mac_address": "aa:bb:cc:dd:ee:01",
            "last_seen": "2024-01-15T10:00:00Z",
            "status": "connected",
        },
        "aa:bb:cc:dd:ee:02": {
            "hostname": "TestCamera2",
            "ip_address": "192.168.52.102",
            "mac_address": "aa:bb:cc:dd:ee:02",
            "last_seen": "2024-01-15T10:00:00Z",
            "status": "disconnected",
        },
    }
    return webui


def test_heartbeat_initialization(mock_webui):
    """Test CameraHeartbeat initialization with default values."""
    heartbeat = CameraHeartbeat(mock_webui)

    assert heartbeat.webui == mock_webui
    assert heartbeat.interval == 60
    assert heartbeat.enabled is True
    assert heartbeat.check_method == "tcp"
    assert heartbeat.tcp_port == 80
    assert heartbeat.tcp_timeout == 3
    assert heartbeat.icmp_timeout == 2
    assert heartbeat._running is False


def test_heartbeat_initialization_custom_values(mock_webui):
    """Test CameraHeartbeat initialization with custom values."""
    heartbeat = CameraHeartbeat(
        mock_webui,
        interval=120,
        enabled=False,
        check_method="icmp",
        tcp_port=8080,
        tcp_timeout=5,
        icmp_timeout=3,
    )

    assert heartbeat.interval == 120
    assert heartbeat.enabled is False
    assert heartbeat.check_method == "icmp"
    assert heartbeat.tcp_port == 8080
    assert heartbeat.tcp_timeout == 5
    assert heartbeat.icmp_timeout == 3


def test_heartbeat_invalid_check_method(mock_webui):
    """Test CameraHeartbeat with invalid check method defaults to tcp."""
    heartbeat = CameraHeartbeat(mock_webui, check_method="invalid")

    assert heartbeat.check_method == "tcp"


@patch("subprocess.run")
def test_check_icmp_success(mock_run, mock_webui):
    """Test successful ICMP ping."""
    mock_run.return_value = MagicMock(returncode=0)
    heartbeat = CameraHeartbeat(mock_webui)

    result = heartbeat._check_icmp("192.168.52.101")

    assert result is True
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "ping"
    assert args[1] == "-c"
    assert args[2] == "1"
    assert "192.168.52.101" in args


@patch("subprocess.run")
def test_check_icmp_failure(mock_run, mock_webui):
    """Test failed ICMP ping."""
    mock_run.return_value = MagicMock(returncode=1)
    heartbeat = CameraHeartbeat(mock_webui)

    result = heartbeat._check_icmp("192.168.52.101")

    assert result is False


@patch("subprocess.run")
def test_check_icmp_timeout(mock_run, mock_webui):
    """Test ICMP ping timeout."""
    mock_run.side_effect = TimeoutExpired("ping", 3)
    heartbeat = CameraHeartbeat(mock_webui)

    result = heartbeat._check_icmp("192.168.52.101")

    assert result is False


@patch("socket.socket")
def test_check_tcp_success(mock_socket_class, mock_webui):
    """Test successful TCP connection."""
    mock_socket = MagicMock()
    mock_socket.connect_ex.return_value = 0
    mock_socket_class.return_value = mock_socket

    heartbeat = CameraHeartbeat(mock_webui)
    result = heartbeat._check_tcp("192.168.52.101", 80)

    assert result is True
    mock_socket.connect_ex.assert_called_once_with(("192.168.52.101", 80))
    mock_socket.close.assert_called_once()


@patch("socket.socket")
def test_check_tcp_failure(mock_socket_class, mock_webui):
    """Test failed TCP connection."""
    mock_socket = MagicMock()
    mock_socket.connect_ex.return_value = 1  # Connection refused
    mock_socket_class.return_value = mock_socket

    heartbeat = CameraHeartbeat(mock_webui)
    result = heartbeat._check_tcp("192.168.52.101", 80)

    assert result is False


@patch("socket.socket")
def test_check_tcp_exception(mock_socket_class, mock_webui):
    """Test TCP connection with exception."""
    mock_socket = MagicMock()
    mock_socket.connect_ex.side_effect = OSError("Connection error")
    mock_socket_class.return_value = mock_socket

    heartbeat = CameraHeartbeat(mock_webui)
    result = heartbeat._check_tcp("192.168.52.101", 80)

    assert result is False


def test_check_camera_tcp_method(mock_webui):
    """Test check_camera with TCP method."""
    heartbeat = CameraHeartbeat(mock_webui, check_method="tcp")

    with patch.object(heartbeat, "_check_tcp", return_value=True) as mock_tcp:
        result = heartbeat.check_camera("192.168.52.101")

        assert result is True
        mock_tcp.assert_called_once_with("192.168.52.101", 80)


def test_check_camera_icmp_method(mock_webui):
    """Test check_camera with ICMP method."""
    heartbeat = CameraHeartbeat(mock_webui, check_method="icmp")

    with patch.object(
        heartbeat, "_check_icmp", return_value=True
    ) as mock_icmp:
        result = heartbeat.check_camera("192.168.52.101")

        assert result is True
        mock_icmp.assert_called_once_with("192.168.52.101")


def test_check_camera_both_method_icmp_success(mock_webui):
    """Test check_camera with both method when ICMP succeeds."""
    heartbeat = CameraHeartbeat(mock_webui, check_method="both")

    with patch.object(
        heartbeat, "_check_icmp", return_value=True
    ) as mock_icmp:
        with patch.object(heartbeat, "_check_tcp") as mock_tcp:
            result = heartbeat.check_camera("192.168.52.101")

            assert result is True
            mock_icmp.assert_called_once()
            mock_tcp.assert_not_called()


def test_check_camera_both_method_icmp_fails_tcp_succeeds(mock_webui):
    """Test check_camera with both method when ICMP fails but TCP succeeds."""
    heartbeat = CameraHeartbeat(mock_webui, check_method="both")

    with patch.object(
        heartbeat, "_check_icmp", return_value=False
    ) as mock_icmp:
        with patch.object(
            heartbeat, "_check_tcp", return_value=True
        ) as mock_tcp:
            result = heartbeat.check_camera("192.168.52.101")

            assert result is True
            mock_icmp.assert_called_once()
            mock_tcp.assert_called_once()


def test_check_camera_both_method_both_fail(mock_webui):
    """Test check_camera with both method when both checks fail."""
    heartbeat = CameraHeartbeat(mock_webui, check_method="both")

    with patch.object(
        heartbeat, "_check_icmp", return_value=False
    ) as mock_icmp:
        with patch.object(
            heartbeat, "_check_tcp", return_value=False
        ) as mock_tcp:
            result = heartbeat.check_camera("192.168.52.101")

            assert result is False
            mock_icmp.assert_called_once()
            mock_tcp.assert_called_once()


def test_update_camera_status_reachable(mock_webui):
    """Test updating camera status when reachable."""
    heartbeat = CameraHeartbeat(mock_webui)

    with patch.object(heartbeat, "_save_camera_list"):
        heartbeat._update_camera_status("aa:bb:cc:dd:ee:02", True)

    camera = mock_webui.cameras["aa:bb:cc:dd:ee:02"]
    assert camera["status"] == "connected"
    assert camera["last_seen"] != "2024-01-15T10:00:00Z"  # Updated


def test_update_camera_status_unreachable(mock_webui):
    """Test updating camera status when unreachable."""
    heartbeat = CameraHeartbeat(mock_webui)
    original_last_seen = mock_webui.cameras["aa:bb:cc:dd:ee:01"]["last_seen"]

    with patch.object(heartbeat, "_save_camera_list"):
        heartbeat._update_camera_status("aa:bb:cc:dd:ee:01", False)

    camera = mock_webui.cameras["aa:bb:cc:dd:ee:01"]
    assert camera["status"] == "disconnected"
    assert camera["last_seen"] == original_last_seen  # Not updated on failure


def test_update_camera_status_nonexistent(mock_webui):
    """Test updating status for non-existent camera."""
    heartbeat = CameraHeartbeat(mock_webui)

    with patch.object(heartbeat, "_save_camera_list") as mock_save:
        heartbeat._update_camera_status("aa:bb:cc:dd:ee:99", True)
        # Should not crash or call save
        mock_save.assert_not_called()


def test_save_camera_list(mock_webui):
    """Test saving camera list to settings."""
    heartbeat = CameraHeartbeat(mock_webui)

    heartbeat._save_camera_list()

    assert len(mock_webui.presets.cameras) == 2
    mock_webui.presets.save.assert_called_once()


def test_save_camera_list_exception(mock_webui):
    """Test saving camera list handles exceptions gracefully."""
    heartbeat = CameraHeartbeat(mock_webui)
    mock_webui.presets.save.side_effect = Exception("Save failed")

    # Should not raise exception
    heartbeat._save_camera_list()


def test_check_now(mock_webui):
    """Test manual check_now method."""
    heartbeat = CameraHeartbeat(mock_webui)

    with patch.object(heartbeat, "check_camera") as mock_check:
        mock_check.side_effect = [True, False]

        with patch.object(heartbeat, "_save_camera_list"):
            results = heartbeat.check_now()

    assert len(results) == 2
    assert results["aa:bb:cc:dd:ee:01"] is True
    assert results["aa:bb:cc:dd:ee:02"] is False
    assert mock_check.call_count == 2


def test_check_now_empty_ip(mock_webui):
    """Test check_now with camera that has no IP address."""
    mock_webui.cameras["aa:bb:cc:dd:ee:03"] = {
        "hostname": "NoIP",
        "ip_address": "",
        "mac_address": "aa:bb:cc:dd:ee:03",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "disconnected",
    }

    heartbeat = CameraHeartbeat(mock_webui)

    with patch.object(heartbeat, "check_camera") as mock_check:
        with patch.object(heartbeat, "_save_camera_list"):
            results = heartbeat.check_now()

    assert results["aa:bb:cc:dd:ee:03"] is False
    # Should not call check_camera for empty IP
    assert mock_check.call_count == 2  # Only for cameras with IPs


def test_start_heartbeat_enabled(mock_webui):
    """Test starting heartbeat when enabled."""
    heartbeat = CameraHeartbeat(mock_webui, interval=1)

    heartbeat.start()

    assert heartbeat._running is True
    assert heartbeat._thread is not None
    assert heartbeat._thread.is_alive()

    # Clean up
    heartbeat.stop()


def test_start_heartbeat_disabled(mock_webui):
    """Test starting heartbeat when disabled."""
    heartbeat = CameraHeartbeat(mock_webui, enabled=False)

    heartbeat.start()

    assert heartbeat._running is False
    assert heartbeat._thread is None


def test_start_heartbeat_already_running(mock_webui):
    """Test starting heartbeat when already running."""
    heartbeat = CameraHeartbeat(mock_webui, interval=1)

    heartbeat.start()
    assert heartbeat._running is True

    # Try to start again
    heartbeat.start()

    # Should still be running, but only one thread
    assert heartbeat._running is True

    # Clean up
    heartbeat.stop()


def test_stop_heartbeat(mock_webui):
    """Test stopping heartbeat."""
    heartbeat = CameraHeartbeat(mock_webui, interval=1)

    heartbeat.start()
    assert heartbeat._running is True

    heartbeat.stop()

    assert heartbeat._running is False
    assert heartbeat._stop_event.is_set()


def test_stop_heartbeat_not_running(mock_webui):
    """Test stopping heartbeat when not running."""
    heartbeat = CameraHeartbeat(mock_webui)

    # Should not raise exception
    heartbeat.stop()

    assert heartbeat._running is False


def test_monitor_loop_checks_cameras(mock_webui):
    """Test that monitor loop checks cameras periodically."""
    heartbeat = CameraHeartbeat(mock_webui, interval=0.1)

    with patch.object(heartbeat, "check_camera", return_value=True):
        with patch.object(heartbeat, "_save_camera_list"):
            heartbeat.start()

            # Let it run for a bit
            time.sleep(0.3)

            heartbeat.stop()

    # Should have checked cameras at least once
    assert mock_webui.cameras["aa:bb:cc:dd:ee:01"]["status"] == "connected"


def test_monitor_loop_handles_exceptions(mock_webui):
    """Test that monitor loop handles exceptions gracefully."""
    heartbeat = CameraHeartbeat(mock_webui, interval=0.1)

    with patch.object(
        heartbeat, "check_camera", side_effect=Exception("Test error")
    ):
        heartbeat.start()

        # Let it run for a bit
        time.sleep(0.3)

        # Should still be running despite exceptions
        assert heartbeat._running is True

        heartbeat.stop()


def test_monitor_loop_stops_on_event(mock_webui):
    """Test that monitor loop stops when stop event is set."""
    heartbeat = CameraHeartbeat(mock_webui, interval=10)  # Long interval

    with patch.object(heartbeat, "check_camera", return_value=True):
        with patch.object(heartbeat, "_save_camera_list"):
            heartbeat.start()

            # Stop immediately
            heartbeat.stop()

            # Thread should exit quickly despite long interval
            if heartbeat._thread:
                heartbeat._thread.join(timeout=2)
                assert not heartbeat._thread.is_alive()


def test_monitor_loop_skips_empty_ip(mock_webui):
    """Test that monitor loop skips cameras with empty IP."""
    mock_webui.cameras["aa:bb:cc:dd:ee:03"] = {
        "hostname": "NoIP",
        "ip_address": "",
        "mac_address": "aa:bb:cc:dd:ee:03",
        "last_seen": "2024-01-15T10:00:00Z",
        "status": "disconnected",
    }

    heartbeat = CameraHeartbeat(mock_webui, interval=0.1)

    with patch.object(heartbeat, "check_camera") as mock_check:
        mock_check.return_value = True

        with patch.object(heartbeat, "_save_camera_list"):
            heartbeat.start()
            time.sleep(0.3)
            heartbeat.stop()

    # Should only check cameras with valid IPs (2 cameras)
    assert mock_check.call_count >= 2
    # Should not check the camera with empty IP
    for call in mock_check.call_args_list:
        assert call[0][0] != ""
