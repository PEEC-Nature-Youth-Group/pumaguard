"""
Test script for volume control functionality.

This script tests the playsound function with different volume levels.
"""

import os
import subprocess
import sys
import time

from pumaguard.sound import (
    playsound,
)


def test_volume_levels():
    """
    Test playing sound at different volume levels.
    """
    # Find a test sound file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sound_file = os.path.join(
        script_dir, "../pumaguard-sounds/forest-ambience-296528.mp3"
    )

    if not os.path.exists(sound_file):
        print(f"Error: Sound file not found: {sound_file}")
        sys.exit(1)

    print("Testing volume control with playsound()")
    print("=" * 50)
    print(f"Sound file: {sound_file}\n")

    # Test different volume levels
    volume_levels = [0, 25, 50, 75, 100]

    for volume in volume_levels:
        print(f"Playing at volume {volume}%...")
        try:
            playsound(sound_file, volume)
            print(f"  ✓ Volume {volume}% played successfully")
        except (subprocess.CalledProcessError, OSError) as e:
            print(f"  ✗ Error at volume {volume}%: {e}")

        # Wait a bit between tests
        if volume < 100:
            time.sleep(1)

    print("\n" + "=" * 50)
    print("Volume test completed!")


def main():
    """
    Main entry point.
    """
    if len(sys.argv) > 1:
        # Allow testing with custom sound file
        sound_file = sys.argv[1]
        volume = int(sys.argv[2]) if len(sys.argv) > 2 else 80

        print(f"Playing: {sound_file}")
        print(f"Volume: {volume}%")

        if not os.path.exists(sound_file):
            print(f"Error: File not found: {sound_file}")
            sys.exit(1)

        playsound(sound_file, volume)
    else:
        # Run full test suite
        test_volume_levels()


if __name__ == "__main__":
    main()
