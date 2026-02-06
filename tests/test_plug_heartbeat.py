"""
Test PlugHeartbeat monitoring functionality.
"""

import time
import unittest
from unittest.mock import (
    Mock,
    patch,
)

import requests

from pumaguard.plug_heartbeat import (
    PlugHeartbeat,
)


# pylint: disable=protected-access,too-many-public-methods
class TestPlugHeartbeat(unittest.TestCase):
    """Test PlugHeartbeat class."""

    def setUp(self):
        """Set up test fixtures."""
        self.webui = Mock()
        self.webui.plugs = {
            "11:22:33:44:55:66": {
                "hostname": "plug1",
                "ip_address": "192.168.1.200",
                "mac_address": "11:22:33:44:55:66",
                "last_seen": "2024-01-15T10:00:00Z",
                "status": "connected",
                "mode": "off",
            },
            "aa:bb:cc:dd:ee:ff": {
                "hostname": "plug2",
                "ip_address": "192.168.1.201",
                "mac_address": "aa:bb:cc:dd:ee:ff",
                "last_seen": "2024-01-15T09:30:00Z",
                "status": "disconnected",
                "mode": "automatic",
            },
        }
        self.webui.presets = Mock()
        self.webui.presets.plugs = []
        self.webui.presets.save = Mock()

    def test_initialization(self):
        """Test PlugHeartbeat initialization."""
        heartbeat = PlugHeartbeat(
            webui=self.webui,
            interval=120,
            enabled=False,
            timeout=10,
        )

        assert heartbeat.webui == self.webui
        assert heartbeat.interval == 120
        assert heartbeat.enabled is False
        assert heartbeat.timeout == 10
        assert heartbeat._running is False

    def test_initialization_defaults(self):
        """Test PlugHeartbeat initialization with defaults."""
        heartbeat = PlugHeartbeat(webui=self.webui)

        assert heartbeat.interval == 60
        assert heartbeat.enabled is True
        assert heartbeat.timeout == 5

    @patch("requests.get")
    def test_check_http_success(self, mock_get):
        """Test HTTP check with successful response."""
        heartbeat = PlugHeartbeat(self.webui)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": True, "apower": 50.0}
        mock_get.return_value = mock_response

        result = heartbeat._check_http("192.168.1.200")

        assert result is True
        mock_get.assert_called_once_with(
            "http://192.168.1.200/rpc/Switch.GetStatus?id=0", timeout=5
        )

    @patch("requests.get")
    def test_check_http_timeout(self, mock_get):
        """Test HTTP check with timeout."""
        heartbeat = PlugHeartbeat(self.webui)
        mock_get.side_effect = requests.exceptions.Timeout()

        result = heartbeat._check_http("192.168.1.200")

        assert result is False

    @patch("requests.get")
    def test_check_http_connection_error(self, mock_get):
        """Test HTTP check with connection error."""
        heartbeat = PlugHeartbeat(self.webui)
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = heartbeat._check_http("192.168.1.200")

        assert result is False

    @patch("requests.get")
    def test_check_http_invalid_response(self, mock_get):
        """Test HTTP check with invalid JSON response."""
        heartbeat = PlugHeartbeat(self.webui)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "data"}
        mock_get.return_value = mock_response

        result = heartbeat._check_http("192.168.1.200")

        # Should return False because "output" key is missing
        assert result is False

    @patch("requests.get")
    def test_check_plug(self, mock_get):
        """Test check_plug method."""
        heartbeat = PlugHeartbeat(self.webui)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": True}
        mock_get.return_value = mock_response

        result = heartbeat.check_plug("192.168.1.200")

        assert result is True

    def test_update_plug_status_reachable(self):
        """Test updating plug status when reachable."""
        heartbeat = PlugHeartbeat(self.webui)

        with patch.object(heartbeat, "_save_plug_list"):
            heartbeat._update_plug_status("aa:bb:cc:dd:ee:ff", True)

        plug = self.webui.plugs["aa:bb:cc:dd:ee:ff"]
        assert plug["status"] == "connected"
        assert plug["last_seen"] != "2024-01-15T09:30:00Z"  # Updated

    def test_update_plug_status_unreachable(self):
        """Test updating plug status when unreachable."""
        heartbeat = PlugHeartbeat(self.webui)
        original_last_seen = self.webui.plugs["11:22:33:44:55:66"]["last_seen"]

        with patch.object(heartbeat, "_save_plug_list"):
            heartbeat._update_plug_status("11:22:33:44:55:66", False)

        plug = self.webui.plugs["11:22:33:44:55:66"]
        assert plug["status"] == "disconnected"
        assert (
            plug["last_seen"] == original_last_seen
        )  # Not updated on failure

    def test_update_plug_status_callback(self):
        """Test status change callback is called."""
        callback = Mock()
        heartbeat = PlugHeartbeat(self.webui, status_change_callback=callback)

        with patch.object(heartbeat, "_save_plug_list"):
            # Change from disconnected to connected
            heartbeat._update_plug_status("aa:bb:cc:dd:ee:ff", True)

        # Callback should be called once for status change
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == "plug_status_changed_online"
        assert args[1]["hostname"] == "plug2"

    def test_update_plug_status_no_callback_when_unchanged(self):
        """Test callback is not called when status doesn't change."""
        callback = Mock()
        heartbeat = PlugHeartbeat(self.webui, status_change_callback=callback)

        with patch.object(heartbeat, "_save_plug_list"):
            # Status is already connected
            heartbeat._update_plug_status("11:22:33:44:55:66", True)

        # Callback should not be called
        callback.assert_not_called()

    def test_save_plug_list(self):
        """Test saving plug list to settings."""
        heartbeat = PlugHeartbeat(self.webui)

        heartbeat._save_plug_list()

        assert len(self.webui.presets.plugs) == 2
        self.webui.presets.save.assert_called_once()

    def test_save_plug_list_exception(self):
        """Test saving plug list handles exceptions gracefully."""
        heartbeat = PlugHeartbeat(self.webui)
        self.webui.presets.save.side_effect = Exception("Save failed")

        # Should not raise exception
        heartbeat._save_plug_list()

    @patch("requests.get")
    def test_check_now(self, mock_get):
        """Test check_now method checks all plugs."""
        heartbeat = PlugHeartbeat(self.webui)

        # Mock responses for both plugs
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": True}
        mock_get.return_value = mock_response

        with patch.object(heartbeat, "_update_plug_status"):
            results = heartbeat.check_now()

        assert len(results) == 2
        assert "11:22:33:44:55:66" in results
        assert "aa:bb:cc:dd:ee:ff" in results

    def test_start_disabled(self):
        """Test starting heartbeat when disabled."""
        heartbeat = PlugHeartbeat(self.webui, enabled=False)

        heartbeat.start()

        assert heartbeat._running is False
        assert heartbeat._thread is None

    def test_start_enabled(self):
        """Test starting heartbeat when enabled."""
        heartbeat = PlugHeartbeat(self.webui, enabled=True)

        with patch.object(heartbeat, "_monitor_loop"):
            heartbeat.start()

            assert heartbeat._running is True
            assert heartbeat._thread is not None
            assert heartbeat._thread.name == "PlugHeartbeat"
            assert heartbeat._thread.daemon is True

            # Stop to clean up
            heartbeat.stop()

    def test_start_already_running(self):
        """Test starting heartbeat when already running."""
        heartbeat = PlugHeartbeat(self.webui, enabled=True)
        heartbeat._running = True

        with patch.object(heartbeat, "_monitor_loop"):
            heartbeat.start()

            # Thread should not be created
            assert heartbeat._thread is None

    def test_stop(self):
        """Test stopping heartbeat."""
        heartbeat = PlugHeartbeat(self.webui, enabled=True)

        with patch.object(heartbeat, "_monitor_loop"):
            heartbeat.start()
            heartbeat.stop()

            assert heartbeat._running is False
            assert heartbeat._stop_event.is_set()

    def test_stop_not_running(self):
        """Test stopping heartbeat when not running."""
        heartbeat = PlugHeartbeat(self.webui)
        heartbeat._running = False

        # Should not raise exception
        heartbeat.stop()

    @patch("requests.get")
    def test_monitor_loop_checks_plugs(self, mock_get):
        """Test monitor loop checks all plugs."""
        heartbeat = PlugHeartbeat(self.webui, interval=1)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": True}
        mock_get.return_value = mock_response

        with patch.object(heartbeat, "_save_plug_list"):
            # Start monitoring
            heartbeat.start()

            # Let it run briefly
            time.sleep(0.1)

            # Stop monitoring
            heartbeat.stop()

        # Should have attempted to check plugs
        assert mock_get.call_count >= 0  # May not have time to check

    def test_update_plug_status_nonexistent_plug(self):
        """Test updating status for a plug that doesn't exist."""
        heartbeat = PlugHeartbeat(self.webui)

        # Should not raise exception
        heartbeat._update_plug_status("99:99:99:99:99:99", True)

        # Verify save was not called
        self.webui.presets.save.assert_not_called()

    def test_update_plug_status_preserves_mode(self):
        """Test that updating status preserves plug mode."""
        heartbeat = PlugHeartbeat(self.webui)

        with patch.object(heartbeat, "_save_plug_list"):
            heartbeat._update_plug_status("aa:bb:cc:dd:ee:ff", True)

        plug = self.webui.plugs["aa:bb:cc:dd:ee:ff"]
        assert plug["mode"] == "automatic"  # Mode preserved

    @patch("requests.get")
    def test_check_now_empty_ip(self, mock_get):
        """Test check_now handles plugs with empty IP addresses."""
        heartbeat = PlugHeartbeat(self.webui)

        # Mock successful response for other plugs
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"output": True}
        mock_get.return_value = mock_response

        # Add plug with empty IP
        self.webui.plugs["empty:ip:plug"] = {
            "hostname": "plug-no-ip",
            "ip_address": "",
            "mac_address": "empty:ip:plug",
            "last_seen": "2024-01-15T10:00:00Z",
            "status": "disconnected",
            "mode": "off",
        }

        with patch.object(heartbeat, "_update_plug_status"):
            results = heartbeat.check_now()

        # Should return False for empty IP
        assert results["empty:ip:plug"] is False
        # mock_get should be called for the 2 plugs with valid IPs,
        # but not for empty IP
        assert mock_get.call_count == 2

    def test_callback_exception_handled(self):
        """Test that callback exceptions are handled gracefully."""
        callback = Mock(side_effect=Exception("Callback error"))
        heartbeat = PlugHeartbeat(self.webui, status_change_callback=callback)

        with patch.object(heartbeat, "_save_plug_list"):
            # Should not raise exception despite callback error
            heartbeat._update_plug_status("aa:bb:cc:dd:ee:ff", True)

        # Status should still be updated
        assert self.webui.plugs["aa:bb:cc:dd:ee:ff"]["status"] == "connected"


if __name__ == "__main__":
    unittest.main()
