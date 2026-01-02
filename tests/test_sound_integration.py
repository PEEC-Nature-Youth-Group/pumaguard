"""
Integration tests for sound module.

These tests actually play sounds and are meant for manual testing.
They are skipped by default in automated test runs.

To run these tests manually:
    python -m unittest tests.test_sound_integration -v

Or run a specific test:
    INTEGRATION_TESTS=1 python -m unittest \
        tests.test_sound_integration.TestSoundIntegration.test_volume_levels -v
"""

import os
import subprocess
import unittest

from pumaguard.sound import (
    playsound,
)

# Skip integration tests by default unless explicitly enabled
SKIP_INTEGRATION = os.environ.get("INTEGRATION_TESTS") != "1"
SKIP_MESSAGE = "Integration tests disabled. Set INTEGRATION_TESTS=1 to enable."


class TestSoundIntegration(unittest.TestCase):
    """
    Integration tests that play actual sounds.
    These are skipped by default.
    """

    @classmethod
    def setUpClass(cls):
        """Find the test sound file."""
        # Look for sound file relative to tests directory
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(tests_dir)
        cls.sound_file = os.path.join(
            project_root, "pumaguard-sounds", "forest-ambience-296528.mp3"
        )

    @unittest.skipIf(SKIP_INTEGRATION, SKIP_MESSAGE)
    def test_sound_file_exists(self):
        """
        Test that the test sound file exists.
        """
        self.assertTrue(
            os.path.exists(self.sound_file),
            f"Sound file not found: {self.sound_file}",
        )

    @unittest.skipIf(SKIP_INTEGRATION, SKIP_MESSAGE)
    def test_volume_levels(self):
        """
        Test playing sound at different volume levels.
        This actually plays sounds - use for manual testing only.
        """
        if not os.path.exists(self.sound_file):
            self.skipTest(f"Sound file not found: {self.sound_file}")

        print("\n" + "=" * 50)
        print("Testing volume control with actual sound playback")
        print(f"Sound file: {self.sound_file}")
        print("=" * 50)

        # Test different volume levels
        volume_levels = [0, 25, 50, 75, 100]

        for volume in volume_levels:
            with self.subTest(volume=volume):
                print(f"\nPlaying at volume {volume}%...")
                try:
                    playsound(self.sound_file, volume, blocking=True)
                    print(f"  ✓ Volume {volume}% played successfully")
                except (subprocess.CalledProcessError, OSError) as e:
                    self.fail(f"Error at volume {volume}%: {e}")

        print("\n" + "=" * 50)
        print("Volume test completed!")
        print("=" * 50)

    @unittest.skipIf(SKIP_INTEGRATION, SKIP_MESSAGE)
    def test_custom_sound_file(self):
        """
        Test playing a custom sound file if provided.
        Set SOUND_FILE environment variable to test a specific file.
        """
        custom_file = os.environ.get("SOUND_FILE")
        if not custom_file:
            self.skipTest(
                "No custom sound file specified via SOUND_FILE env var"
            )

        if not os.path.exists(custom_file):
            self.fail(f"Custom sound file not found: {custom_file}")

        volume = int(os.environ.get("VOLUME", "80"))

        print(f"\nPlaying: {custom_file}")
        print(f"Volume: {volume}%")

        try:
            playsound(custom_file, volume, blocking=True)
            print("  ✓ Playback completed successfully")
        except (subprocess.CalledProcessError, OSError) as e:
            self.fail(f"Error playing sound: {e}")


if __name__ == "__main__":
    # Print instructions if running directly
    if not SKIP_INTEGRATION:
        print("\n" + "=" * 70)
        print("RUNNING INTEGRATION TESTS - ACTUAL SOUNDS WILL BE PLAYED")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("Integration tests are disabled by default.")
        print("To run these tests, use:")
        print(
            "  INTEGRATION_TESTS=1 python -m unittest "
            "tests.test_sound_integration -v"
        )
        print("\nTo test a custom sound file:")
        print(
            "  INTEGRATION_TESTS=1 SOUND_FILE=/path/to/file.mp3 VOLUME=75 \\"
        )
        print(
            "    python -m unittest "
            "tests.test_sound_integration.TestSoundIntegration"
            ".test_custom_sound_file -v"
        )
        print("=" * 70 + "\n")

    unittest.main()
