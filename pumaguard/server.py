"""
Pumaguard server watches folders for new images and returns the probability
that the new images show pumas.
"""

# pyright: reportImportCycles=false
import argparse
import logging
import os
import random
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import (
    Path,
)

from PIL import (
    Image,
)

from pumaguard import (
    __version__,
)
from pumaguard.lock_manager import (
    acquire_lock,
)
from pumaguard.presets import (
    Settings,
)
from pumaguard.shelly_control import (
    set_shelly_switch,
)
from pumaguard.sound import (
    playsound,
)
from pumaguard.utils import (
    cache_model_two_stage,
    classify_image_two_stage,
)
from pumaguard.web_ui import (
    PlugInfo,
    WebUI,
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

    def __init__(
        self, folder: str, method: str, presets: Settings, webui: WebUI
    ):
        self.folder: str = folder
        self.method: str = method
        self.presets: Settings = presets
        self.webui: WebUI = webui
        self._stop_event: threading.Event = threading.Event()
        self._thread: threading.Thread | None = None
        self._monitor_thread: threading.Thread | None = None

    def start(self):
        """
        Start watching the folder, with monitoring and auto-restart.
        """
        self._stop_event.clear()
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning(
                "Monitor thread already running for %s", self.folder
            )
            return
        self._monitor_thread = threading.Thread(
            target=self._monitor_observer, name=f"Monitor-{self.folder}"
        )
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

    def _monitor_observer(self):
        """
        Monitor the observer thread, restart if it crashes.
        """
        while not self._stop_event.is_set():
            self._thread = threading.Thread(
                target=self._observe, name=f"Observer-{self.folder}"
            )
            self._thread.daemon = True
            try:
                self._thread.start()
                self._thread.join()
            except (RuntimeError, threading.ThreadError, TypeError) as exc:
                logger.warning(
                    "FolderObserver thread crashed for %s: %s",
                    self.folder,
                    exc,
                )
            if self._stop_event.is_set():
                break
            logger.warning(
                "FolderObserver thread for %s exited unexpectedly. "
                + "Restarting...",
                self.folder,
            )
            time.sleep(1)

    def stop(self):
        """
        Stop watching the folder and monitoring thread.
        """
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)

    def _get_time(self) -> float:
        """
        Get the current time.
        """
        return time.time()

    def _sleep(self, duration: float):
        """
        Sleep a little.
        """
        time.sleep(duration)

    def _wait_for_file_stability(
        self, filepath: str, timeout: int = 10, interval: float = 0.5
    ) -> bool:
        """
        Wait until the file is no longer open by any process.

        Arguments:
            filepath -- The path of the file to check.
            timeout -- Maximum time to wait for stability (in seconds).
            interval -- Time interval between checks (in seconds).
        """
        logger.info("Making sure %s is readable", filepath)
        if timeout < 1:
            raise ValueError("timeout needs to be greater than 0")
        start_time = self._get_time()
        while self._get_time() - start_time < timeout:
            try:
                logger.debug("Attempting to open image")
                with Image.open(filepath) as img:
                    img.verify()
                logger.debug("Image is loadable")
                return True
            except FileNotFoundError:
                logger.error("Could not find file %s", filepath)
                raise
            except OSError as e:
                logger.debug("Image not completely uploaded: %s", e)
                self._sleep(interval)
                continue
            except ModuleNotFoundError as e:
                logger.debug("Missing module: %s", e)
                self._sleep(interval)
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
        cache_model_two_stage(
            yolo_model_filename=self.presets.yolo_model_filename,
            classifier_model_filename=self.presets.classifier_model_filename,
            print_progress=self.presets.print_download_progress,
        )
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
                        if self.presets.file_stabilization_extra_wait > 0:
                            logger.debug(
                                "Waiting an extra %.2f seconds",
                                self.presets.file_stabilization_extra_wait,
                            )
                            time.sleep(
                                self.presets.file_stabilization_extra_wait
                            )
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
                        if self.presets.file_stabilization_extra_wait > 0:
                            logger.debug(
                                "Waiting an extra %.2f seconds",
                                self.presets.file_stabilization_extra_wait,
                            )
                            time.sleep(
                                self.presets.file_stabilization_extra_wait
                            )
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
        me = threading.current_thread()
        logger.debug("Acquiring classification lock (%s)", me.name)
        lock = acquire_lock()
        logger.debug("Acquired lock after %d seconds", lock.time_waited())
        if lock.time_waited() > 1 * 60:
            logger.info(
                "Could not acquire lock in time, skipping classification"
            )
            lock.release()
            return
        logger.debug("Classifying: %s", filepath)
        prediction = classify_image_two_stage(
            presets=self.presets,
            image_path=filepath,
            intermediate_dir=self.presets.intermediate_dir,
        )
        logger.info("Chance of puma in %s: %.2f%%", filepath, prediction * 100)
        is_puma = prediction > self.presets.puma_threshold
        if is_puma:
            logger.info("Puma detected in %s", filepath)
            if self.presets.play_sound:
                # Turn on automatic plugs before playing sound
                self._turn_on_automatic_plugs()

                # Randomly select one sound from the list
                sound_file = random.choice(self.presets.deterrent_sound_files)
                sound_file_path = os.path.join(
                    self.presets.sound_path, sound_file
                )
                logger.info("Playing sound: %s", sound_file)
                playsound(sound_file_path, self.presets.volume)

                # Turn off automatic plugs after sound finishes
                self._turn_off_automatic_plugs()
        # Move original file into classification folder
        try:
            dest_root = (
                self.presets.classified_puma_dir
                if is_puma
                else self.presets.classified_other_dir
            )
            Path(dest_root).mkdir(parents=True, exist_ok=True)
            dest_path = Path(dest_root) / Path(filepath).name
            shutil.move(filepath, dest_path)
            logger.info(
                "Moved %s to classification folder %s", filepath, dest_path
            )
            # Notify SSE clients that a new image is available
            if self.webui.image_notification_callback is not None:
                self.webui.image_notification_callback(
                    "image_added",
                    {
                        "path": str(dest_path),
                        "folder": dest_root,
                    },
                )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Failed to move %s into classification folder: %s",
                filepath,
                exc,
            )
        # Move viz bounding-box image into the appropriate split folder
        viz_filename = Path(filepath).stem + "_viz.jpg"
        viz_src = Path(self.presets.intermediate_dir) / viz_filename
        if viz_src.exists():
            viz_dest_root = (
                self.presets.intermediate_puma_dir
                if is_puma
                else self.presets.intermediate_other_dir
            )
            try:
                Path(viz_dest_root).mkdir(parents=True, exist_ok=True)
                viz_dest = Path(viz_dest_root) / viz_filename
                shutil.move(str(viz_src), viz_dest)
                logger.info("Moved viz image %s to %s", viz_src, viz_dest)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Failed to move viz image %s: %s", viz_src, exc)
        else:
            logger.debug("No viz image found at %s, skipping move", viz_src)
        lock.release()
        logger.debug("Exiting (%s)", me.name)

    def _turn_on_automatic_plugs(self):
        """
        Turn on all plugs that are set to automatic mode.
        """
        automatic_plugs = [
            plug
            for plug in self.webui.plugs.values()
            if plug.get("mode") == "automatic"
            and plug.get("status") == "connected"
        ]

        if not automatic_plugs:
            logger.debug("No automatic plugs to turn on")
            return

        logger.info("Turning on %d automatic plug(s)", len(automatic_plugs))
        for plug in automatic_plugs:
            self._control_plug_switch(plug, True)

    def _turn_off_automatic_plugs(self):
        """
        Turn off all plugs that are set to automatic mode.
        """
        automatic_plugs = [
            plug
            for plug in self.webui.plugs.values()
            if plug.get("mode") == "automatic"
            and plug.get("status") == "connected"
        ]

        if not automatic_plugs:
            logger.debug("No automatic plugs to turn off")
            return

        logger.info("Turning off %d automatic plug(s)", len(automatic_plugs))
        for plug in automatic_plugs:
            self._control_plug_switch(plug, False)

    def _control_plug_switch(self, plug: PlugInfo, on_state: bool):
        """
        Control a Shelly plug switch.

        Arguments:
            plug -- The plug information dictionary
            on_state -- True to turn on, False to turn off
        """
        ip_address = plug.get("ip_address")
        hostname = plug.get("hostname", "unknown")

        # Use shared Shelly control function
        set_shelly_switch(ip_address, on_state, hostname)


class FolderManager:
    """
    FolderManager manages the folders to observe.
    """

    def __init__(self, presets: Settings, webui: WebUI):
        self.presets: Settings = presets
        self.webui: WebUI = webui
        self.observers: list[FolderObserver] = []

    def register_folder(self, folder: str, method: str, start: bool = True):
        """
        Register a new folder for observation.

        Arguments:
            folder -- The path of the folder to watch.
            method -- The watch method to use (inotify or os).
            start -- Whether to start watching immediately (default: True).
        """
        observer = FolderObserver(folder, method, self.presets, self.webui)
        self.observers.append(observer)
        logger.info("registered %s", folder)
        if start:
            observer.start()
            logger.info("started watching %s", folder)

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


def main(options: argparse.Namespace, presets: Settings):
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

    logger.debug("Starting web UI")
    webui = WebUI(
        presets=presets,
        host="0.0.0.0",
        folder_manager=None,  # Will be set after manager is created
        watch_method=options.watch_method,
    )
    webui.start()

    logger.debug("Getting folder manager")
    manager = FolderManager(presets, webui)

    # Update webui with the manager
    webui.folder_manager = manager

    # Determine folders to watch: user-specified or default
    if options.FOLDER and len(options.FOLDER) > 0:
        folders_to_watch = list(options.FOLDER)
    else:
        folders_to_watch = [presets.default_watch_dir]
        logger.info(
            "No folders specified, using default watch directory: %s",
            presets.default_watch_dir,
        )

    # Ensure default exists if used
    for f in folders_to_watch:
        try:
            Path(f).mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover
            logger.error("Could not create watch folder %s: %s", f, exc)

    for folder in folders_to_watch:
        manager.register_folder(folder, options.watch_method, start=False)
        webui.add_image_directory(folder)
        logger.info("Watching folder: %s", folder)

    # Also expose classified result folders in the UI (browse-only)
    try:
        Path(presets.classified_puma_dir).mkdir(parents=True, exist_ok=True)
        Path(presets.classified_other_dir).mkdir(parents=True, exist_ok=True)
        Path(presets.intermediate_dir).mkdir(parents=True, exist_ok=True)
        Path(presets.intermediate_puma_dir).mkdir(parents=True, exist_ok=True)
        Path(presets.intermediate_other_dir).mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover
        logger.error("Could not ensure classified folders exist: %s", exc)

    webui.add_classification_directory(presets.classified_puma_dir)
    webui.add_classification_directory(presets.classified_other_dir)
    webui.add_classification_directory(presets.intermediate_puma_dir)
    webui.add_classification_directory(presets.intermediate_other_dir)
    logger.info(
        "Classification browsing enabled for: %s, %s; "
        "intermediate-puma: %s, intermediate-other: %s",
        presets.classified_puma_dir,
        presets.classified_other_dir,
        presets.intermediate_puma_dir,
        presets.intermediate_other_dir,
    )

    manager.start_all()

    lock = acquire_lock()
    cache_model_two_stage(
        yolo_model_filename=presets.yolo_model_filename,
        classifier_model_filename=presets.classifier_model_filename,
    )
    lock.release()

    def handle_termination(signum, frame):  # pylint: disable=unused-argument
        logger.info("Received termination signal (%d). Stopping...", signum)
        manager.stop_all()
        logger.info("Stopped watching folders.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_termination)
    signal.signal(signal.SIGINT, handle_termination)

    logger.info("Pumaguard version %s started", __version__)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_all()
        webui.stop()
        logger.info("Stopped watching folders.")
