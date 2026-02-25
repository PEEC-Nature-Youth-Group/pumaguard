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
    Union,
)

# Controls to try in order of preference when auto-detecting the ALSA playback
# control.  The first entry that exists on the device and supports playback
# volume will be used.
_VOLUME_CONTROL_PRIORITY = [
    "PCM",
    "Master",
    "Speaker",
    "Headphone",
    "Digital",
    "Lineout",
]

# Cached result of detect_volume_control() so we only probe amixer once per
# process lifetime.
_detected_volume_control: Union[str, None] = None

logger = logging.getLogger(__name__)


def detect_volume_control() -> Optional[str]:
    """Auto-detect the ALSA simple-mixer control to use for volume.

    Runs ``amixer scontents`` once and finds all controls that advertise
    ``pvolume`` (playback volume) capability.  From those, the first name that
    appears in :data:`_VOLUME_CONTROL_PRIORITY` is returned.  If none of the
    preferred names match, the first playback-capable control found is returned
    instead.  The result is cached so that ``amixer`` is only invoked once for
    the lifetime of the process.

    Returns:
        The name of the best available playback volume control (e.g.
        ``"PCM"``, ``"Master"``), or ``None`` if amixer is unavailable or no
        suitable control could be found.
    """
    global _detected_volume_control  # pylint: disable=global-statement

    if _detected_volume_control is not None:
        return _detected_volume_control

    logger.debug("Auto-detecting ALSA playback volume control")
    try:
        result = subprocess.run(
            ["amixer", "scontents"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "amixer scontents failed (rc=%d): %s",
                result.returncode,
                result.stderr.decode().strip(),
            )
            return None

        # Parse output: collect control names that have 'pvolume' capability.
        # amixer scontents output looks like:
        #   Simple mixer control 'Master',0
        #     Capabilities: pvolume pswitch pswitch-joined
        #     ...
        #   Simple mixer control 'Capture',0
        #     Capabilities: cvolume cswitch cswitch-joined
        #     ...
        playback_controls: list[str] = []
        current_control: Optional[str] = None
        for line in result.stdout.decode().splitlines():
            ctrl_match = re.match(r"Simple mixer control '([^']+)'", line)
            if ctrl_match:
                current_control = ctrl_match.group(1)
            elif current_control is not None and "Capabilities:" in line:
                if "pvolume" in line:
                    playback_controls.append(current_control)
                # Either way, reset so we don't re-check on subsequent lines.
                current_control = None

        if not playback_controls:
            logger.warning(
                "No ALSA controls with playback volume capability found"
            )
            return None

        # Pick the highest-priority preferred control that is available.
        for preferred in _VOLUME_CONTROL_PRIORITY:
            if preferred in playback_controls:
                _detected_volume_control = preferred
                logger.debug(
                    "Selected ALSA volume control: %s (preferred)",
                    _detected_volume_control,
                )
                return _detected_volume_control

        # None of the preferred names matched — use the first available one.
        _detected_volume_control = playback_controls[0]
        logger.debug(
            "Selected ALSA volume control: %s (first available)",
            _detected_volume_control,
        )
        return _detected_volume_control

    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("Could not detect ALSA volume control: %s", e)
        return None


def reset_volume_control_cache():
    """Reset the cached ALSA volume control detection result.

    This forces :func:`detect_volume_control` to re-probe ``amixer`` on its
    next call.  Intended for use in tests and for situations where the audio
    device has changed at runtime.
    """
    global _detected_volume_control  # pylint: disable=global-statement

    _detected_volume_control = None


# Global variable to track the current playing process
_current_process: Optional[subprocess.Popen] = None
_process_lock = threading.Lock()


def get_volume(control: Optional[str] = None) -> Optional[int]:
    """
    Get the current ALSA mixer volume using amixer.

    Args:
        control: ALSA mixer control name.  When ``None`` (the default) the
            control is auto-detected via :func:`detect_volume_control`.

    Returns:
        Current volume level as an integer from 0-100, or None if it
        could not be determined.
    """
    if control is None:
        control = detect_volume_control()
        if control is None:
            logger.warning("Could not determine ALSA volume control")
            return None
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


def set_volume(volume: int, control: Optional[str] = None):
    """
    Set the ALSA mixer volume using amixer.

    Args:
        volume: Volume level from 0-100
        control: ALSA mixer control name.  When ``None`` (the default) the
        control is auto-detected via :func:`detect_volume_control`.
    """
    if control is None:
        control = detect_volume_control()
        if control is None:
            logger.warning(
                "Could not determine ALSA volume control; skipping set_volume"
            )
            return
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
