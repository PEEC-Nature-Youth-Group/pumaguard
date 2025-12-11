"""
Sounds
"""

import logging
import subprocess
import sys
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Global variable to track the current playing process
_current_process: Optional[subprocess.Popen] = None
_process_lock = threading.Lock()


def playsound(soundfile: str, volume: int = 80, blocking: bool = True):
    """
    Play a sound file with specified volume.

    Args:
        soundfile: Path to the sound file to play
        volume: Volume level from 0-100 (default: 80)
        blocking: If True, wait for sound to finish. If False, return
        immediately (default: True)
    """
    global _current_process  # pylint: disable=global-statement

    logger.info(
        "playsound called: file=%s, volume=%d, blocking=%s",
        soundfile,
        volume,
        blocking,
    )

    # mpg123 -f flag scales output samples (soft gain)
    # Default/normal is 32768 (100%)
    # Valid range: 0 to much higher than 32768
    # Convert 0-100 percentage to mpg123 scale:
    # 0% = 0 (muted), 100% = 32768 (normal), 200% = 65536 (double)
    # Linear scaling: mpg123_volume = (volume / 100) * 32768
    mpg123_volume = int((volume / 100.0) * 32768)

    logger.debug(
        "Volume conversion: %d%% -> mpg123 scale %d", volume, mpg123_volume
    )

    try:
        with _process_lock:
            # Stop any currently playing sound
            if _current_process is not None:
                try:
                    _current_process.terminate()
                    _current_process.wait(timeout=1)
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    pass
                _current_process = None

            # Start new process
            # pylint: disable=consider-using-with
            cmd = [
                "mpg123",
                "-o",
                "alsa,pulse",
                "-f",
                str(mpg123_volume),
                soundfile,
            ]
            logger.info("Executing command: %s", " ".join(cmd))

            _current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            logger.info(
                "Sound playback started, PID: %d", _current_process.pid
            )

            if blocking:
                # Wait for completion
                _current_process.wait()
                _current_process = None

    except subprocess.SubprocessError as e:
        logger.error("Error playing soundfile %s: %s", soundfile, e)
        print(f"Error playing soundfile {soundfile}: {e}")
        with _process_lock:
            _current_process = None


def stop_sound():
    """
    Stop any currently playing sound.

    Returns:
        bool: True if a sound was stopped, False if nothing was playing
    """
    global _current_process  # pylint: disable=global-statement

    with _process_lock:
        if _current_process is not None:
            try:
                logger.info(
                    "Stopping sound playback, PID: %d", _current_process.pid
                )
                _current_process.terminate()
                _current_process.wait(timeout=1)
                logger.info("Sound playback stopped successfully")
                return True
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    _current_process.kill()
                    _current_process.wait(timeout=1)
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    pass
                return True
            finally:
                _current_process = None
        return False


def is_playing():
    """
    Check if a sound is currently playing.

    Returns:
        bool: True if a sound is currently playing, False otherwise
    """
    global _current_process  # pylint: disable=global-statement

    with _process_lock:
        if _current_process is not None:
            # Check if process is still running
            if _current_process.poll() is None:
                return True
            # Process finished, clean up
            _current_process = None
        return False


def main():
    """
    Main entry point.
    """
    if len(sys.argv) < 2:
        print("Usage: pumaguard-sound <soundfile> [volume]")
        sys.exit(1)

    volume = 80
    if len(sys.argv) >= 3:
        try:
            volume = int(sys.argv[2])
            if volume < 0 or volume > 100:
                print("Volume must be between 0 and 100")
                sys.exit(1)
        except ValueError:
            print("Volume must be an integer")
            sys.exit(1)

    playsound(sys.argv[1], volume)
