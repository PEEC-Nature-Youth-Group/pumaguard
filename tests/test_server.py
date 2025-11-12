"""
Test server.
"""

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
    Preset,
)


class TestFolderObserver(unittest.TestCase):
    """
    Unit tests for FolderObserver class
    """

    def setUp(self):
        self.folder = "test_folder"
        self.notebook = 6
        self.presets = Preset()
        self.presets.notebook_number = self.notebook
        self.presets.model_version = "pre-trained"
        self.presets.image_dimensions = (512, 512)
        self.observer = FolderObserver(self.folder, "inotify", self.presets)

    @patch("pumaguard.server.subprocess.Popen")
    @patch("pumaguard.server.threading.Thread")
    def test_observe_new_file(self, MockThread, MockPopen):  # pylint: disable=invalid-name
        """
        Test observing a new file.
        """
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

        self.assertEqual(mock_logger.info.call_count, 2)
        mock_logger.info.call_arg_list(
            [
                call("Chance of puma in %s: %.2f%%"),
            ]
        )
        self.assertEqual(path, "fake_image.jpg")
        self.assertAlmostEqual(prediction, 70, places=2)

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

            # The file will always be truncated
            # pylint: disable=protected-access
            result = self.observer._wait_for_file_stability(
                test_file, timeout=1, interval=0.01
            )

            # Should return None after timeout
            self.assertFalse(result)


class TestFolderManager(unittest.TestCase):
    """
    Unit tests for FolderManager class
    """

    def setUp(self):
        self.notebook = 6
        self.presets = Preset()
        self.presets.notebook_number = self.notebook
        self.presets.model_version = "pre-trained"
        self.presets.image_dimensions = (512, 512)
        self.manager = FolderManager(self.presets)

    @patch("pumaguard.server.FolderObserver")
    def test_register_folder(self, MockFolderObserver):  # pylint: disable=invalid-name
        """
        Test register folder.
        """
        folder = "test_folder"
        self.manager.register_folder(folder, "inotify")
        self.assertEqual(len(self.manager.observers), 1)
        MockFolderObserver.assert_called_with(folder, "inotify", self.presets)

    @patch.object(FolderObserver, "start")
    def test_start_all(self, mock_start):
        """
        Test the start_all method.
        """
        folder = "test_folder"
        self.manager.register_folder(folder, "inotify")
        self.manager.start_all()
        mock_start.assert_called_once()

    @patch.object(FolderObserver, "stop")
    def test_stop_all(self, mock_stop):
        """
        Test the stop_all method.
        """
        folder = "test_folder"
        self.manager.register_folder(folder, "inotify")
        self.manager.start_all()
        self.manager.stop_all()
        mock_stop.assert_called_once()
