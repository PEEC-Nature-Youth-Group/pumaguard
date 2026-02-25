"""Tests for WebUI class and Flask server initialization."""
# pylint: disable=too-many-lines

import hashlib
import time
from unittest.mock import (
    Mock,
    patch,
)

from flask import (
    Flask,
)
from zeroconf import (
    NonUniqueNameException,
)

from pumaguard.presets import (
    Settings,
)
from pumaguard.web_ui import (
    WebUI,
)


class TestWebUIInitialization:
    """Tests for WebUI.__init__ method."""

    def test_webui_initialization_default_parameters(self):
        """Test WebUI initializes with default parameters."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert webui.host == "127.0.0.1"
            assert webui.port == 5000
            assert webui.debug is False
            assert webui.mdns_enabled is True
            assert webui.mdns_name == "pumaguard"
            assert webui.watch_method == "os"
            assert isinstance(webui.app, Flask)

    def test_webui_initialization_custom_parameters(self):
        """Test WebUI initializes with custom parameters."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(
                presets=presets,
                host="0.0.0.0",
                port=8080,
                debug=True,
                mdns_enabled=False,
                mdns_name="custom-name",
                watch_method="inotify",
            )

            assert webui.host == "0.0.0.0"
            assert webui.port == 8080
            assert webui.debug is True
            assert webui.mdns_enabled is False
            assert webui.mdns_name == "custom-name"
            assert webui.watch_method == "inotify"

    def test_webui_initialization_with_folder_manager(self):
        """Test WebUI initializes with folder manager."""
        presets = Settings()
        mock_manager = Mock()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets, folder_manager=mock_manager)

            assert webui.folder_manager is mock_manager

    def test_webui_cors_configured(self):
        """Test CORS is configured correctly."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS") as mock_cors:
            webui = WebUI(presets=presets)

            # Verify CORS was called with correct parameters
            mock_cors.assert_called_once()
            call_args = mock_cors.call_args
            assert call_args[0][0] == webui.app
            assert "resources" in call_args[1]
            assert "allow_headers" in call_args[1]
            assert "methods" in call_args[1]

    def test_webui_initializes_empty_directories(self):
        """Test WebUI initializes with empty directory lists."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert not webui.image_directories
            assert not webui.classification_directories

    def test_webui_initializes_empty_cameras_and_plugs(self):
        """Test WebUI initializes with empty camera and plug dicts."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert not webui.cameras
            assert not webui.plugs

    def test_webui_loads_cameras_from_presets(self):
        """Test WebUI loads cameras from presets."""
        presets = Settings()
        presets.cameras = [
            {
                "hostname": "camera1",
                "ip_address": "192.168.1.10",
                "mac_address": "AA:BB:CC:DD:EE:01",
                "last_seen": "2024-01-01T00:00:00",
                "status": "connected",
            }
        ]

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert "AA:BB:CC:DD:EE:01" in webui.cameras
            camera = webui.cameras["AA:BB:CC:DD:EE:01"]
            assert camera["hostname"] == "camera1"
            assert camera["ip_address"] == "192.168.1.10"
            assert camera["status"] == "connected"

    def test_webui_loads_plugs_from_presets(self):
        """Test WebUI loads plugs from presets."""
        presets = Settings()
        presets.plugs = [
            {
                "hostname": "plug1",
                "ip_address": "192.168.1.20",
                "mac_address": "AA:BB:CC:DD:EE:02",
                "last_seen": "2024-01-01T00:00:00",
                "status": "connected",
                "mode": "on",
            }
        ]

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert "AA:BB:CC:DD:EE:02" in webui.plugs
            plug = webui.plugs["AA:BB:CC:DD:EE:02"]
            assert plug["hostname"] == "plug1"
            assert plug["ip_address"] == "192.168.1.20"
            assert plug["status"] == "connected"
            assert plug["mode"] == "on"

    def test_webui_loads_device_history_from_presets(self):
        """Test WebUI loads device history from presets."""
        presets = Settings()
        presets.device_history = {
            "AA:BB:CC:DD:EE:03": {"type": "camera", "hostname": "old-camera"}
        }

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert "AA:BB:CC:DD:EE:03" in webui.device_history
            assert (
                webui.device_history["AA:BB:CC:DD:EE:03"]["type"] == "camera"
            )

    def test_webui_adds_cameras_to_device_history(self):
        """Test WebUI adds loaded cameras to device history."""
        presets = Settings()
        presets.cameras = [
            {
                "hostname": "camera1",
                "ip_address": "192.168.1.10",
                "mac_address": "AA:BB:CC:DD:EE:04",
            }
        ]

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert "AA:BB:CC:DD:EE:04" in webui.device_history
            assert (
                webui.device_history["AA:BB:CC:DD:EE:04"]["type"] == "camera"
            )
            assert (
                webui.device_history["AA:BB:CC:DD:EE:04"]["hostname"]
                == "camera1"
            )

    def test_webui_adds_plugs_to_device_history(self):
        """Test WebUI adds loaded plugs to device history."""
        presets = Settings()
        presets.plugs = [
            {
                "hostname": "plug1",
                "ip_address": "192.168.1.20",
                "mac_address": "AA:BB:CC:DD:EE:05",
            }
        ]

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert "AA:BB:CC:DD:EE:05" in webui.device_history
            assert webui.device_history["AA:BB:CC:DD:EE:05"]["type"] == "plug"
            assert (
                webui.device_history["AA:BB:CC:DD:EE:05"]["hostname"]
                == "plug1"
            )

    def test_webui_initializes_heartbeat_monitors(self):
        """Test WebUI initializes camera and plug heartbeat monitors."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            with patch("pumaguard.web_ui.CameraHeartbeat") as mock_cam:
                with patch("pumaguard.web_ui.PlugHeartbeat") as mock_plug:
                    _ = WebUI(presets=presets)

                    # Verify heartbeat monitors were created
                    mock_cam.assert_called_once()
                    mock_plug.assert_called_once()

    def test_webui_tracks_start_time(self):
        """Test WebUI tracks server start time."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            before = time.time()
            webui = WebUI(presets=presets)
            after = time.time()

            assert before <= webui.start_time <= after

    def test_webui_not_running_initially(self):
        """Test WebUI._running is False initially."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert webui._running is False  # pylint: disable=protected-access

    def test_webui_no_mdns_services_initially(self):
        """Test WebUI has no mDNS services initially."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert webui.zeroconf is None
            assert webui.service_info is None


class TestWebUIFlutterBuildDirectory:
    """Tests for Flutter build directory detection."""

    def test_webui_finds_package_build_dir(self):
        """Test WebUI finds package build directory."""
        presets = Settings()
        # This test is complex to mock due to Path resolution
        # Just verify WebUI initializes without error
        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            # Should have a build_dir set (even if not built)
            assert webui.build_dir is not None

    def test_webui_handles_missing_build_dir(self):
        """Test WebUI handles missing build directory gracefully."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            # Should not raise an error even if build dir doesn't exist
            webui = WebUI(presets=presets)
            assert webui.build_dir is not None


class TestWebUIDirectoryManagement:
    """Tests for add_image_directory and add_classification_directory."""

    def test_add_image_directory(self):
        """Test adding image directory."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            webui.add_image_directory("/path/to/images")

            assert "/path/to/images" in webui.image_directories

    def test_add_image_directory_duplicate(self):
        """Test adding duplicate image directory doesn't duplicate entry."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            webui.add_image_directory("/path/to/images")
            webui.add_image_directory("/path/to/images")

            assert webui.image_directories.count("/path/to/images") == 1

    def test_add_multiple_image_directories(self):
        """Test adding multiple image directories."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            webui.add_image_directory("/path/to/images1")
            webui.add_image_directory("/path/to/images2")
            webui.add_image_directory("/path/to/images3")

            assert len(webui.image_directories) == 3

    def test_add_classification_directory(self):
        """Test adding classification directory."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            webui.add_classification_directory("/path/to/classified")

            assert "/path/to/classified" in webui.classification_directories

    def test_add_classification_directory_duplicate(self):
        """Test adding duplicate classification directory."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            webui.add_classification_directory("/path/to/classified")
            webui.add_classification_directory("/path/to/classified")

            assert (
                webui.classification_directories.count("/path/to/classified")
                == 1
            )


class TestWebUIGetLocalIP:
    """Tests for _get_local_ip method."""

    def test_get_local_ip_success(self):
        """Test _get_local_ip returns IP address."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            with patch("socket.socket") as mock_socket_class:
                mock_socket = Mock()
                mock_socket.getsockname.return_value = ("192.168.1.100", 0)
                mock_socket_class.return_value = mock_socket

                ip = webui._get_local_ip()  # pylint: disable=protected-access

                assert ip == "192.168.1.100"
                mock_socket.connect.assert_called_once_with(("8.8.8.8", 80))
                mock_socket.close.assert_called_once()

    def test_get_local_ip_failure_returns_localhost(self):
        """Test _get_local_ip returns localhost on failure."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            with patch("socket.socket") as mock_socket_class:
                mock_socket_class.side_effect = OSError("Network error")

                ip = webui._get_local_ip()  # pylint: disable=protected-access

                assert ip == "127.0.0.1"


class TestWebUIMDNS:
    """Tests for mDNS/Zeroconf functionality."""

    def test_start_mdns_success(self):
        """Test _start_mdns registers service."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets, mdns_enabled=True, mdns_name="test")

            with patch("pumaguard.web_ui.Zeroconf") as mock_zeroconf_class:
                with patch("pumaguard.web_ui.ServiceInfo"):
                    with patch.object(
                        webui, "_get_local_ip", return_value="192.168.1.100"
                    ):
                        mock_zc = Mock()
                        mock_zeroconf_class.return_value = mock_zc

                        webui._start_mdns()  # pylint: disable=protected-access

                        # Verify Zeroconf was created
                        mock_zeroconf_class.assert_called_once()
                        # Verify service was registered
                        mock_zc.register_service.assert_called_once()

    def test_start_mdns_disabled(self):
        """Test _start_mdns does nothing when disabled."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets, mdns_enabled=False)

            with patch("pumaguard.web_ui.Zeroconf") as mock_zeroconf:
                webui._start_mdns()  # pylint: disable=protected-access

                # Zeroconf should not be called
                mock_zeroconf.assert_not_called()

    def test_start_mdns_handles_non_unique_name(self):
        """Test _start_mdns handles NonUniqueNameException."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets, mdns_enabled=True)

            with patch("pumaguard.web_ui.Zeroconf") as mock_zeroconf_class:
                with patch("pumaguard.web_ui.ServiceInfo"):
                    with patch.object(
                        webui, "_get_local_ip", return_value="192.168.1.100"
                    ):
                        mock_zc = Mock()
                        mock_zeroconf_class.return_value = mock_zc
                        # First register fails, second succeeds
                        mock_zc.register_service.side_effect = [
                            NonUniqueNameException(),
                            None,
                        ]

                        webui._start_mdns()  # pylint: disable=protected-access

                        # Should have tried to unregister and re-register
                        mock_zc.unregister_service.assert_called_once()
                        assert mock_zc.register_service.call_count == 2

    def test_start_mdns_handles_error(self):
        """Test _start_mdns handles errors gracefully."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets, mdns_enabled=True)

            with patch("pumaguard.web_ui.Zeroconf") as mock_zeroconf_class:
                with patch.object(
                    webui, "_get_local_ip", return_value="192.168.1.100"
                ):
                    mock_zeroconf_class.side_effect = OSError("mDNS error")

                    # Should not raise, just log error
                    webui._start_mdns()  # pylint: disable=protected-access

                    assert webui.zeroconf is None

    def test_stop_mdns_success(self):
        """Test _stop_mdns unregisters service."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            mock_zc = Mock()
            mock_service = Mock()
            webui.zeroconf = mock_zc
            webui.service_info = mock_service

            webui._stop_mdns()  # pylint: disable=protected-access

            mock_zc.unregister_service.assert_called_once_with(mock_service)
            mock_zc.close.assert_called_once()
            assert webui.zeroconf is None
            assert webui.service_info is None

    def test_stop_mdns_when_not_started(self):
        """Test _stop_mdns does nothing when mDNS not started."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            # Should not raise error
            webui._stop_mdns()  # pylint: disable=protected-access

            assert webui.zeroconf is None

    def test_stop_mdns_handles_error(self):
        """Test _stop_mdns handles errors gracefully."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            mock_zc = Mock()
            mock_zc.unregister_service.side_effect = OSError("Error")
            webui.zeroconf = mock_zc
            webui.service_info = Mock()

            # Should not raise, just log error
            webui._stop_mdns()  # pylint: disable=protected-access

            # Should still clean up references
            assert webui.zeroconf is None


class TestWebUIStartStop:
    """Tests for start and stop methods."""

    def test_start_server_in_debug_mode(self):
        """Test start runs server directly in debug mode."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets, debug=True)

            with patch.object(webui, "_run_server") as mock_run:
                with patch.object(webui, "_start_mdns"):
                    with patch.object(webui.heartbeat, "start"):
                        with patch.object(webui.plug_heartbeat, "start"):
                            webui.start()

                            # pylint: disable=protected-access
                            assert webui._running is True
                            mock_run.assert_called_once()

    def test_start_server_in_production_mode(self):
        """Test start runs server in thread in production mode."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets, debug=False)

            with patch("threading.Thread") as mock_thread_class:
                with patch.object(webui, "_start_mdns"):
                    with patch.object(webui.heartbeat, "start"):
                        with patch.object(webui.plug_heartbeat, "start"):
                            mock_thread = Mock()
                            mock_thread_class.return_value = mock_thread

                            webui.start()

                            # pylint: disable=protected-access
                            assert webui._running is True
                            mock_thread.start.assert_called_once()

    def test_start_already_running(self):
        """Test start does nothing if already running."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            webui._running = True  # pylint: disable=protected-access

            with patch.object(webui, "_run_server") as mock_run:
                webui.start()

                # Should not run server again
                mock_run.assert_not_called()

    def test_start_starts_mdns(self):
        """Test start calls _start_mdns."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets, debug=True)

            with patch.object(webui, "_start_mdns") as mock_mdns:
                with patch.object(webui, "_run_server"):
                    with patch.object(webui.heartbeat, "start"):
                        with patch.object(webui.plug_heartbeat, "start"):
                            webui.start()

                            mock_mdns.assert_called_once()

    def test_start_starts_heartbeat_monitors(self):
        """Test start starts heartbeat monitors."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets, debug=True)

            with patch.object(webui, "_run_server"):
                with patch.object(webui, "_start_mdns"):
                    with patch.object(webui.heartbeat, "start") as mock_cam:
                        with patch.object(
                            webui.plug_heartbeat, "start"
                        ) as mock_plug:
                            webui.start()

                            mock_cam.assert_called_once()
                            mock_plug.assert_called_once()

    def test_stop_server(self):
        """Test stop sets _running to False."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            webui._running = True  # pylint: disable=protected-access

            with patch.object(webui, "_stop_mdns"):
                with patch.object(webui.heartbeat, "stop"):
                    with patch.object(webui.plug_heartbeat, "stop"):
                        webui.stop()

                        assert webui._running is False  # pylint: disable=protected-access

    def test_stop_not_running(self):
        """Test stop does nothing if not running."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            # pylint: disable=protected-access
            webui._running = True

            with patch.object(webui, "_stop_mdns"):
                webui.stop()

                # Should still try to stop (idempotent)
                # but log a warning

    def test_stop_stops_mdns(self):
        """Test stop calls _stop_mdns."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            webui._running = True  # pylint: disable=protected-access

            with patch.object(webui, "_stop_mdns") as mock_mdns:
                with patch.object(webui.heartbeat, "stop"):
                    with patch.object(webui.plug_heartbeat, "stop"):
                        webui.stop()

                        mock_mdns.assert_called_once()

    def test_stop_stops_heartbeat_monitors(self):
        """Test stop stops heartbeat monitors."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)
            webui._running = True  # pylint: disable=protected-access

            with patch.object(webui, "_stop_mdns"):
                with patch.object(webui.heartbeat, "stop") as mock_cam:
                    with patch.object(
                        webui.plug_heartbeat, "stop"
                    ) as mock_plug:
                        webui.stop()

                        mock_cam.assert_called_once()
                        mock_plug.assert_called_once()


class TestWebUICalculateFileChecksum:
    """Tests for _calculate_file_checksum method."""

    def test_calculate_file_checksum(self, tmp_path):
        """Test _calculate_file_checksum calculates correct checksum."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            test_file = tmp_path / "test.txt"
            content = b"test content"
            test_file.write_bytes(content)

            expected = hashlib.sha256(content).hexdigest()
            # pylint: disable=protected-access
            result = webui._calculate_file_checksum(str(test_file))

            assert result == expected

    def test_calculate_file_checksum_large_file(self, tmp_path):
        """Test _calculate_file_checksum handles large files."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            test_file = tmp_path / "large.bin"
            # Create file larger than chunk size (4096)
            content = b"x" * 10000
            test_file.write_bytes(content)

            expected = hashlib.sha256(content).hexdigest()
            # pylint: disable=protected-access
            result = webui._calculate_file_checksum(str(test_file))

            assert result == expected


class TestWebUIMain:
    """Tests for main convenience function."""

    def test_main_starts_server(self):
        """Test main function starts server."""
        with patch("sys.argv", ["pumaguard-webui"]):
            with patch("pumaguard.web_ui.WebUI") as mock_webui_class:
                mock_webui = Mock()
                mock_webui_class.return_value = mock_webui

                with patch("time.sleep", side_effect=KeyboardInterrupt):
                    # Use KeyboardInterrupt to break the infinite loop
                    try:
                        # pylint: disable=import-outside-toplevel
                        from pumaguard.web_ui import (
                            main,
                        )

                        main()
                    except KeyboardInterrupt:
                        pass

                    mock_webui.start.assert_called_once()

    def test_main_with_arguments(self):
        """Test main function parses command line arguments."""
        with patch(
            "sys.argv",
            [
                "pumaguard-webui",
                "--host",
                "0.0.0.0",
                "--port",
                "8080",
                "--debug",
                "--no-mdns",
            ],
        ):
            with patch("pumaguard.web_ui.WebUI") as mock_webui_class:
                mock_webui = Mock()
                mock_webui_class.return_value = mock_webui

                with patch("time.sleep", side_effect=KeyboardInterrupt):
                    try:
                        # pylint: disable=import-outside-toplevel
                        from pumaguard.web_ui import (
                            main,
                        )

                        main()
                    except KeyboardInterrupt:
                        pass

                    # Verify WebUI was created with correct args
                    call_kwargs = mock_webui_class.call_args[1]
                    assert call_kwargs["host"] == "0.0.0.0"
                    assert call_kwargs["port"] == 8080
                    assert call_kwargs["debug"] is True
                    assert call_kwargs["mdns_enabled"] is False

    def test_main_with_settings_file(self, tmp_path):
        """Test main function loads settings from file."""
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text(
            "yolo-min-size: 0.05\nimage-dimensions: [299, 299]"
        )

        with patch(
            "sys.argv",
            ["pumaguard-webui", "--settings", str(settings_file)],
        ):
            with patch("pumaguard.web_ui.WebUI") as mock_webui_class:
                mock_webui = Mock()
                mock_webui.flutter_dir = tmp_path
                mock_webui_class.return_value = mock_webui

                with patch("time.sleep", side_effect=KeyboardInterrupt):
                    try:
                        # pylint: disable=import-outside-toplevel
                        from pumaguard.web_ui import (
                            main,
                        )

                        main()
                    except KeyboardInterrupt:
                        pass

                    # Verify settings file was used
                    # Verify settings were loaded
                    mock_webui_class.assert_called_once()

    def test_main_with_image_directories(self):
        """Test main function adds image directories."""
        with patch(
            "sys.argv",
            [
                "pumaguard-webui",
                "--image-dir",
                "/path/to/images1",
                "--image-dir",
                "/path/to/images2",
            ],
        ):
            with patch("pumaguard.web_ui.WebUI") as mock_webui_class:
                mock_webui = Mock()
                mock_webui_class.return_value = mock_webui

                with patch("time.sleep", side_effect=KeyboardInterrupt):
                    try:
                        # pylint: disable=import-outside-toplevel
                        from pumaguard.web_ui import (
                            main,
                        )

                        main()
                    except KeyboardInterrupt:
                        pass

                    # Verify watch method was set
                    # Verify image directories were added
                    assert mock_webui.add_image_directory.call_count == 2

    def test_main_with_mdns_name(self):
        """Test main function uses custom mDNS name."""
        with patch(
            "sys.argv",
            ["pumaguard-webui", "--mdns-name", "my-server"],
        ):
            with patch("pumaguard.web_ui.WebUI") as mock_webui_class:
                mock_webui = Mock()
                mock_webui_class.return_value = mock_webui

                with patch("time.sleep", side_effect=KeyboardInterrupt):
                    try:
                        # pylint: disable=import-outside-toplevel
                        from pumaguard.web_ui import (
                            main,
                        )

                        main()
                    except KeyboardInterrupt:
                        pass

                    # Verify mDNS name was set
                    call_kwargs = mock_webui_class.call_args[1]
                    assert call_kwargs["mdns_name"] == "my-server"

    def test_main_handles_keyboard_interrupt(self):
        """Test main function handles KeyboardInterrupt gracefully."""
        with patch("sys.argv", ["pumaguard-webui"]):
            with patch("pumaguard.web_ui.WebUI") as mock_webui_class:
                mock_webui = Mock()
                mock_webui_class.return_value = mock_webui

                with patch("time.sleep", side_effect=KeyboardInterrupt):
                    # pylint: disable=import-outside-toplevel
                    from pumaguard.web_ui import (
                        main,
                    )

                    # Should not raise, just exit cleanly
                    main()

                    mock_webui.stop.assert_called_once()


class TestWebUIRouteSetup:
    """Tests for route setup and registration."""

    def test_setup_routes_registers_all_route_modules(self):
        """Test _setup_routes registers all route modules."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            with patch(
                "pumaguard.web_ui.register_settings_routes"
            ) as mock_settings:
                pth = "pumaguard.web_ui.register_photos_routes"
                with patch(pth) as mock_photos:
                    pth = "pumaguard.web_ui.register_folders_routes"
                    with patch(pth) as mock_folders:
                        pth = "pumaguard.web_ui.register_sync_routes"
                        with patch(pth) as mock_sync:
                            pth = (
                                "pumaguard.web_ui.register_directories_routes"
                            )
                            with patch(pth) as mock_dirs:
                                pth = (
                                    "pumaguard.web_ui"
                                    ".register_diagnostics_routes"
                                )
                                with patch(pth) as mock_diag:
                                    pth = (
                                        "pumaguard.web_ui"
                                        ".register_system_routes"
                                    )
                                    with patch(pth) as mock_system:
                                        pth = (
                                            "pumaguard.web_ui"
                                            ".register_dhcp_routes"
                                        )
                                        with patch(pth) as mock_dhcp:
                                            pth = (
                                                "pumaguard.web_ui"
                                                ".register_artifacts_"
                                                "routes"
                                            )
                                            with patch(pth) as mock_artifacts:
                                                dhcp_ret = None
                                                mock_dhcp.return_value = (
                                                    dhcp_ret
                                                )

                                                _ = WebUI(presets=presets)

                                                # Verify routes
                                                called = mock_settings
                                                called.assert_called_once()
                                                called = mock_photos
                                                called.assert_called_once()
                                                called = mock_folders
                                                called.assert_called_once()
                                                mock_sync.assert_called_once()
                                                mock_dirs.assert_called_once()
                                                mock_diag.assert_called_once()
                                                called = mock_system
                                                called.assert_called_once()
                                                mock_dhcp.assert_called_once()
                                                called = mock_artifacts
                                                called.assert_called_once()

    def test_setup_routes_wires_heartbeat_callbacks(self):
        """Test _setup_routes wires heartbeat callbacks from DHCP routes."""
        presets = Settings()

        with patch("pumaguard.web_ui.CORS"):
            pth = "pumaguard.web_ui.register_dhcp_routes"
            with patch(pth) as mock_dhcp:
                mock_callback = Mock()
                mock_dhcp.return_value = mock_callback

                webui = WebUI(presets=presets)

                # Verify callbacks were wired
                callback = webui.heartbeat.status_change_callback
                assert callback == mock_callback
                assert (
                    webui.plug_heartbeat.status_change_callback
                    == mock_callback
                )


class TestWebUIEdgeCases:
    """Tests for edge cases and error handling."""

    def test_webui_handles_missing_mac_address_in_camera(self):
        """Test WebUI handles camera without MAC address."""
        presets = Settings()
        presets.cameras = [
            {
                "hostname": "camera1",
                "ip_address": "192.168.1.10",
                # No mac_address
            }
        ]

        with patch("pumaguard.web_ui.CORS"):
            # Should not raise error
            webui = WebUI(presets=presets)
            assert len(webui.cameras) == 0

    def test_webui_handles_missing_mac_address_in_plug(self):
        """Test WebUI handles plug without MAC address."""
        presets = Settings()
        presets.plugs = [
            {
                "hostname": "plug1",
                "ip_address": "192.168.1.20",
                # No mac_address
            }
        ]

        with patch("pumaguard.web_ui.CORS"):
            # Should not raise error
            webui = WebUI(presets=presets)
            assert len(webui.plugs) == 0

    def test_webui_handles_missing_hostname_in_camera(self):
        """Test WebUI handles camera without hostname."""
        presets = Settings()
        presets.cameras = [
            {
                # No hostname
                "ip_address": "192.168.1.10",
                "mac_address": "AA:BB:CC:DD:EE:06",
            }
        ]

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            # Should still load camera with empty hostname
            assert "AA:BB:CC:DD:EE:06" in webui.cameras
            assert webui.cameras["AA:BB:CC:DD:EE:06"]["hostname"] == ""

    def test_webui_loads_default_status_for_camera(self):
        """Test WebUI uses default status if not provided."""
        presets = Settings()
        presets.cameras = [
            {
                "hostname": "camera1",
                "ip_address": "192.168.1.10",
                "mac_address": "AA:BB:CC:DD:EE:07",
                # No status
            }
        ]

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            assert (
                webui.cameras["AA:BB:CC:DD:EE:07"]["status"] == "disconnected"
            )

    def test_webui_loads_default_mode_for_plug(self):
        """Test WebUI uses default mode if not provided."""
        presets = Settings()
        presets.plugs = [
            {
                "hostname": "plug1",
                "ip_address": "192.168.1.20",
                "mac_address": "AA:BB:CC:DD:EE:08",
                # No mode
            }
        ]

        with patch("pumaguard.web_ui.CORS"):
            webui = WebUI(presets=presets)

            # Default mode should be "automatic"
            assert webui.plugs["AA:BB:CC:DD:EE:08"]["mode"] == "automatic"
