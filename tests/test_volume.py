"""
Unit tests for sound module functionality.

Tests the playsound, stop_sound, and is_playing functions with proper mocking
to avoid actual audio playback during testing.
"""

import subprocess
import threading
import unittest
from unittest.mock import (
    Mock,
    patch,
)

from pumaguard.sound import (
    is_playing,
    playsound,
    stop_sound,
)


class TestPlaysound(unittest.TestCase):
    """
    Test the playsound function.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Reset the global process state before each test
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            pumaguard.sound._current_process = (  # pylint: disable=protected-access
                None
            )

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_basic(self, mock_popen):
        """Test basic sound playback with default parameters."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        playsound("/path/to/sound.mp3")

        # Verify subprocess was called with correct arguments
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], "mpg123")
        self.assertEqual(args[1], "-o")
        self.assertEqual(args[2], "alsa,pulse")
        self.assertEqual(args[3], "--scale")
        self.assertEqual(args[4], "26214")  # 80% of 32768
        self.assertEqual(args[5], "/path/to/sound.mp3")

        # Verify wait was called (blocking=True by default)
        mock_process.wait.assert_called_once()

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_volume_levels(self, mock_popen):
        """Test playsound with different volume levels."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # Test volume 0%
        playsound("/path/to/sound.mp3", volume=0)
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[4], "0")

        # Test volume 50%
        playsound("/path/to/sound.mp3", volume=50)
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[4], "16384")  # 50% of 32768

        # Test volume 100%
        playsound("/path/to/sound.mp3", volume=100)
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[4], "32768")  # 100% of 32768

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_non_blocking(self, mock_popen):
        """Test playsound with blocking=False."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        playsound("/path/to/sound.mp3", blocking=False)

        # Verify subprocess was called
        mock_popen.assert_called_once()

        # Verify wait was NOT called (non-blocking)
        mock_process.wait.assert_not_called()

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_stops_previous_sound(self, mock_popen):
        """Test that playsound stops any currently playing sound."""
        # First sound
        mock_process1 = Mock()
        mock_process1.pid = 12345
        mock_process1.poll.return_value = None  # Still running

        # Second sound
        mock_process2 = Mock()
        mock_process2.pid = 67890

        mock_popen.side_effect = [mock_process1, mock_process2]

        # Start first sound (non-blocking)
        playsound("/path/to/sound1.mp3", blocking=False)

        # Start second sound (should terminate first)
        playsound("/path/to/sound2.mp3", blocking=False)

        # Verify first process was terminated
        mock_process1.terminate.assert_called_once()
        mock_process1.wait.assert_called_once_with(timeout=1)

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_subprocess_error(self, mock_popen):
        """Test playsound handles subprocess errors gracefully."""
        mock_popen.side_effect = subprocess.SubprocessError("Command failed")

        # Should not raise exception
        playsound("/path/to/sound.mp3")

        # Process should be cleaned up
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            self.assertIsNone(
                pumaguard.sound._current_process  # pylint: disable=protected-access
            )

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_stdout_stderr_devnull(self, mock_popen):
        """Test that stdout and stderr are redirected to DEVNULL."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        playsound("/path/to/sound.mp3")

        # Verify subprocess.DEVNULL is used
        kwargs = mock_popen.call_args[1]
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)


class TestStopSound(unittest.TestCase):
    """
    Test the stop_sound function.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Reset the global process state before each test
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            pumaguard.sound._current_process = (  # pylint: disable=protected-access
                None
            )

    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_when_playing(self, mock_popen):
        """Test stopping a sound that is currently playing."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Still running
        mock_popen.return_value = mock_process

        # Start a sound (non-blocking)
        playsound("/path/to/sound.mp3", blocking=False)

        # Stop it
        result = stop_sound()

        # Verify process was terminated
        self.assertTrue(result)
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=1)

    def test_stop_sound_when_nothing_playing(self):
        """Test stopping when no sound is playing."""
        result = stop_sound()

        # Should return False
        self.assertFalse(result)

    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_timeout_then_kill(self, mock_popen):
        """Test that stop_sound kills process if terminate times out."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired("cmd", 1),
            None,
        ]
        mock_popen.return_value = mock_process

        # Start a sound
        playsound("/path/to/sound.mp3", blocking=False)

        # Stop it (should timeout then kill)
        result = stop_sound()

        # Verify terminate was called, then kill
        self.assertTrue(result)
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_process_lookup_error(self, mock_popen):
        """Test stop_sound handles ProcessLookupError gracefully."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate.side_effect = ProcessLookupError()
        mock_popen.return_value = mock_process

        # Start a sound
        playsound("/path/to/sound.mp3", blocking=False)

        # Stop it (process already gone)
        result = stop_sound()

        # Should still return True
        self.assertTrue(result)

    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_kill_timeout(self, mock_popen):
        """Test stop_sound handles timeout on kill operation."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        # First wait times out, second wait (after kill) also times out
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired("cmd", 1),
            subprocess.TimeoutExpired("cmd", 1),
        ]
        mock_popen.return_value = mock_process

        # Start a sound
        playsound("/path/to/sound.mp3", blocking=False)

        # Stop it (both terminate and kill timeout)
        result = stop_sound()

        # Should still return True despite timeouts
        self.assertTrue(result)
        mock_process.kill.assert_called_once()

    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_kill_process_lookup_error(self, mock_popen):
        """Test stop_sound handles ProcessLookupError on kill."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired("cmd", 1),
            ProcessLookupError(),
        ]
        mock_popen.return_value = mock_process

        # Start a sound
        playsound("/path/to/sound.mp3", blocking=False)

        # Stop it (terminate times out, kill gets ProcessLookupError)
        result = stop_sound()

        # Should still return True
        self.assertTrue(result)
        mock_process.kill.assert_called_once()

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_cleanup_previous_timeout(self, mock_popen):
        """Test playsound handles timeout when cleaning up previous sound."""
        # First sound
        mock_process1 = Mock()
        mock_process1.pid = 12345
        mock_process1.poll.return_value = None
        mock_process1.wait.side_effect = subprocess.TimeoutExpired("cmd", 1)

        # Second sound
        mock_process2 = Mock()
        mock_process2.pid = 67890

        mock_popen.side_effect = [mock_process1, mock_process2]

        # Start first sound (non-blocking)
        playsound("/path/to/sound1.mp3", blocking=False)

        # Start second sound (cleanup of first times out but should continue)
        playsound("/path/to/sound2.mp3", blocking=False)

        # Verify both processes were created
        self.assertEqual(mock_popen.call_count, 2)
        mock_process1.terminate.assert_called_once()

    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_cleanup_previous_process_lookup_error(self, mock_popen):
        """
        Test playsound handles ProcessLookupError when cleaning up
        previous sound.
        """
        # First sound
        mock_process1 = Mock()
        mock_process1.pid = 12345
        mock_process1.poll.return_value = None
        mock_process1.wait.side_effect = ProcessLookupError()

        # Second sound
        mock_process2 = Mock()
        mock_process2.pid = 67890

        mock_popen.side_effect = [mock_process1, mock_process2]

        # Start first sound (non-blocking)
        playsound("/path/to/sound1.mp3", blocking=False)

        # Start second sound (cleanup of first gets ProcessLookupError
        # but should continue)
        playsound("/path/to/sound2.mp3", blocking=False)

        # Verify both processes were created
        self.assertEqual(mock_popen.call_count, 2)
        mock_process1.terminate.assert_called_once()


class TestIsPlaying(unittest.TestCase):
    """
    Test the is_playing function.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Reset the global process state before each test
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            pumaguard.sound._current_process = (  # pylint: disable=protected-access
                None
            )

    @patch("pumaguard.sound.subprocess.Popen")
    def test_is_playing_when_sound_playing(self, mock_popen):
        """Test is_playing returns True when sound is playing."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Still running
        mock_popen.return_value = mock_process

        # Start a sound (non-blocking)
        playsound("/path/to/sound.mp3", blocking=False)

        # Check if playing
        result = is_playing()

        self.assertTrue(result)
        mock_process.poll.assert_called_once()

    def test_is_playing_when_nothing_playing(self):
        """Test is_playing returns False when no sound is playing."""
        result = is_playing()

        self.assertFalse(result)

    @patch("pumaguard.sound.subprocess.Popen")
    def test_is_playing_cleans_up_finished_process(self, mock_popen):
        """Test is_playing cleans up when process has finished."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Process finished
        mock_popen.return_value = mock_process

        # Start a sound (non-blocking)
        playsound("/path/to/sound.mp3", blocking=False)

        # Check if playing (should clean up)
        result = is_playing()

        self.assertFalse(result)

        # Verify process was cleaned up
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            self.assertIsNone(
                pumaguard.sound._current_process  # pylint: disable=protected-access
            )


class TestThreadSafety(unittest.TestCase):
    """
    Test thread safety of sound functions.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Reset the global process state before each test
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            pumaguard.sound._current_process = (  # pylint: disable=protected-access
                None
            )

    @patch("pumaguard.sound.subprocess.Popen")
    def test_concurrent_playsound_calls(self, mock_popen):
        """Test that concurrent playsound calls are thread-safe."""
        mock_processes = []
        for i in range(5):
            mock_process = Mock()
            mock_process.pid = 10000 + i
            mock_process.poll.return_value = None
            mock_processes.append(mock_process)

        mock_popen.side_effect = mock_processes

        def play_sound(index):
            playsound(f"/path/to/sound{index}.mp3", blocking=False)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=play_sound, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all calls were made
        self.assertEqual(mock_popen.call_count, 5)

        # Verify only one process is active at the end
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            self.assertIsNotNone(
                pumaguard.sound._current_process  # pylint: disable=protected-access
            )


class TestVolumeConversion(unittest.TestCase):
    """
    Test volume percentage to mpg123 scale conversion.
    """

    @patch("pumaguard.sound.subprocess.Popen")
    def test_volume_conversion_formula(self, mock_popen):
        """Test the volume conversion formula is correct."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        test_cases = [
            (0, 0),  # 0% -> 0
            (25, 8192),  # 25% -> 8192
            (50, 16384),  # 50% -> 16384
            (75, 24576),  # 75% -> 24576
            (100, 32768),  # 100% -> 32768
        ]

        for volume_percent, expected_scale in test_cases:
            mock_popen.reset_mock()
            playsound("/path/to/sound.mp3", volume=volume_percent)

            args = mock_popen.call_args[0][0]
            actual_scale = int(args[4])
            self.assertEqual(
                actual_scale,
                expected_scale,
                f"Volume {volume_percent}% should convert to {expected_scale}",
            )


class TestMain(unittest.TestCase):
    """
    Test the main function.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Reset the global process state before each test
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            pumaguard.sound._current_process = (  # pylint: disable=protected-access
                None
            )

    @patch("pumaguard.sound.sys.argv", ["pumaguard-sound"])
    @patch("builtins.print")
    def test_main_no_arguments(self, mock_print):
        """Test main with no arguments shows usage."""
        # pylint: disable=import-outside-toplevel
        from pumaguard.sound import (
            main,
        )

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)
        mock_print.assert_called_once_with(
            "Usage: pumaguard-sound <soundfile> [volume]"
        )

    @patch(
        "pumaguard.sound.sys.argv", ["pumaguard-sound", "/path/to/sound.mp3"]
    )
    @patch("pumaguard.sound.playsound")
    def test_main_with_soundfile_only(self, mock_playsound):
        """Test main with only soundfile argument uses default volume."""
        # pylint: disable=import-outside-toplevel
        from pumaguard.sound import (
            main,
        )

        main()

        mock_playsound.assert_called_once_with("/path/to/sound.mp3", 80)

    @patch(
        "pumaguard.sound.sys.argv",
        ["pumaguard-sound", "/path/to/sound.mp3", "50"],
    )
    @patch("pumaguard.sound.playsound")
    def test_main_with_volume(self, mock_playsound):
        """Test main with soundfile and volume arguments."""
        # pylint: disable=import-outside-toplevel
        from pumaguard.sound import (
            main,
        )

        main()

        mock_playsound.assert_called_once_with("/path/to/sound.mp3", 50)

    @patch(
        "pumaguard.sound.sys.argv",
        ["pumaguard-sound", "/path/to/sound.mp3", "-10"],
    )
    @patch("builtins.print")
    def test_main_with_negative_volume(self, mock_print):
        """Test main with negative volume exits with error."""
        # pylint: disable=import-outside-toplevel
        from pumaguard.sound import (
            main,
        )

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)
        mock_print.assert_called_once_with("Volume must be between 0 and 100")

    @patch(
        "pumaguard.sound.sys.argv",
        ["pumaguard-sound", "/path/to/sound.mp3", "150"],
    )
    @patch("builtins.print")
    def test_main_with_excessive_volume(self, mock_print):
        """Test main with volume > 100 exits with error."""
        # pylint: disable=import-outside-toplevel
        from pumaguard.sound import (
            main,
        )

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)
        mock_print.assert_called_once_with("Volume must be between 0 and 100")

    @patch(
        "pumaguard.sound.sys.argv",
        ["pumaguard-sound", "/path/to/sound.mp3", "invalid"],
    )
    @patch("builtins.print")
    def test_main_with_invalid_volume(self, mock_print):
        """Test main with non-integer volume exits with error."""
        # pylint: disable=import-outside-toplevel
        from pumaguard.sound import (
            main,
        )

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)
        mock_print.assert_called_once_with("Volume must be an integer")

    @patch(
        "pumaguard.sound.sys.argv",
        ["pumaguard-sound", "/path/to/sound.mp3", "0"],
    )
    @patch("pumaguard.sound.playsound")
    def test_main_with_zero_volume(self, mock_playsound):
        """Test main with volume 0 (boundary case)."""
        # pylint: disable=import-outside-toplevel
        from pumaguard.sound import (
            main,
        )

        main()

        mock_playsound.assert_called_once_with("/path/to/sound.mp3", 0)

    @patch(
        "pumaguard.sound.sys.argv",
        ["pumaguard-sound", "/path/to/sound.mp3", "100"],
    )
    @patch("pumaguard.sound.playsound")
    def test_main_with_max_volume(self, mock_playsound):
        """Test main with volume 100 (boundary case)."""
        # pylint: disable=import-outside-toplevel
        from pumaguard.sound import (
            main,
        )

        main()

        mock_playsound.assert_called_once_with("/path/to/sound.mp3", 100)


if __name__ == "__main__":
    unittest.main()
