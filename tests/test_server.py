"""
Test server.
"""

# pyright: reportImportCycles=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportMissingTypeArgument=false
# pyright: reportPrivateUsage=false
# pyright: reportAttributeAccessIssue=false

import io
import os
import tempfile
import unittest
from unittest.mock import (
    MagicMock,
    call,
    patch,
)

from PIL import (
    Image,
)

from pumaguard.server import (
    FolderManager,
    FolderObserver,
)
from pumaguard.utils import (
    Settings,
)


class TestFolderObserver(unittest.TestCase):
    """
    Unit tests for FolderObserver class
    """

    def setUp(self):
        self.folder = "test_folder"
        self.notebook = 6
        self.presets = Settings()
        self.presets.notebook_number = self.notebook
        self.presets.model_version = "pre-trained"
        self.presets.image_dimensions = (512, 512)
        self.mock_webui = MagicMock()
        self.mock_webui.plugs = {}
        self.observer = FolderObserver(
            self.folder, "inotify", self.presets, self.mock_webui
        )

    @patch("pumaguard.server.acquire_lock")
    @patch("pumaguard.server.cache_model_two_stage")
    @patch("pumaguard.server.subprocess.Popen")
    @patch("pumaguard.server.threading.Thread")
    def test_observe_new_file(
        self, MockThread, MockPopen, mock_cache, mock_lock
    ):  # pylint: disable=invalid-name
        """
        Test observing a new file.
        """
        # Mock the lock
        mock_lock_instance = MagicMock()
        mock_lock.return_value = mock_lock_instance

        mock_process = MagicMock()
        mock_process.stdout = iter(["test_folder/new_file.jpg\n"])
        MockPopen.return_value.__enter__.return_value = mock_process

        with (
            patch.object(
                self.observer,
                "_wait_for_file_stability",
                return_value=True,
            ) as mock_wait,
        ):
            self.observer._observe()  # pylint: disable=protected-access
            mock_wait.assert_called_once_with("test_folder/new_file.jpg")
            mock_cache.assert_called_with(
                yolo_model_filename="yolov8s_101425.pt",
                classifier_model_filename="colorbw_111325.h5",
                print_progress=True,
            )

            # Verify threading.Thread was called with _handle_new_file
            # as target
            MockThread.assert_called_once()
            call_args = MockThread.call_args
            # pylint: disable=protected-access
            self.assertEqual(
                call_args.kwargs["target"], self.observer._handle_new_file
            )
            self.assertEqual(
                call_args.kwargs["args"],
                ("test_folder/new_file.jpg",),
            )

    @patch("pumaguard.server.threading.Thread")
    def test_start(self, MockThread):  # pylint: disable=invalid-name
        """
        Test starting the observer.
        """
        self.observer.start()
        MockThread.assert_called_once_with(
            target=self.observer._observe  # pylint: disable=protected-access
        )
        MockThread.return_value.start.assert_called_once()

    def test_stop(self):
        """
        Test stopping the observer.
        """
        # pylint: disable=protected-access
        self.observer._stop_event = MagicMock()
        self.observer.stop()
        self.observer._stop_event.set.assert_called_once()

    # pylint: enable=protected-access
    @patch("pumaguard.server.classify_image_two_stage", return_value=0.7)
    @patch("pumaguard.server.logger")
    @patch("pumaguard.server.playsound")
    def test_handle_new_file_prediction(
        self, mock_playsound, mock_logger, mock_classify
    ):  # pylint: disable=unused-argument
        """
        Test that _handle_new_file logs the correct chance of puma
        when classify_image returns 0.7.
        """
        self.observer._handle_new_file(  # pylint: disable=protected-access
            filepath="fake_image.jpg"
        )

        mock_playsound.assert_called_once()
        mock_classify.assert_called_once()
        mock_logger.info.assert_called()
        _, path, prediction = mock_logger.info.call_args_list[0][0]

        self.assertEqual(mock_logger.info.call_count, 3)
        mock_logger.info.call_arg_list(
            [
                call("Chance of puma in %s: %.2f%%"),
            ]
        )
        self.assertEqual(path, "fake_image.jpg")
        self.assertAlmostEqual(prediction, 70, places=2)

    @patch("pumaguard.server.classify_image_two_stage", return_value=0.7)
    @patch("pumaguard.server.playsound")
    @patch("pumaguard.server.set_shelly_switch")
    def test_handle_new_file_automatic_plugs_on_off(
        self, mock_set_switch, mock_playsound, mock_classify
    ):
        """
        Test that automatic plugs are turned on before sound plays
        and turned off after sound finishes.
        """
        # Setup automatic plugs
        self.mock_webui.plugs = {
            "aa:bb:cc:dd:ee:01": {
                "hostname": "plug-auto-1",
                "ip_address": "192.168.52.101",
                "mac_address": "aa:bb:cc:dd:ee:01",
                "status": "connected",
                "mode": "automatic",
                "last_seen": "2024-01-15T10:00:00Z",
            },
            "aa:bb:cc:dd:ee:02": {
                "hostname": "plug-auto-2",
                "ip_address": "192.168.52.102",
                "mac_address": "aa:bb:cc:dd:ee:02",
                "status": "connected",
                "mode": "automatic",
                "last_seen": "2024-01-15T10:00:00Z",
            },
            "aa:bb:cc:dd:ee:03": {
                "hostname": "plug-manual",
                "ip_address": "192.168.52.103",
                "mac_address": "aa:bb:cc:dd:ee:03",
                "status": "connected",
                "mode": "on",  # Not automatic
                "last_seen": "2024-01-15T10:00:00Z",
            },
        }

        # Mock successful Shelly API responses
        mock_set_switch.return_value = (True, {"was_on": False}, None)

        self.observer._handle_new_file(  # pylint: disable=protected-access
            filepath="fake_puma_image.jpg"
        )

        # Verify classify was called
        mock_classify.assert_called_once()

        # Verify sound was played
        mock_playsound.assert_called_once()

        # Verify set_shelly_switch was called 4 times:
        # 2 for turning on automatic plugs, 2 for turning off
        self.assertEqual(mock_set_switch.call_count, 4)

        # Verify the order: ON calls before playsound, OFF calls after
        calls = mock_set_switch.call_args_list

        # First two calls should turn plugs ON
        self.assertTrue(calls[0][0][1])  # on_state=True
        self.assertTrue(calls[1][0][1])  # on_state=True

        # Last two calls should turn plugs OFF
        self.assertFalse(calls[2][0][1])  # on_state=False
        self.assertFalse(calls[3][0][1])  # on_state=False

        # Verify only automatic plugs were controlled (not the manual one)
        controlled_ips = {call_info[0][0] for call_info in calls}
        self.assertIn("192.168.52.101", controlled_ips)
        self.assertIn("192.168.52.102", controlled_ips)
        self.assertNotIn("192.168.52.103", controlled_ips)

    @patch("pumaguard.server.classify_image_two_stage", return_value=0.3)
    @patch("pumaguard.server.playsound")
    @patch("pumaguard.server.set_shelly_switch")
    def test_handle_new_file_no_puma_no_plug_control(
        self, mock_set_switch, mock_playsound, mock_classify
    ):
        """
        Test that plugs are NOT controlled when no puma is detected.
        """
        # Setup automatic plugs
        self.mock_webui.plugs = {
            "aa:bb:cc:dd:ee:01": {
                "hostname": "plug-auto-1",
                "ip_address": "192.168.52.101",
                "mac_address": "aa:bb:cc:dd:ee:01",
                "status": "connected",
                "mode": "automatic",
                "last_seen": "2024-01-15T10:00:00Z",
            },
        }

        self.observer._handle_new_file(  # pylint: disable=protected-access
            filepath="fake_no_puma_image.jpg"
        )

        # Verify classify was called
        mock_classify.assert_called_once()

        # Verify sound was NOT played (since prediction < 0.5)
        mock_playsound.assert_not_called()

        # Verify set_shelly_switch was NOT called (no plug control)
        mock_set_switch.assert_not_called()

    @patch("pumaguard.server.classify_image_two_stage", return_value=0.7)
    @patch("pumaguard.server.playsound")
    @patch("pumaguard.server.set_shelly_switch")
    def test_handle_new_file_disconnected_plugs_not_controlled(
        self, mock_set_switch, mock_playsound, mock_classify
    ):
        """
        Test that disconnected automatic plugs are not controlled.
        """
        # Setup plugs with one disconnected
        self.mock_webui.plugs = {
            "aa:bb:cc:dd:ee:01": {
                "hostname": "plug-auto-connected",
                "ip_address": "192.168.52.101",
                "mac_address": "aa:bb:cc:dd:ee:01",
                "status": "connected",
                "mode": "automatic",
                "last_seen": "2024-01-15T10:00:00Z",
            },
            "aa:bb:cc:dd:ee:02": {
                "hostname": "plug-auto-disconnected",
                "ip_address": "192.168.52.102",
                "mac_address": "aa:bb:cc:dd:ee:02",
                "status": "disconnected",
                "mode": "automatic",
                "last_seen": "2024-01-15T09:00:00Z",
            },
        }

        # Mock successful Shelly API responses
        mock_set_switch.return_value = (True, {"was_on": False}, None)

        self.observer._handle_new_file(  # pylint: disable=protected-access
            filepath="fake_puma_image.jpg"
        )

        # Verify classify and sound playback
        mock_classify.assert_called_once()
        mock_playsound.assert_called_once()

        # Verify only the connected plug was controlled (2 calls: on + off)
        self.assertEqual(mock_set_switch.call_count, 2)

        # Verify only the connected plug's IP was used
        calls = mock_set_switch.call_args_list
        for call_info in calls:
            # First argument is IP address
            self.assertEqual(call_info[0][0], "192.168.52.101")

    @patch("pumaguard.server.Image.open")
    @patch("pumaguard.server.FolderObserver._get_time")
    @patch("pumaguard.server.logger")
    def test_wait_for_file_stability_closed_immediately(
        self, mock_logger, mock_time, mock_open
    ):
        """
        If file can be opened immediately, it is considered closed.
        """
        mock_time.side_effect = [0.0, 0.1]
        mock_logger.info = MagicMock()

        result = self.observer._wait_for_file_stability(  # pylint: disable=protected-access
            "somepath", timeout=1, interval=0.01
        )
        self.assertEqual(result, True)
        self.assertEqual(mock_open.call_count, 1)
        self.assertEqual(mock_time.call_count, 2)
        mock_logger.info.assert_called()

    @patch("pumaguard.server.Image.open")
    @patch("pumaguard.server.FolderObserver._sleep", return_value=None)
    @patch("pumaguard.server.FolderObserver._get_time")
    def test_wait_for_file_stability_opens_then_closes(
        self, mock_time, mock_sleep, mock_open
    ):
        """
        If file raises OSError first then opens successfully,
        method returns the converted image.
        """
        mock_time.side_effect = [0.0, 0.1, 0.2, 0.3]

        # First call raises OSError, second and third calls succeed
        # (verify + convert)
        mock_open.side_effect = [
            OSError("Image not ready"),
            MagicMock(),
            MagicMock(),
        ]

        # pylint: disable=protected-access
        result = self.observer._wait_for_file_stability(
            "somepath", timeout=2, interval=0.01
        )
        self.assertEqual(result, True)
        self.assertEqual(mock_sleep.call_count, 1)
        self.assertEqual(mock_open.call_count, 2)
        self.assertEqual(mock_time.call_count, 3)

    @patch("pumaguard.server.FolderObserver._get_time")
    @patch("pumaguard.server.FolderObserver._sleep")
    @patch("pumaguard.server.Image.open")
    def test_wait_for_file_stability_timeout(
        self, mock_open, mock_sleep, mock_time
    ):
        """
        If time advances beyond timeout before file can be opened,
        method returns None.
        """
        mock_open.side_effect = OSError("Image not ready")
        mock_sleep.return_value = None

        # Provide enough time values: start_time, checks in the loop, and
        # logger.warning() call
        mock_time.side_effect = [1000.0, 1000.2, 1000.4, 1001.5, 1001.6]

        # pylint: disable=protected-access
        result = self.observer._wait_for_file_stability(
            "somepath", timeout=1, interval=0.01
        )
        self.assertFalse(result)
        self.assertGreater(mock_open.call_count, 0)

    @patch("pumaguard.server.FolderObserver._get_time")
    @patch("pumaguard.server.FolderObserver._sleep")
    def test_wait_for_file_stability_truncated_image(
        self, mock_sleep, mock_time
    ):
        """
        Test that _wait_for_file_stability handles truncated images correctly.
        It should retry until the image is complete or timeout occurs.
        """
        mock_time.side_effect = [0.0, 0.1, 0.2]
        mock_sleep.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_image.jpg")

            # Create a valid small image
            img = Image.new("RGB", (10, 10), color="red")
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG")
            full_image_data = img_bytes.getvalue()

            # First write a truncated version (incomplete file)
            with open(test_file, "wb") as f:
                f.write(full_image_data[: len(full_image_data) - 100])

            # Create a patched version that writes the full file after first
            # attempt
            original_open = Image.open
            attempt_count = [0]

            def mock_open_with_completion(filepath, *args, **kwargs):
                attempt_count[0] += 1
                if attempt_count[0] == 1:
                    # First attempt: file is still truncated, raise error
                    raise OSError("image file is truncated")
                # Second attempt: complete the file
                with open(test_file, "wb") as f:
                    f.write(full_image_data)
                return original_open(filepath, *args, **kwargs)

            with patch(
                "pumaguard.server.Image.open",
                side_effect=mock_open_with_completion,
            ):
                # pylint: disable=protected-access
                result = self.observer._wait_for_file_stability(
                    test_file, timeout=2, interval=0.01
                )

            self.assertIsNotNone(result)
            self.assertEqual(attempt_count[0], 2)

    def test_wait_for_file_stability_permanently_truncated(self):
        """
        Test that _wait_for_file_stability returns None when image remains
        truncated.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_image.jpg")

            # Create a truncated image that will never complete
            img = Image.new("RGB", (10, 10), color="blue")
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="JPEG")
            truncated_data = img_bytes.getvalue()[:20]  # Only first 20 bytes

            with open(test_file, "wb") as f:
                f.write(truncated_data)

            # Mock Image.open to always raise OSError (truncated image),
            # bypassing the ultralytics monkey-patch that attempts to install
            # pi_heif when PIL.UnidentifiedImageError is raised.
            with patch(
                "pumaguard.server.Image.open",
                side_effect=OSError("image file is truncated"),
            ):
                # pylint: disable=protected-access
                result = self.observer._wait_for_file_stability(
                    test_file, timeout=1, interval=0.01
                )

            # Should return False after timeout
            self.assertFalse(result)


class TestHandleNewFileNotification(unittest.TestCase):
    """
    Tests verifying that image_notification_callback is invoked by
    _handle_new_file after a classified image is moved.
    """

    def setUp(self):
        self.presets = Settings()
        self.presets.notebook_number = 6
        self.presets.model_version = "pre-trained"
        self.presets.image_dimensions = (512, 512)
        self.mock_webui = MagicMock()
        self.mock_webui.plugs = {}
        self.mock_notification = MagicMock()
        self.mock_webui.image_notification_callback = self.mock_notification
        self.observer = FolderObserver(
            "test_folder", "inotify", self.presets, self.mock_webui
        )

    @patch("pumaguard.server.shutil.move")
    @patch("pumaguard.server.Path.mkdir")
    @patch("pumaguard.server.classify_image_two_stage", return_value=0.3)
    def test_notification_called_after_move_non_puma(
        self,
        mock_classify,
        mock_mkdir,  # pylint: disable=unused-argument
        mock_move,
    ):
        """
        image_notification_callback must be called with 'image_added' after a
        non-puma image is successfully moved to its classification folder.
        """
        self.observer._handle_new_file(  # pylint: disable=protected-access
            filepath="test_folder/other.jpg"
        )

        mock_classify.assert_called_once()
        mock_move.assert_called_once()
        self.mock_notification.assert_called_once()
        event_type, event_data = self.mock_notification.call_args[0]
        self.assertEqual(event_type, "image_added")
        self.assertIn("path", event_data)
        self.assertIn("folder", event_data)
        # Non-puma images go to classified_other_dir
        self.assertEqual(
            event_data["folder"], self.presets.classified_other_dir
        )

    @patch("pumaguard.server.shutil.move")
    @patch("pumaguard.server.Path.mkdir")
    @patch("pumaguard.server.classify_image_two_stage", return_value=0.9)
    @patch("pumaguard.server.playsound")
    def test_notification_called_after_move_puma(
        self,
        mock_playsound,  # pylint: disable=unused-argument
        mock_classify,
        mock_mkdir,  # pylint: disable=unused-argument
        mock_move,  # pylint: disable=unused-argument
    ):
        """
        image_notification_callback must be called with 'image_added' after a
        puma image is moved to the puma classification folder.
        """
        self.observer._handle_new_file(  # pylint: disable=protected-access
            filepath="test_folder/puma.jpg"
        )

        mock_classify.assert_called_once()
        mock_move.assert_called_once()
        self.mock_notification.assert_called_once()
        event_type, event_data = self.mock_notification.call_args[0]
        self.assertEqual(event_type, "image_added")
        self.assertIn("path", event_data)
        self.assertIn("folder", event_data)
        # Puma images go to classified_puma_dir
        self.assertEqual(
            event_data["folder"], self.presets.classified_puma_dir
        )

    @patch("pumaguard.server.shutil.move", side_effect=OSError("disk full"))
    @patch("pumaguard.server.Path.mkdir")
    @patch("pumaguard.server.classify_image_two_stage", return_value=0.3)
    def test_notification_not_called_when_move_fails(
        self,
        mock_classify,
        mock_mkdir,  # pylint: disable=unused-argument
        mock_move,  # pylint: disable=unused-argument
    ):
        """
        image_notification_callback must NOT be called when shutil.move raises,
        because no image was actually placed in the destination folder.
        """
        self.observer._handle_new_file(  # pylint: disable=protected-access
            filepath="test_folder/other.jpg"
        )

        mock_classify.assert_called_once()
        mock_move.assert_called_once()
        self.mock_notification.assert_not_called()

    @patch("pumaguard.server.shutil.move")
    @patch("pumaguard.server.Path.mkdir")
    @patch("pumaguard.server.classify_image_two_stage", return_value=0.3)
    def test_notification_not_called_when_callback_is_none(
        self,
        mock_classify,
        mock_mkdir,  # pylint: disable=unused-argument
        mock_move,  # pylint: disable=unused-argument
    ):
        """
        _handle_new_file must not raise when image_notification_callback is
        None (i.e. the WebUI was started without the SSE route registered).
        """
        self.mock_webui.image_notification_callback = None

        # Should not raise
        self.observer._handle_new_file(  # pylint: disable=protected-access
            filepath="test_folder/other.jpg"
        )

        mock_classify.assert_called_once()
        mock_move.assert_called_once()


class TestHandleNewFileVizMove(unittest.TestCase):
    """
    Tests verifying that the bounding-box viz image is moved to the correct
    split intermediate folder (intermediate-puma or intermediate-other) after
    classification.
    """

    def setUp(self):
        self.presets = Settings()
        self.presets.notebook_number = 6
        self.presets.model_version = "pre-trained"
        self.presets.image_dimensions = (512, 512)
        self.mock_webui = MagicMock()
        self.mock_webui.plugs = {}
        self.mock_notification = MagicMock()
        self.mock_webui.image_notification_callback = self.mock_notification
        self.observer = FolderObserver(
            "test_folder", "inotify", self.presets, self.mock_webui
        )

    @patch("pumaguard.server.shutil.move")
    @patch("pumaguard.server.Path.mkdir")
    @patch("pumaguard.server.classify_image_two_stage", return_value=0.9)
    @patch("pumaguard.server.playsound")
    def test_viz_image_moved_to_intermediate_puma_on_puma_detection(
        self,
        mock_playsound,  # pylint: disable=unused-argument
        mock_classify,  # pylint: disable=unused-argument
        mock_mkdir,  # pylint: disable=unused-argument
        mock_move,
    ):
        """
        When a puma is detected, the viz image should be moved from
        intermediate_dir to intermediate_puma_dir.
        """
        intermediate_dir = self.presets.intermediate_dir
        intermediate_puma_dir = self.presets.intermediate_puma_dir
        viz_filename = "puma_image_viz.jpg"
        viz_src = os.path.join(intermediate_dir, viz_filename)

        # Simulate the viz file existing in intermediate_dir
        with patch("pumaguard.server.Path.exists", return_value=True):
            self.observer._handle_new_file(  # pylint: disable=protected-access
                filepath="test_folder/puma_image.jpg"
            )

        # shutil.move should be called at least twice:
        # once for the original image, once for the viz
        self.assertGreaterEqual(mock_move.call_count, 2)

        # Find the viz-related move call
        move_calls = [str(c) for c in mock_move.call_args_list]
        viz_move_found = any(viz_filename in c for c in move_calls)
        self.assertTrue(
            viz_move_found,
            f"Expected a move call for {viz_filename}, got: {move_calls}",
        )

        # Verify the destination is inside intermediate_puma_dir
        viz_dest_calls = [
            c
            for c in mock_move.call_args_list
            if viz_filename in str(c.args[0])
        ]
        self.assertTrue(
            len(viz_dest_calls) >= 1,
            "No move call found with viz source path",
        )
        dest_path = str(viz_dest_calls[0].args[1])
        self.assertIn(
            os.path.basename(intermediate_puma_dir),
            dest_path,
            f"Viz dest {dest_path} should be inside intermediate_puma_dir "
            f"{intermediate_puma_dir}",
        )
        _ = viz_src  # consumed for clarity

    @patch("pumaguard.server.shutil.move")
    @patch("pumaguard.server.Path.mkdir")
    @patch("pumaguard.server.classify_image_two_stage", return_value=0.1)
    def test_viz_image_moved_to_intermediate_other_on_no_puma(
        self,
        mock_classify,  # pylint: disable=unused-argument
        mock_mkdir,  # pylint: disable=unused-argument
        mock_move,
    ):
        """
        When no puma is detected, the viz image should be moved from
        intermediate_dir to intermediate_other_dir.
        """
        intermediate_other_dir = self.presets.intermediate_other_dir
        viz_filename = "other_image_viz.jpg"

        with patch("pumaguard.server.Path.exists", return_value=True):
            self.observer._handle_new_file(  # pylint: disable=protected-access
                filepath="test_folder/other_image.jpg"
            )

        self.assertGreaterEqual(mock_move.call_count, 2)

        viz_dest_calls = [
            c
            for c in mock_move.call_args_list
            if viz_filename in str(c.args[0])
        ]
        self.assertTrue(
            len(viz_dest_calls) >= 1,
            "No move call found with viz source path",
        )
        dest_path = str(viz_dest_calls[0].args[1])
        self.assertIn(
            os.path.basename(intermediate_other_dir),
            dest_path,
            f"Viz dest {dest_path} should be inside intermediate_other_dir "
            f"{intermediate_other_dir}",
        )

    @patch("pumaguard.server.shutil.move")
    @patch("pumaguard.server.Path.mkdir")
    @patch("pumaguard.server.classify_image_two_stage", return_value=0.9)
    @patch("pumaguard.server.playsound")
    def test_viz_move_skipped_when_viz_file_absent(
        self,
        mock_playsound,  # pylint: disable=unused-argument
        mock_classify,  # pylint: disable=unused-argument
        mock_mkdir,  # pylint: disable=unused-argument
        mock_move,
    ):
        """
        When no viz file exists in intermediate_dir, _handle_new_file should
        not attempt to move it and should not raise.
        """
        with patch("pumaguard.server.Path.exists", return_value=False):
            # Should not raise even when the viz file is absent
            self.observer._handle_new_file(  # pylint: disable=protected-access
                filepath="test_folder/puma_image.jpg"
            )

        # Only one move call: for the original classified image
        self.assertEqual(mock_move.call_count, 1)


class TestFolderManager(unittest.TestCase):
    """
    Unit tests for FolderManager class
    """

    def setUp(self):
        self.notebook = 6
        self.presets = Settings()
        self.presets.notebook_number = self.notebook
        self.presets.model_version = "pre-trained"
        self.presets.image_dimensions = (512, 512)
        self.mock_webui = MagicMock()
        self.mock_webui.plugs = {}
        self.manager = FolderManager(self.presets, self.mock_webui)

    @patch("pumaguard.server.FolderObserver")
    def test_register_folder(self, MockFolderObserver):  # pylint: disable=invalid-name
        """
        Test register folder.
        """
        folder = "test_folder"
        self.manager.register_folder(folder, "inotify")
        self.assertEqual(len(self.manager.observers), 1)
        MockFolderObserver.assert_called_with(
            folder, "inotify", self.presets, self.mock_webui
        )

    @patch.object(FolderObserver, "start")
    def test_start_all(self, mock_start):
        """
        Test the start_all method.
        """
        folder = "test_folder"
        self.manager.register_folder(folder, "inotify", start=False)
        self.manager.start_all()
        mock_start.assert_called_once()

    @patch.object(FolderObserver, "start")
    @patch.object(FolderObserver, "stop")
    def test_stop_all(self, mock_stop, mock_start):  # pylint: disable=unused-argument
        """
        Test the stop_all method.
        """
        folder = "test_folder"
        self.manager.register_folder(folder, "inotify")
        self.manager.start_all()
        self.manager.stop_all()
        mock_stop.assert_called_once()
