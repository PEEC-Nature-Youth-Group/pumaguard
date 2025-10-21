"""
Pumaguard server watches folders for new images and returns the probability
that the new images show pumas.
"""

import argparse
import logging
import os
import signal
import subprocess
import sys
import threading
import time

from pumaguard.lock_manager import (
    acquire_lock,
)
from pumaguard.presets import (
    Preset,
)
from pumaguard.sound import (
    playsound,
)
from pumaguard.utils import (
    cache_model_two_stage,
    classify_image_two_stage,
)

logger = logging.getLogger("PumaGuard")


def configure_subparser(parser: argparse.ArgumentParser):
    """
    Parses the command line arguments provided to the script.
    """
    parser.add_argument(
        "FOLDER",
        help="The folder(s) to watch. Can be used multiple times.",
        nargs="*",
    )
    parser.add_argument(
        "--sound-path",
        help="Where the sound files are stored (default = %(default)s)",
        type=str,
        default=os.getenv(
            "PUMAGUARD_SOUND_PATH",
            default=os.path.join(
                os.path.dirname(__file__), "../pumaguard-sounds"
            ),
        ),
    )
    parser.add_argument(
        "--no-play-sound",
        help="Do not play a sound when detecting a Puma",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--no-download-progress",
        help="Do not print out model download progress",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--watch-method",
        help='''What implementation (method) to use for watching
        the folder. Linux on baremetal supports both methods. Linux
        in WSL supports inotify on folders using ext4 but only os
        on folders that are mounted from the Windows host. Defaults
        to "%(default)s"''',
        choices=["inotify", "os"],
        default="os",
    )


class FolderObserver:
    """
    FolderObserver watches a folder for new files.
    """

    def __init__(self, folder: str, method: str, presets: Preset):
        self.folder = folder
        self.method = method
        self.presets = presets
        # self.model = model_factory(presets).model
        self._stop_event = threading.Event()

    def start(self):
        """
        start watching the folder.
        """
        self._stop_event.clear()
        threading.Thread(target=self._observe).start()

    def stop(self):
        """
        Stop watching the folder.
        """
        self._stop_event.set()

    def _wait_for_file_stability(
        self, filepath: str, timeout: int = 30, interval: float = 0.5
    ) -> bool:
        """
        Wait until the file is no longer open by any process.

        Arguments:
            filepath -- The path of the file to check.
            timeout -- Maximum time to wait for stability (in seconds).
            interval -- Time interval between checks (in seconds).
        """
        logger.info("Making sure %s is closed", filepath)
        if timeout < 1:
            raise ValueError("timeout needs to be greater than 0")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["lsof", "-F", "p", "--", filepath],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=min(1, timeout),
                    text=True,
                    check=False,
                )
                # lsof returns non-zero if the file is not open
                if result.returncode != 0:
                    return True
                pid = result.stdout.strip()
                logger.debug("%s is still open by PID %s", filepath, pid)
                time.sleep(interval)
            except FileNotFoundError:
                time.sleep(interval)
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Could not get exclusive access to file %s", filepath
                )
        logger.warning(
            "File %s is still open after %d seconds", filepath, timeout
        )
        return False

    def _observe(self):
        """
        Observe whether a new file is created in the folder.
        """
        logger.info("Starting new observer, method = %s", self.method)
        lock = acquire_lock()
        logger.debug("Caching models")
        cache_model_two_stage(self.presets.print_download_progress)
        lock.release()
        logger.debug("Models are cached")
        if self.method == "inotify":
            with subprocess.Popen(
                [
                    "inotifywait",
                    "--monitor",
                    "--event",
                    "create",
                    "--format",
                    "%w%f",
                    self.folder,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                text=True,
            ) as process:
                logger.info("New observer started")
                if process.stdout is None:
                    raise ValueError("Failed to initialize process.stdout")

                for line in process.stdout:
                    if self._stop_event.is_set():
                        process.terminate()
                        break
                    filepath = line.strip()
                    logger.info("New file detected: %s", filepath)
                    if self._wait_for_file_stability(filepath):
                        threading.Thread(
                            target=self._handle_new_file,
                            args=(filepath,),
                        ).start()
                    else:
                        logger.warning(
                            "File %s not closed, ignoring", filepath
                        )
        elif self.method == "os":
            known_files = set(os.listdir(self.folder))
            logger.info("New observer started")
            while not self._stop_event.is_set():
                current_files = set(os.listdir(self.folder))
                new_files = current_files - known_files
                for new_file in new_files:
                    filepath = os.path.join(self.folder, new_file)
                    logger.info("New file detected: %s", filepath)
                    if self._wait_for_file_stability(filepath):
                        threading.Thread(
                            target=self._handle_new_file,
                            args=(filepath,),
                        ).start()
                    else:
                        logger.warning(
                            "File %s not closed, ignoring", filepath
                        )
                known_files = current_files
                time.sleep(1)
        else:
            raise ValueError("FIXME: This method is not implemented")

    def _handle_new_file(self, filepath: str):
        """
        Handle the new file detected in the folder.

        Arguments:
            filepath -- The path of the new file.
        """
        logger.debug("Acquiring classification lock")
        lock = acquire_lock()
        logger.debug("Acquired lock after %d seconds", lock.time_waited())
        if lock.time_waited() > 10 * 60:
            logger.info(
                "Could not acquire lock in time, skipping classification"
            )
            lock.release()
            return
        logger.debug("Classifying: %s", filepath)
        prediction = classify_image_two_stage(self.presets, filepath)
        logger.info("Chance of puma in %s: %.2f%%", filepath, prediction * 100)
        if prediction > 0.5:
            logger.info("Puma detected in %s", filepath)
            if self.presets.play_sound:
                sound_file_path = os.path.join(
                    self.presets.sound_path, "cougar_call.mp3"
                )
                playsound(sound_file_path)
        lock.release()


class FolderManager:
    """
    FolderManager manages the folders to observe.
    """

    def __init__(self, presets: Preset):
        self.presets = presets
        self.observers: list[FolderObserver] = []

    def register_folder(self, folder: str, method: str):
        """
        Register a new folder for observation.

        Arguments:
            folder -- The path of the folder to watch.
        """
        observer = FolderObserver(folder, method, self.presets)
        self.observers.append(observer)
        logger.info("registered %s", folder)

    def start_all(self):
        """
        Start watching all registered folders.
        """
        logger.info("starting to watch folders")
        for observer in self.observers:
            observer.start()

    def stop_all(self):
        """
        Stop watching all registered folders.
        """
        logger.info("stopping to watch all folders")
        for observer in self.observers:
            observer.stop()


def main(options: argparse.Namespace, presets: Preset):
    """
    Main entry point.
    """

    sound_path = (
        options.sound_path
        if hasattr(options, "sound_path") and options.sound_path
        else os.getenv("PUMAGUARD_SOUND_PATH", default=None)
    )
    if sound_path is not None:
        logger.debug("setting sound path to %s", sound_path)
        presets.sound_path = sound_path

    if options.no_play_sound:
        logger.debug("Will not play sounds")
        presets.play_sound = False

    if options.no_download_progress:
        logger.debug("Will not print out download progress")
        presets.print_download_progress = False

    logger.debug("getting folder manager")
    manager = FolderManager(presets)
    for folder in options.FOLDER:
        manager.register_folder(folder, options.watch_method)

    manager.start_all()

    lock = acquire_lock()
    cache_model_two_stage()
    lock.release()

    def handle_termination(signum, frame):  # pylint: disable=unused-argument
        logger.info("Received termination signal (%d). Stopping...", signum)
        manager.stop_all()
        logger.info("Stopped watching folders.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_termination)
    signal.signal(signal.SIGINT, handle_termination)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_all()
        logger.info("Stopped watching folders.")
