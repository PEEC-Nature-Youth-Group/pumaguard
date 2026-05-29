"""
Unit tests for detect_volume_control() in the sound module.

Tests the auto-detection of the ALSA playback mixer control, covering
priority ordering, capability filtering, error handling, and caching.
"""

import unittest
from types import (
    SimpleNamespace,
)
from unittest.mock import (
    MagicMock,
    patch,
)

from pumaguard.sound import (
    detect_volume_control,
    playsound,
    reset_volume_control_cache,
    set_volume,
)


class TestDetectVolumeControl(unittest.TestCase):
    """
    Test the detect_volume_control function which auto-detects the ALSA
    playback mixer control for the current device.
    """

    def setUp(self):
        """Reset the cached volume control before each test."""
        reset_volume_control_cache()

    @patch("pumaguard.sound.subprocess.run")
    def test_detects_pcm_when_available(self, mock_run):
        """Test that PCM is selected when present and has pvolume
        capability."""
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

        result = detect_volume_control()

        self.assertEqual(result, "PCM")

    @patch("pumaguard.sound.subprocess.run")
    def test_detects_master_when_pcm_absent(self, mock_run):
        """Test that Master is selected when PCM is not present."""
        amixer_output = (
            "Simple mixer control 'Master',0\n"
            "  Capabilities: pvolume pswitch pswitch-joined\n"
            "  Playback channels: Front Left - Front Right\n"
            "  Limits: Playback 0 - 65536\n"
            "  Front Left: Playback 49152 [75%] [on]\n"
            "  Front Right: Playback 49152 [75%] [on]\n"
            "Simple mixer control 'Capture',0\n"
            "  Capabilities: cvolume cswitch cswitch-joined\n"
            "  Capture channels: Front Left - Front Right\n"
            "  Limits: Capture 0 - 65536\n"
            "  Front Left: Capture 0 [0%] [off]\n"
            "  Front Right: Capture 0 [0%] [off]\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout=amixer_output.encode()
        )

        result = detect_volume_control()

        self.assertEqual(result, "Master")

    @patch("pumaguard.sound.subprocess.run")
    def test_prefers_pcm_over_master(self, mock_run):
        """Test that PCM is preferred over Master when both are present."""
        amixer_output = (
            "Simple mixer control 'Master',0\n"
            "  Capabilities: pvolume pswitch\n"
            "  Playback channels: Front Left - Front Right\n"
            "  Limits: Playback 0 - 65536\n"
            "  Front Left: Playback 49152 [75%] [on]\n"
            "Simple mixer control 'PCM',0\n"
            "  Capabilities: pvolume pvolume-joined\n"
            "  Playback channels: Mono\n"
            "  Limits: Playback 0 - 255\n"
            "  Mono: Playback 192 [75%] [on]\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout=amixer_output.encode()
        )

        result = detect_volume_control()

        self.assertEqual(result, "PCM")

    @patch("pumaguard.sound.subprocess.run")
    def test_falls_back_to_first_playback_control(self, mock_run):
        """Test that the first pvolume control is used when none are
        preferred."""
        amixer_output = (
            "Simple mixer control 'CustomOutput',0\n"
            "  Capabilities: pvolume pswitch\n"
            "  Playback channels: Mono\n"
            "  Limits: Playback 0 - 100\n"
            "  Mono: Playback 80 [80%] [on]\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout=amixer_output.encode()
        )

        result = detect_volume_control()

        self.assertEqual(result, "CustomOutput")

    @patch("pumaguard.sound.subprocess.run")
    def test_ignores_capture_only_controls(self, mock_run):
        """Test that controls without pvolume (e.g. Capture) are ignored."""
        amixer_output = (
            "Simple mixer control 'Capture',0\n"
            "  Capabilities: cvolume cswitch cswitch-joined\n"
            "  Capture channels: Front Left - Front Right\n"
            "  Limits: Capture 0 - 65536\n"
            "  Front Left: Capture 0 [0%] [off]\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout=amixer_output.encode()
        )

        result = detect_volume_control()

        self.assertIsNone(result)

    @patch("pumaguard.sound.subprocess.run")
    def test_returns_none_when_amixer_fails(self, mock_run):
        """Test that None is returned when amixer scontents exits non-zero."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout=b"", stderr=b"amixer: error"
        )

        result = detect_volume_control()

        self.assertIsNone(result)

    def test_returns_none_when_amixer_not_found(self):
        """Test that None is returned when amixer is not installed."""
        with patch(
            "pumaguard.sound.subprocess.run",
            side_effect=FileNotFoundError("amixer not found"),
        ):
            result = detect_volume_control()

        self.assertIsNone(result)

    @patch("pumaguard.sound.subprocess.run")
    def test_result_is_cached(self, mock_run):
        """Test that amixer scontents is only called once across multiple
        calls."""
        amixer_output = (
            "Simple mixer control 'Master',0\n"
            "  Capabilities: pvolume pswitch\n"
            "  Playback channels: Mono\n"
            "  Limits: Playback 0 - 65536\n"
            "  Mono: Playback 32768 [50%] [on]\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout=amixer_output.encode()
        )

        first = detect_volume_control()
        second = detect_volume_control()

        self.assertEqual(first, "Master")
        self.assertEqual(second, "Master")
        mock_run.assert_called_once()

    @patch("pumaguard.sound.subprocess.run")
    def test_reset_clears_cache(self, mock_run):
        """Test that reset_volume_control_cache() forces re-detection."""
        amixer_output = (
            "Simple mixer control 'PCM',0\n"
            "  Capabilities: pvolume pvolume-joined\n"
            "  Playback channels: Mono\n"
            "  Limits: Playback 0 - 255\n"
            "  Mono: Playback 192 [75%] [on]\n"
        )
        mock_run.return_value = MagicMock(
            returncode=0, stdout=amixer_output.encode()
        )

        detect_volume_control()
        reset_volume_control_cache()
        detect_volume_control()

        self.assertEqual(mock_run.call_count, 2)


class TestPlaybackVolumeFallback(unittest.TestCase):
    """Tests for playback behavior when ALSA volume control is unavailable."""

    @staticmethod
    def _mock_process():
        return SimpleNamespace(
            pid=1234,
            terminate=MagicMock(),
            wait=MagicMock(),
        )

    @patch("pumaguard.sound.subprocess.Popen")
    @patch("pumaguard.sound.set_volume", return_value=False)
    def test_playsound_uses_software_gain_fallback(
        self,
        mock_set_volume,
        mock_popen,
    ):
        """When ALSA volume control fails, mpg123 fallback gain is used."""
        mock_popen.return_value = self._mock_process()

        playsound("deterrent.mp3", volume=80, blocking=False)

        mock_set_volume.assert_called_once_with(80)
        cmd = mock_popen.call_args.args[0]
        self.assertEqual(
            cmd,
            [
                "mpg123",
                "-o",
                "alsa,pulse",
                "-f",
                "26214",
                "deterrent.mp3",
            ],
        )

    @patch("pumaguard.sound.subprocess.Popen")
    @patch("pumaguard.sound.set_volume", return_value=True)
    def test_playsound_skips_software_gain_when_alsa_set_succeeds(
        self,
        mock_set_volume,
        mock_popen,
    ):
        """When ALSA volume succeeds, no mpg123 software gain is added."""
        mock_popen.return_value = self._mock_process()

        playsound("deterrent.mp3", volume=80, blocking=False)

        mock_set_volume.assert_called_once_with(80)
        cmd = mock_popen.call_args.args[0]
        self.assertEqual(
            cmd,
            ["mpg123", "-o", "alsa,pulse", "deterrent.mp3"],
        )

    @patch("pumaguard.sound.subprocess.run")
    def test_set_volume_returns_false_when_control_is_missing(self, mock_run):
        """set_volume returns False when no ALSA playback control exists."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Simple mixer control 'Capture',0\n"
                "  Capabilities: cvolume cswitch cswitch-joined\n"
            ).encode(),
        )
        reset_volume_control_cache()

        self.assertFalse(set_volume(50))

    @patch("pumaguard.sound.detect_volume_control", return_value=None)
    @patch("pumaguard.sound.subprocess.run")
    def test_set_volume_returns_false_when_detection_returns_none(
        self,
        mock_run,
        _mock_detect,
    ):
        """
        set_volume returns False immediately when control detection
        fails.
        """
        self.assertFalse(set_volume(50))
        mock_run.assert_not_called()
