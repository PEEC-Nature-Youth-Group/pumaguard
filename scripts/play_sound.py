"""
Test script to play a sound file using the USB speaker.
"""

import os

from pumaguard.sound import (
    playsound,
)


def play_sound(file_path, volume=80):
    """
    Play a sound file using the USB speaker.

    Args:
        file_path (str): Path to the sound file.
        volume (int): Volume level 0-100 (default: 80).
    """
    playsound(file_path, volume)


script_dir = os.path.dirname(os.path.abspath(__file__))
sound_file_path = os.path.join(
    script_dir, "../pumaguard-sounds/forest-ambience-296528.mp3"
)
play_sound(sound_file_path)
