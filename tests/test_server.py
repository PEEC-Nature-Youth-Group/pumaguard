"""
Test server.
"""

import unittest
from unittest.mock import (
    MagicMock,
    patch,
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
        self.folder = 'test_folder'
        self.notebook = 6
        self.presets = Preset()
        self.presets.notebook_number = self.notebook
        self.presets.model_version = 'pre-trained'
        self.presets.image_dimensions = (512, 512)
        self.observer = FolderObserver(self.folder, 'inotify', self.presets)

    @patch('pumaguard.server.subprocess.Popen')
    def test_observe_new_file(self, MockPopen):  # pylint: disable=invalid-name
        """
        Test observing a new file.
        """
        mock_process = MagicMock()
        mock_process.stdout = iter(['test_folder/new_file.jpg\n'])
        MockPopen.return_value.__enter__.return_value = mock_process

        with patch.object(self.observer, '_handle_new_file') \
                as mock_handle_new_file, \
                patch.object(self.observer, '_wait_for_file_stability') \
                as mock_wait:
            self.observer._observe()  # pylint: disable=protected-access
            mock_handle_new_file.assert_called_once_with(
                'test_folder/new_file.jpg')
            mock_wait.assert_called_once_with(
                'test_folder/new_file.jpg')

    @patch('pumaguard.server.threading.Thread')
    def test_start(self, MockThread):  # pylint: disable=invalid-name
        """
        Test starting the observer.
        """
        self.observer.start()
        MockThread.assert_called_once_with(
            target=self.observer._observe)  # pylint: disable=protected-access
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

    @patch('pumaguard.server.classify_image', return_value=0.7)
    @patch('pumaguard.server.logger')
    def test_handle_new_file_prediction(self, mock_logger, mock_classify): \
            # pylint: disable=unused-argument
        """
        Test that _handle_new_file logs the correct chance of puma
        when classify_image returns 0.7.
        """
        self.observer._handle_new_file(  # pylint: disable=protected-access
            'fake_image.jpg')

        mock_classify.assert_called_once()
        mock_logger.info.assert_called_once()
        msg, path, prediction = mock_logger.info.call_args_list[0][0]

        self.assertEqual(msg, 'Chance of puma in %s: %.2f%%')
        self.assertEqual(path, 'fake_image.jpg')
        self.assertAlmostEqual(prediction, 30, places=2)


class TestFolderManager(unittest.TestCase):
    """
    Unit tests for FolderManager class
    """

    def setUp(self):
        self.notebook = 6
        self.presets = Preset()
        self.presets.notebook_number = self.notebook
        self.presets.model_version = 'pre-trained'
        self.presets.image_dimensions = (512, 512)
        self.manager = FolderManager(self.presets)

    @patch('pumaguard.server.FolderObserver')
    def test_register_folder(self, MockFolderObserver): \
            # pylint: disable=invalid-name
        """
        Test register folder.
        """
        folder = 'test_folder'
        self.manager.register_folder(folder, 'inotify')
        self.assertEqual(len(self.manager.observers), 1)
        MockFolderObserver.assert_called_with(folder, 'inotify', self.presets)

    @patch.object(FolderObserver, 'start')
    def test_start_all(self, mock_start):
        """
        Test the start_all method.
        """
        folder = 'test_folder'
        self.manager.register_folder(folder, 'inotify')
        self.manager.start_all()
        mock_start.assert_called_once()

    @patch.object(FolderObserver, 'stop')
    def test_stop_all(self, mock_stop):
        """
        Test the stop_all method.
        """
        folder = 'test_folder'
        self.manager.register_folder(folder, 'inotify')
        self.manager.start_all()
        self.manager.stop_all()
        mock_stop.assert_called_once()
