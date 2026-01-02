"""
Test sound module.
"""

import subprocess
import unittest
from unittest.mock import (
    MagicMock,
    patch,
)

import pumaguard.sound
from pumaguard.sound import (
    is_playing,
    playsound,
    stop_sound,
)


class TestPlaysound(unittest.TestCase):
    """
    Unit tests for playsound function with mocked mpg123 calls.
    """

    def setUp(self):
        """Reset the global process state before each test."""
        # pylint: disable=protected-access
        pumaguard.sound._current_process = None

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_default_volume(self, mock_popen):
        """
        Test playsound with default volume (80%).
        """
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        playsound("test_sound.mp3", blocking=False)

        # Verify Popen was called with correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]

        # Check command structure
        self.assertEqual(call_args[0], "mpg123")
        self.assertEqual(call_args[1], "-o")
        self.assertEqual(call_args[2], "alsa,pulse")
        self.assertEqual(call_args[3], "--scale")
        # 80% should convert to 26214 (80/100 * 32768)
        self.assertEqual(call_args[4], "26214")
        self.assertEqual(call_args[5], "test_sound.mp3")

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_volume_levels(self, mock_popen):
        """
        Test playsound with different volume levels to verify correct
        volume conversion.
        """
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # Test various volume levels
        test_cases = [
            (0, 0),  # 0% = 0
            (25, 8192),  # 25% = 8192
            (50, 16384),  # 50% = 16384
            (75, 24576),  # 75% = 24576
            (100, 32768),  # 100% = 32768
        ]

        for volume_percent, expected_mpg123_volume in test_cases:
            # Reset mock
            mock_popen.reset_mock()
            # Reset global process state
            # pylint: disable=protected-access
            pumaguard.sound._current_process = None

            playsound("test_sound.mp3", volume=volume_percent, blocking=False)

            # Verify the volume scale parameter
            call_args = mock_popen.call_args[0][0]
            actual_volume = call_args[4]
            self.assertEqual(
                actual_volume,
                str(expected_mpg123_volume),
                f"Volume {volume_percent}% should convert to "
                f"{expected_mpg123_volume}",
            )

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_blocking_mode(self, mock_popen):
        """
        Test playsound in blocking mode calls wait().
        """
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        playsound("test_sound.mp3", blocking=True)

        # Verify wait was called for blocking mode
        mock_process.wait.assert_called_once()

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_non_blocking_mode(self, mock_popen):
        """
        Test playsound in non-blocking mode does not call wait().
        """
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        playsound("test_sound.mp3", blocking=False)

        # Verify wait was NOT called for non-blocking mode
        mock_process.wait.assert_not_called()

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_stops_previous_sound(self, mock_popen):
        """
        Test that playsound terminates a previously playing sound.
        """
        # Create first process
        mock_process1 = MagicMock()
        mock_process1.pid = 12345

        # Create second process
        mock_process2 = MagicMock()
        mock_process2.pid = 67890

        mock_popen.side_effect = [mock_process1, mock_process2]

        # Start first sound (non-blocking)
        playsound("sound1.mp3", blocking=False)

        # Start second sound - should terminate first
        playsound("sound2.mp3", blocking=False)

        # Verify first process was terminated
        mock_process1.terminate.assert_called_once()
        mock_process1.wait.assert_called_once_with(timeout=1)

    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_when_playing(self, mock_popen):
        """
        Test stop_sound() when a sound is playing.
        """
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # Start playing a sound (non-blocking)
        playsound("test_sound.mp3", blocking=False)

        # Stop the sound
        result = stop_sound()

        # Verify it was stopped
        self.assertTrue(result)
        mock_process.terminate.assert_called()

    def test_stop_sound_when_not_playing(self):
        """
        Test stop_sound() when nothing is playing.
        """
        # Ensure nothing is playing
        # pylint: disable=protected-access
        pumaguard.sound._current_process = None

        result = stop_sound()

        # Should return False when nothing was playing
        self.assertFalse(result)

    @patch("pumaguard.sound.subprocess.Popen")
    def test_is_playing_when_sound_active(self, mock_popen):
        """
        Test is_playing() returns True when sound is active.
        """
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # None means still running
        mock_popen.return_value = mock_process

        # Start playing a sound (non-blocking)
        playsound("test_sound.mp3", blocking=False)

        # Check if playing
        result = is_playing()
        self.assertTrue(result)

    @patch("pumaguard.sound.subprocess.Popen")
    def test_is_playing_when_sound_finished(self, mock_popen):
        """
        Test is_playing() returns False when sound has finished.
        """
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # 0 means process finished
        mock_popen.return_value = mock_process

        # Start playing a sound (non-blocking)
        playsound("test_sound.mp3", blocking=False)

        # Check if playing - should return False and clean up
        result = is_playing()
        self.assertFalse(result)

    def test_is_playing_when_nothing_started(self):
        """
        Test is_playing() returns False when no sound has been started.
        """
        # Ensure nothing is playing
        # pylint: disable=protected-access
        pumaguard.sound._current_process = None

        result = is_playing()
        self.assertFalse(result)

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_handles_subprocess_error(self, mock_popen):
        """
        Test playsound handles subprocess errors gracefully.
        """
        # Make Popen raise a SubprocessError (which is caught)
        mock_popen.side_effect = subprocess.SubprocessError("Process error")

        # Should not raise exception
        try:
            playsound("test_sound.mp3", blocking=False)
        except subprocess.SubprocessError:
            self.fail("playsound should handle SubprocessError gracefully")

        # Verify Popen was called
        mock_popen.assert_called_once()

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_oserror_not_caught(self, mock_popen):
        """
        Test that OSError (e.g., command not found) is not caught.
        This documents the current behavior - OSError propagates to caller.
        """
        # Make Popen raise OSError (not caught by current implementation)
        mock_popen.side_effect = OSError("mpg123 not found")

        # OSError should propagate
        with self.assertRaises(OSError):
            playsound("test_sound.mp3", blocking=False)

        # Verify Popen was called
        mock_popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
