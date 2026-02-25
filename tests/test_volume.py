"""
Unit tests for sound module functionality.

Tests the playsound, stop_sound, is_playing, get_volume, and set_volume
functions with proper mocking to avoid actual audio playback or amixer
calls during testing.
"""

import subprocess
import threading
import unittest
from unittest.mock import (
    MagicMock,
    Mock,
    patch,
)

from pumaguard.sound import (
    get_volume,
    is_playing,
    playsound,
    set_volume,
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

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_basic(self, mock_popen, mock_set_volume):
        """Test basic sound playback with default parameters."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        playsound("/path/to/sound.mp3")

        # Verify set_volume was called with default volume
        mock_set_volume.assert_called_once_with(80)

        # Verify mpg123 was called with correct arguments (no --scale)
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], "mpg123")
        self.assertEqual(args[1], "-o")
        self.assertEqual(args[2], "alsa,pulse")
        self.assertEqual(args[3], "/path/to/sound.mp3")

        # Verify wait was called (blocking=True by default)
        mock_process.wait.assert_called_once()

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_volume_levels(self, mock_popen, mock_set_volume):
        """Test playsound with different volume levels."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # Test volume 0%
        playsound("/path/to/sound.mp3", volume=0)
        mock_set_volume.assert_called_with(0)

        # Test volume 50%
        playsound("/path/to/sound.mp3", volume=50)
        mock_set_volume.assert_called_with(50)

        # Test volume 100%
        playsound("/path/to/sound.mp3", volume=100)
        mock_set_volume.assert_called_with(100)

        # Verify set_volume was called once per playsound call
        self.assertEqual(mock_set_volume.call_count, 3)

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_non_blocking(self, mock_popen, mock_set_volume):
        """Test playsound with blocking=False."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        playsound("/path/to/sound.mp3", blocking=False)

        # Verify set_volume was called
        mock_set_volume.assert_called_once_with(80)

        # Verify subprocess was called
        mock_popen.assert_called_once()

        # Verify wait was NOT called (non-blocking)
        mock_process.wait.assert_not_called()

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_stops_previous_sound(self, mock_popen, mock_set_volume):
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

        # set_volume called once per playsound
        self.assertEqual(mock_set_volume.call_count, 2)

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_subprocess_error(self, mock_popen, mock_set_volume):
        """Test playsound handles subprocess errors gracefully."""
        mock_popen.side_effect = subprocess.SubprocessError("Command failed")

        # Should not raise exception
        playsound("/path/to/sound.mp3")

        # set_volume should still have been called before the error
        mock_set_volume.assert_called_once_with(80)

        # Process should be cleaned up
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            self.assertIsNone(
                pumaguard.sound._current_process  # pylint: disable=protected-access
            )

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_stdout_stderr_devnull(
        self, mock_popen, mock_set_volume
    ):
        """Test that stdout and stderr are redirected to DEVNULL."""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        playsound("/path/to/sound.mp3")

        mock_set_volume.assert_called_once()

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

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_when_playing(self, mock_popen, mock_set_volume):
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

        mock_set_volume.assert_called_once()

    def test_stop_sound_when_nothing_playing(self):
        """Test stopping when no sound is playing."""
        result = stop_sound()

        # Should return False
        self.assertFalse(result)

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_timeout_then_kill(self, mock_popen, mock_set_volume):
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

        mock_set_volume.assert_called_once()

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_process_lookup_error(
        self, mock_popen, mock_set_volume
    ):
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

        mock_set_volume.assert_called_once()

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_kill_timeout(self, mock_popen, mock_set_volume):
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

        mock_set_volume.assert_called_once()

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_stop_sound_kill_process_lookup_error(
        self, mock_popen, mock_set_volume
    ):
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

        mock_set_volume.assert_called_once()

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_cleanup_previous_timeout(
        self, mock_popen, mock_set_volume
    ):
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

        self.assertEqual(mock_set_volume.call_count, 2)

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_playsound_cleanup_previous_process_lookup_error(
        self, mock_popen, mock_set_volume
    ):
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

        self.assertEqual(mock_set_volume.call_count, 2)


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

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_is_playing_when_sound_playing(self, mock_popen, mock_set_volume):
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
        mock_set_volume.assert_called_once()

    def test_is_playing_when_nothing_playing(self):
        """Test is_playing returns False when no sound is playing."""
        result = is_playing()

        self.assertFalse(result)

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_is_playing_cleans_up_finished_process(
        self, mock_popen, mock_set_volume
    ):
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

        mock_set_volume.assert_called_once()


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

    @patch("pumaguard.sound.set_volume")
    @patch("pumaguard.sound.subprocess.Popen")
    def test_concurrent_playsound_calls(self, mock_popen, mock_set_volume):
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
        self.assertEqual(mock_set_volume.call_count, 5)

        # Verify only one process is active at the end
        import pumaguard.sound  # pylint: disable=import-outside-toplevel

        with pumaguard.sound._process_lock:  # pylint: disable=protected-access
            self.assertIsNotNone(
                pumaguard.sound._current_process  # pylint: disable=protected-access
            )


class TestSetVolume(unittest.TestCase):
    """
    Test the set_volume function which calls amixer to set ALSA volume.
    """

    @patch("pumaguard.sound.subprocess.run")
    def test_set_volume_calls_amixer(self, mock_run):
        """Test that set_volume calls amixer with the correct arguments."""
        mock_run.return_value = MagicMock(returncode=0)

        set_volume(75)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["amixer", "set", "PCM", "75%"])

    @patch("pumaguard.sound.subprocess.run")
    def test_set_volume_default_control_is_pcm(self, mock_run):
        """Test that the default ALSA control is PCM."""
        mock_run.return_value = MagicMock(returncode=0)

        set_volume(50)

        args = mock_run.call_args[0][0]
        self.assertEqual(args[2], "PCM")

    @patch("pumaguard.sound.subprocess.run")
    def test_set_volume_custom_control(self, mock_run):
        """Test set_volume with a custom ALSA control name."""
        mock_run.return_value = MagicMock(returncode=0)

        set_volume(60, control="Master")

        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["amixer", "set", "Master", "60%"])

    @patch("pumaguard.sound.subprocess.run")
    def test_set_volume_boundary_zero(self, mock_run):
        """Test set_volume at 0%."""
        mock_run.return_value = MagicMock(returncode=0)

        set_volume(0)

        args = mock_run.call_args[0][0]
        self.assertEqual(args[3], "0%")

    @patch("pumaguard.sound.subprocess.run")
    def test_set_volume_boundary_hundred(self, mock_run):
        """Test set_volume at 100%."""
        mock_run.return_value = MagicMock(returncode=0)

        set_volume(100)

        args = mock_run.call_args[0][0]
        self.assertEqual(args[3], "100%")

    @patch("pumaguard.sound.subprocess.run")
    def test_set_volume_amixer_failure_does_not_raise(self, mock_run):
        """Test that a non-zero amixer return code does not raise."""
        mock_run.return_value = MagicMock(
            returncode=1, stderr=b"No such control"
        )

        # Should not raise
        set_volume(80)

    def test_set_volume_amixer_not_found_does_not_raise(self):
        """Test that a missing amixer binary does not raise."""
        with patch(
            "pumaguard.sound.subprocess.run",
            side_effect=FileNotFoundError("amixer not found"),
        ):
            # Should not raise
            set_volume(80)

    @patch("pumaguard.sound.subprocess.run")
    def test_set_volume_subprocess_error_does_not_raise(self, mock_run):
        """Test that a SubprocessError does not raise."""
        mock_run.side_effect = subprocess.SubprocessError("failed")

        # Should not raise
        set_volume(80)


class TestGetVolume(unittest.TestCase):
    """
    Test the get_volume function which reads the ALSA volume via amixer.
    """

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_parses_mono_output(self, mock_run):
        """Test parsing of mono amixer output (e.g. Raspberry Pi PCM)."""
        amixer_output = (
            "Simple mixer control 'PCM',0\n"
            "  Capabilities: pvolume pvolume-joined pswitch pswitch-joined\n"
            "  Playback channels: Mono\n"
            "  Limits: Playback 0 - 255\n"
            "  Mono: Playback 192 [75%] [on]\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout=amixer_output.encode()
        )

        result = get_volume()

        self.assertEqual(result, 75)

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_parses_stereo_output(self, mock_run):
        """Test parsing of stereo amixer output (left/right channels)."""
        amixer_output = (
            "Simple mixer control 'Master',0\n"
            "  Capabilities: pvolume pswitch\n"
            "  Playback channels: Front Left - Front Right\n"
            "  Limits: Playback 0 - 65536\n"
            "  Mono:\n"
            "  Front Left: Playback 49152 [75%] [on]\n"
            "  Front Right: Playback 49152 [75%] [on]\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout=amixer_output.encode()
        )

        result = get_volume(control="Master")

        self.assertEqual(result, 75)

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_default_control_is_pcm(self, mock_run):
        """Test that get_volume queries the PCM control by default."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"Mono: Playback 128 [50%] [on]\n"
        )

        get_volume()

        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["amixer", "get", "PCM"])

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_custom_control(self, mock_run):
        """Test that get_volume queries the specified control."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"Mono: Playback 128 [50%] [on]\n"
        )

        get_volume(control="Headphone")

        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["amixer", "get", "Headphone"])

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_returns_none_on_amixer_failure(self, mock_run):
        """Test that get_volume returns None when amixer exits with error."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout=b"", stderr=b"No such control"
        )

        result = get_volume()

        self.assertIsNone(result)

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_returns_none_when_no_percentage_in_output(
        self, mock_run
    ):
        """Test that get_volume returns None when output has no percentage."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"Simple mixer control 'PCM',0\n"
        )

        result = get_volume()

        self.assertIsNone(result)

    def test_get_volume_returns_none_when_amixer_not_found(self):
        """Test that get_volume returns None when amixer is not installed."""
        with patch(
            "pumaguard.sound.subprocess.run",
            side_effect=FileNotFoundError("amixer not found"),
        ):
            result = get_volume()

        self.assertIsNone(result)

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_returns_none_on_subprocess_error(self, mock_run):
        """Test that get_volume returns None on a SubprocessError."""
        mock_run.side_effect = subprocess.SubprocessError("failed")

        result = get_volume()

        self.assertIsNone(result)

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_boundary_zero(self, mock_run):
        """Test parsing of 0% volume."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"Mono: Playback 0 [0%] [off]\n"
        )

        result = get_volume()

        self.assertEqual(result, 0)

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_boundary_hundred(self, mock_run):
        """Test parsing of 100% volume."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"Mono: Playback 255 [100%] [on]\n"
        )

        result = get_volume()

        self.assertEqual(result, 100)

    @patch("pumaguard.sound.subprocess.run")
    def test_get_volume_returns_first_percentage_for_stereo(self, mock_run):
        """Test that get_volume returns the first channel's percentage."""
        amixer_output = (
            "  Front Left: Playback 32768 [50%] [on]\n"
            "  Front Right: Playback 49152 [75%] [on]\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout=amixer_output.encode()
        )

        result = get_volume()

        # Should return the first percentage found (50, not 75)
        self.assertEqual(result, 50)


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
