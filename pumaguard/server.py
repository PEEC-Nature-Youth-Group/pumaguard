"""
Pumaguard server watches folders for new images and returns the probability
that the new images show pumas.
"""

import argparse
import logging
import os
import subprocess
import threading
import time

from pumaguard.model_factory import (
    model_factory,
)
from pumaguard.presets import (
    Preset,
)
from pumaguard.sound import (
    playsound,
)
from pumaguard.utils import (
    classify_image,
)

logger = logging.getLogger('PumaGuard')


def configure_subparser(parser: argparse.ArgumentParser):
    """
    Parses the command line arguments provided to the script.
    """
    parser.add_argument(
        'FOLDER',
        help='The folder(s) to watch. Can be used multiple times.',
        nargs='*',
    )
    parser.add_argument(
        '--sound-path',
        help='Where the sound files are stored (default = %(default)s)',
        type=str,
        default=os.getenv(
            'PUMAGUARD_SOUND_PATH',
            default=os.path.join(os.path.dirname(__file__),
                                 '../pumaguard-sounds')),
    )
    parser.add_argument(
        '--watch-method',
        help='''What implementation (method) to use for watching
        the folder. Linux on baremetal supports both methods. Linux
        in WSL supports inotify on folders using ext4 but only os
        on folders that are mounted from the Windows host. Defaults
        to "%(default)s"''',
        choices=['inotify', 'os'],
        default='os',
    )


class FolderObserver:
    """
    FolderObserver watches a folder for new files.
    """

    def __init__(self, folder: str, method: str, presets: Preset):
        self.folder = folder
        self.method = method
        self.presets = presets
        self.model = model_factory(presets).model
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

    def _observe(self):
        """
        Observe whether a new file is created in the folder.
        """
        if self.method == 'inotify':
            with subprocess.Popen(
                ['inotifywait', '--monitor', '--event',
                    'create', '--format', '%w%f', self.folder,],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                text=True,
            ) as process:
                if process.stdout is None:
                    raise ValueError("Failed to initialize process.stdout")

                for line in process.stdout:
                    if self._stop_event.is_set():
                        process.terminate()
                        break
                    logger.info('New file detected: %s', line.strip())
                    threading.Thread(
                        target=self._handle_new_file,
                        args=(line.strip(),),
                    ).start()
        elif self.method == 'os':
            known_files = set(os.listdir(self.folder))
            while not self._stop_event.is_set():
                current_files = set(os.listdir(self.folder))
                new_files = current_files - known_files
                for new_file in new_files:
                    full_path = os.path.join(self.folder, new_file)
                    logger.info('New file detected: %s', full_path)
                    threading.Thread(
                        target=self._handle_new_file,
                        args=(full_path,),
                    ).start()
                known_files = current_files
                time.sleep(1)
        else:
            raise ValueError('FIXME: This method is not implemented')

    def _handle_new_file(self, filepath: str):
        """
        Handle the new file detected in the folder.

        Arguments:
            filepath -- The path of the new file.
        """
        logger.debug('Classifying: %s', filepath)
        prediction = classify_image(self.presets, self.model, filepath)
        logger.info('Chance of puma in %s: %.2f%%',
                    filepath, (1 - prediction) * 100)
        if prediction < 0.5:
            logger.info('Puma detected in %s', filepath)
            sound_file_path = os.path.join(
                self.presets.sound_path, 'lion-roar-6011.mp3')
            playsound(sound_file_path)


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
        logger.info('registered %s', folder)

    def start_all(self):
        """
        Start watching all registered folders.
        """
        logger.info('starting to watch folders')
        for observer in self.observers:
            observer.start()

    def stop_all(self):
        """
        Stop watching all registered folders.
        """
        logger.info('stopping to watch all folders')
        for observer in self.observers:
            observer.stop()


def main(options: argparse.Namespace, presets: Preset):
    """
    Main entry point.
    """

    sound_path = options.sound_path if hasattr(options, 'sound_path') \
        and options.sound_path \
        else os.getenv('PUMAGUARD_SOUND_PATH', default=None)
    if sound_path is not None:
        logger.debug('setting sound path to %s', sound_path)
        presets.sound_path = sound_path

    manager = FolderManager(presets)
    for folder in options.FOLDER:
        manager.register_folder(folder, options.watch_method)

    manager.start_all()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_all()
        logger.info('Stopped watching folders.')
