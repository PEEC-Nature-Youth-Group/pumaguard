"""
Sounds
"""

import logging
import re
import subprocess
import sys
import threading
from typing import (
    Optional,
)

logger = logging.getLogger(__name__)

# Global variable to track the current playing process
_current_process: Optional[subprocess.Popen] = None
_process_lock = threading.Lock()


def get_volume(control: str = "PCM") -> Optional[int]:
    """
    Get the current ALSA mixer volume using amixer.

    Args:
        control: ALSA mixer control name (default: "PCM")

    Returns:
        Current volume level as an integer from 0-100, or None if it
        could not be determined.
    """
    logger.debug("Reading ALSA volume: control=%s", control)
    try:
        cmd = ["amixer", "get", control]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "amixer get %s failed (rc=%d): %s",
                control,
                result.returncode,
                result.stderr.decode().strip(),
            )
            return None

        output = result.stdout.decode()
        # amixer output contains lines like:
        #   Mono: Playback 192 [75%] [on]
        #   Front Left: Playback 49152 [75%] [on]
        # Extract the first percentage value found.
        match = re.search(r"\[(\d+)%\]", output)
        if match:
            volume = int(match.group(1))
            logger.debug(
                "ALSA volume read: %d%% on control %s", volume, control
            )
            return volume

        logger.warning(
            "Could not parse volume from amixer output: %s", output.strip()
        )
        return None
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("Could not read ALSA volume via amixer: %s", e)
        return None


def set_volume(volume: int, control: str = "PCM"):
    """
    Set the ALSA mixer volume using amixer.

    Args:
        volume: Volume level from 0-100
        control: ALSA mixer control name (default: "PCM")
    """
    logger.info(
        "Setting ALSA volume: control=%s, volume=%d%%", control, volume
    )
    try:
        cmd = ["amixer", "set", control, f"{volume}%"]
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "amixer set %s %d%% failed (rc=%d): %s",
                control,
                volume,
                result.returncode,
                result.stderr.decode().strip(),
            )
        else:
            logger.debug(
                "ALSA volume set to %d%% on control %s", volume, control
            )
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("Could not set ALSA volume via amixer: %s", e)


def playsound(soundfile: str, volume: int = 80, blocking: bool = True):
    """
    Play a sound file with specified volume.

    The volume is applied via the ALSA mixer (amixer) before playback,
    so the system output level is adjusted rather than using mpg123's
    software scaling.

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

    # Set the ALSA mixer volume before playback
    set_volume(volume)

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

            cmd = [
                "mpg123",
                "-o",
                "alsa,pulse",
                soundfile,
            ]
            logger.info("Executing command: %s", " ".join(cmd))

            # pylint: disable=consider-using-with
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
