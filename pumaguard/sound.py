"""
Sounds
"""

import subprocess
import sys


def playsound(soundfile: str):
    """
    Play a sound file.
    """
    try:
        subprocess.run(["mpg123", soundfile], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error playing soundfile {soundfile}: {e}")


def main():
    """
    Main entry point.
    """
    playsound(sys.argv[1])
