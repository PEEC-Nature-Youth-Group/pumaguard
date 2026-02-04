"""
The presets for each model.
"""

import copy
import logging
import os
from pathlib import (
    Path,
)
from typing import (
    Tuple,
)

import tensorflow as tf  # type: ignore
import yaml
from packaging import (
    version,
)

logger = logging.getLogger("PumaGuard")


def get_xdg_config_home() -> Path:
    """
    Get the XDG config home directory according to XDG Base Directory spec.

    Returns:
        Path to XDG_CONFIG_HOME (defaults to ~/.config if not set)
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config)
    return Path.home() / ".config"


def get_xdg_data_home() -> Path:
    """
    Get the XDG data home directory.

    Returns:
        Path to XDG_DATA_HOME (defaults to ~/.local/share if not set)
    """
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data)
    return Path.home() / ".local" / "share"


def get_xdg_cache_home() -> Path:
    """
    Get the XDG cache home directory.

    Returns:
        Path to XDG_CACHE_HOME (defaults to ~/.cache if not set)
    """
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache)
    return Path.home() / ".cache"


def get_default_settings_file() -> str:
    """
    Get the default settings file path using XDG standards.

    Checks in order:
    1. If running as snap: SNAP_USER_DATA/pumaguard/settings.yaml
    2. XDG_CONFIG_HOME/pumaguard/settings.yaml
    (e.g., ~/.config/pumaguard/settings.yaml)
    3. Current directory pumaguard-settings.yaml
    (for backwards compatibility)

    Returns:
        Path to the settings file
    """
    # Check if running as snap (strict confinement requires snap path)
    snap_user_data = os.environ.get("SNAP_USER_DATA")
    if snap_user_data:
        snap_config_dir = Path(snap_user_data) / "pumaguard"
        snap_settings_file = snap_config_dir / "pumaguard-settings.yaml"

        # If snap settings file exists, use it
        if snap_settings_file.exists():
            return str(snap_settings_file)

        # Create snap config directory if needed and return path
        snap_config_dir.mkdir(parents=True, exist_ok=True)
        return str(snap_settings_file)

    # XDG compliant location
    xdg_config_dir = get_xdg_config_home() / "pumaguard"
    xdg_settings_file = xdg_config_dir / "pumaguard-settings.yaml"

    # If the XDG file exists, use it
    if xdg_settings_file.exists():
        return str(xdg_settings_file)

    xdg_config_dir.mkdir(parents=True, exist_ok=True)
    return str(xdg_settings_file)


class PresetError(Exception):
    """
    Docstring for PresetError
    """


# pylint: disable=too-many-public-methods
class Preset:
    """
    Base class for Presets
    """

    _alpha: float = 0
    _base_output_directory: str = ""
    _model_file: str = ""

    def __init__(self):
        self.settings_file = get_default_settings_file()
        self.yolo_min_size = 0.02
        self.yolo_conf_thresh = 0.25
        self.yolo_max_dets = 2
        self.yolo_model_filename = "yolov8s_101425.pt"
        self.classifier_model_filename = "colorbw_111325.h5"
        self.alpha = 1e-5
        self.base_output_directory = os.path.join(
            os.path.dirname(__file__), "../pumaguard-models"
        )
        self.sound_path = os.path.join(
            os.path.dirname(__file__), "../pumaguard-sounds"
        )
        self.deterrent_sound_file = "deterrent_puma.mp3"
        self.verification_path = "data/stable/stable_test"
        self.batch_size = 16
        self.notebook_number = 1
        self.color_mode = "rgb"
        self.file_stabilization_extra_wait = 1
        self.epochs = 300
        self.image_dimensions: tuple[int, int] = (128, 128)
        self.lion_directories: list[str] = []
        self.validation_lion_directories: list[str] = []
        self.load_history_from_file = False
        self.load_model_from_file = False
        self.model_function_name = "xception"
        self.model_version = "undefined"
        self.play_sound = True
        self.volume = 80  # Volume level 0-100 for ALSA playback
        self.print_download_progress = True
        self.cameras: list[dict[str, str]] = []  # List of detected cameras
        self.plugs: list[dict[str, str]] = []  # List of detected plugs
        self.no_lion_directories: list[str] = []
        self.validation_no_lion_directories: list[str] = []
        self.with_augmentation = False

        # Camera heartbeat monitoring settings
        self.camera_heartbeat_enabled = True
        self.camera_heartbeat_interval = 60  # Check interval in seconds
        self.camera_heartbeat_method = "tcp"  # "icmp", "tcp", or "both"
        self.camera_heartbeat_tcp_port = 80  # TCP port to check
        self.camera_heartbeat_tcp_timeout = 3  # TCP timeout in seconds
        self.camera_heartbeat_icmp_timeout = 2  # ICMP timeout in seconds
        if version.parse(tf.__version__) < version.parse("2.17"):
            self.tf_compat = "2.15"
        else:
            self.tf_compat = "2.17"

        # Classification product directories (XDG data location by default)
        data_root = get_xdg_data_home() / "pumaguard"
        self.classification_root_dir = str(data_root / "classified")
        self.classified_puma_dir = str(
            Path(self.classification_root_dir) / "puma"
        )
        self.classified_other_dir = str(
            Path(self.classification_root_dir) / "other"
        )
        self.intermediate_dir = str(
            Path(self.classification_root_dir) / "intermediate"
        )
        # Default watch directory (incoming images)
        self.default_watch_dir = str(data_root / "watch")

        # Ensure directories exist
        for d in [
            self.classification_root_dir,
            self.classified_puma_dir,
            self.classified_other_dir,
            self.intermediate_dir,
            self.default_watch_dir,
        ]:
            try:
                Path(d).mkdir(parents=True, exist_ok=True)
            except OSError as exc:  # pragma: no cover (rare failure)
                logger.error("Could not create directory %s: %s", d, exc)

    def load(self, filename: str):
        """
        Load settings from YAML file.
        """
        logger.info("loading settings from %s", filename)
        try:
            with open(filename, encoding="utf-8") as fd:
                settings = yaml.safe_load(fd)
        except FileNotFoundError:
            logger.error(
                "Could not open settings (%s), using defaults", filename
            )
            return
        except yaml.constructor.ConstructorError as e:
            error_msg = str(e)
            if "python/tuple" in error_msg:
                raise PresetError(
                    f"{error_msg}\n\n"
                    "Your settings file contains Python-specific tuple "
                    "formatting that is no longer supported.\n"
                    f"Please update {filename} to use YAML list syntax.\n"
                    "For example, change:\n"
                    "  image-dimensions: !!python/tuple [512, 512]\n"
                    "to:\n"
                    "  image-dimensions:\n"
                    "    - 512\n"
                    "    - 512\n"
                    "Or delete the file to use defaults."
                ) from e
            raise PresetError(error_msg) from e

        self.yolo_min_size = settings.get("YOLO-min-size", 0.02)
        self.yolo_conf_thresh = settings.get("YOLO-conf-thresh", 0.25)
        self.yolo_max_dets = settings.get("YOLO-max-dets", 12)
        self.yolo_model_filename = settings.get(
            "YOLO-model-filename", "yolov8s_101425.pt"
        )
        self.classifier_model_filename = settings.get(
            "classifier-model-filename", "colorbw_111325.h5"
        )
        self.sound_path = settings.get(
            "sound-path", os.path.dirname(__file__) + "../pumaguard-sounds"
        )
        self.deterrent_sound_file = settings.get(
            "deterrent-sound-file", "cougar_call.mp3"
        )
        self.volume = settings.get("volume", 80)
        self.notebook_number = settings.get("notebook", 1)
        self.epochs = settings.get("epochs", 1)
        dimensions = settings.get("image-dimensions", [0, 0])
        if (
            not isinstance(dimensions, list)
            or len(dimensions) != 2
            or not all(isinstance(d, int) for d in dimensions)
        ):
            raise ValueError(
                "expected image-dimensions to be a list of two integers"
            )
        self.image_dimensions = tuple(dimensions)
        self.model_version = settings.get("model-version", "undefined")
        self.model_function_name = settings.get("model-function", "undefined")
        self.base_output_directory = settings.get(
            "base-output-directory", "undefined"
        )
        self.verification_path = settings.get(
            "verification-path", "data/stable/stable_test"
        )
        lions = settings.get("lion-directories", ["undefined"])
        if not isinstance(lions, list) or not all(
            isinstance(p, str) for p in lions
        ):
            raise ValueError("expected lion-directories to be a list of paths")
        self.lion_directories = lions
        no_lions = settings.get("no-lion-directories", ["undefined"])
        if not isinstance(no_lions, list) or not all(
            isinstance(p, str) for p in no_lions
        ):
            raise ValueError(
                "expected no-lion-directories to be a list of paths"
            )
        self.no_lion_directories = no_lions
        validation_lions = settings.get("validation-lion-directories", [])
        if not isinstance(validation_lions, list) or not all(
            isinstance(p, str) for p in validation_lions
        ):
            raise ValueError(
                "expected validation-lion-directories to be a list of paths"
            )
        self.validation_lion_directories = validation_lions
        validation_no_lions = settings.get(
            "validation-no-lion-directories", []
        )
        if not isinstance(validation_no_lions, list) or not all(
            isinstance(p, str) for p in validation_no_lions
        ):
            raise ValueError(
                "expected validation-no-lion-directories to be a list of paths"
            )
        self.validation_no_lion_directories = validation_no_lions
        self.with_augmentation = settings.get("with-augmentation", False)
        self.batch_size = settings.get("batch-size", 1)
        self.alpha = float(settings.get("alpha", 1e-5))
        self.color_mode = settings.get("color-mode", "rgb")
        self.file_stabilization_extra_wait = settings.get(
            "file-stabilization-extra-wait", 0
        )
        self.play_sound = settings.get("play-sound", True)
        self.volume = settings.get("volume", 80)
        self.print_download_progress = settings.get(
            "print-download-progress", True
        )
        self.cameras = settings.get("cameras", [])
        self.plugs = settings.get("plugs", [])

    def save(self):
        """
        Write presets to standard output.
        """
        yaml.dump(self)

    def _relative_paths(self, base: str, paths: list[str]) -> list[str]:
        """
        The directories relative to a base path.
        """
        return [os.path.relpath(path, start=base) for path in paths]

    def __iter__(self):
        """
        Serialize this class.
        """
        # pylint: disable=line-too-long
        yield from {
            "YOLO-min-size": self.yolo_min_size,
            "YOLO-conf-thresh": self.yolo_conf_thresh,
            "YOLO-max-dets": self.yolo_max_dets,
            "YOLO-model-filename": self.yolo_model_filename,
            "classifier-model-filename": self.classifier_model_filename,
            "sound-path": self.sound_path,
            "deterrent-sound-file": self.deterrent_sound_file,
            "play-sound": self.play_sound,
            "volume": self.volume,
            "alpha": self.alpha,
            "batch-size": self.batch_size,
            "color-mode": self.color_mode,
            "file-stabilization-extra-wait": self.file_stabilization_extra_wait,
            "epochs": self.epochs,
            "image-dimensions": list(self.image_dimensions),
            "lion-directories": self.lion_directories,
            "validation-lion-directories": self.validation_lion_directories,
            "model-function": self.model_function_name,
            "model-version": self.model_version,
            "no-lion-directories": self.no_lion_directories,
            "validation-no-lion-directories": self.validation_no_lion_directories,
            "notebook": self.notebook_number,
            "verification-path": self.verification_path,
            "with-augmentation": self.with_augmentation,
            "cameras": self.cameras,
            "plugs": self.plugs,
        }.items()

    def __str__(self):
        """
        Serialize this class.
        """
        return yaml.dump(dict(self), indent=2)

    @property
    def yolo_min_size(self) -> float:
        """
        Get the YOLO min-size.
        """
        return self._yolo_min_size

    @yolo_min_size.setter
    def yolo_min_size(self, yolo_min_size: float):
        """
        Set the YOLO min-size.
        """
        if not isinstance(yolo_min_size, float):
            raise TypeError(
                "yolo_min_size needs to be a floating point number"
            )
        if yolo_min_size <= 0 or yolo_min_size > 1:
            raise ValueError("yolo_min_size needs to be between (0, 1]")
        self._yolo_min_size = yolo_min_size

    @property
    def yolo_conf_thresh(self) -> float:
        """
        Get the YOLO conf-thresh.
        """
        return self._yolo_conf_thresh

    @yolo_conf_thresh.setter
    def yolo_conf_thresh(self, yolo_conf_thresh: float):
        """
        Set the YOLO conf-thresh.
        """
        if not isinstance(yolo_conf_thresh, float):
            raise TypeError(
                "yolo_conf_thresh needs to be a floating point number"
            )
        if yolo_conf_thresh <= 0 or yolo_conf_thresh > 1:
            raise ValueError("yolo_conf_thresh needs to be between (0, 1]")
        self._yolo_conf_thresh = yolo_conf_thresh

    @property
    def yolo_max_dets(self) -> int:
        """
        Get the YOLO max-dets.
        """
        return self._yolo_max_dets

    @yolo_max_dets.setter
    def yolo_max_dets(self, yolo_max_dets: int):
        """
        Set the YOLO max-dets.
        """
        if not isinstance(yolo_max_dets, int):
            raise TypeError("yolo_max_dets needs to be a integer")
        if yolo_max_dets <= 0 or yolo_max_dets > 20:
            raise ValueError("yolo_max_dets needs to be between (0, 20]")
        self._yolo_max_dets = yolo_max_dets

    @property
    def yolo_model_filename(self) -> str:
        """
        Get the YOLO model filename.
        """
        return self._yolo_model_filename

    @yolo_model_filename.setter
    def yolo_model_filename(self, yolo_model_filename: str):
        """
        Set the YOLO model filename.
        """
        if not isinstance(yolo_model_filename, str):
            raise TypeError("yolo_model_filename needs to be a string")
        self._yolo_model_filename = yolo_model_filename

    @property
    def classifier_model_filename(self) -> str:
        """
        Get the classifier model filename.
        """
        return self._classifier_model_filename

    @classifier_model_filename.setter
    def classifier_model_filename(self, classifier_model_filename: str):
        """
        Set the classifier model filename.
        """
        if not isinstance(classifier_model_filename, str):
            raise TypeError("classifier_model_filename needs to be a string")
        self._classifier_model_filename = classifier_model_filename

    @property
    def alpha(self) -> float:
        """
        Get the stepsize alpha.
        """
        return self._alpha

    @alpha.setter
    def alpha(self, alpha: float):
        """
        Set the stepsize alpha.
        """
        if not isinstance(alpha, float):
            raise TypeError("alpha needs to be a floating point number")
        if alpha <= 0:
            raise ValueError("the stepsize needs to be positive")
        self._alpha = alpha

    @property
    def base_output_directory(self) -> str:
        """
        Get the base_output_directory.
        """
        return self._base_output_directory

    @base_output_directory.setter
    def base_output_directory(self, path: str):
        """
        Set the base_output_directory.
        """
        self._base_output_directory = path

    @property
    def verification_path(self) -> str:
        """
        Get the verification path.
        """
        return self._verification_path

    @verification_path.setter
    def verification_path(self, path: str):
        """
        Set the verification path.
        """
        self._verification_path = path

    @property
    def notebook_number(self) -> int:
        """
        Get notebook number.
        """
        return (
            self._notebook_number if hasattr(self, "_notebook_number") else 0
        )

    @notebook_number.setter
    def notebook_number(self, notebook: int):
        """
        Set the notebook number.
        """
        if notebook < 1:
            raise ValueError(
                f"notebook can not be zero or negative ({notebook})"
            )
        self._notebook_number = notebook

    @property
    def file_stabilization_extra_wait(self) -> float:
        """
        Get extra wait.
        """
        return (
            self._file_stabilization_extra_wait
            if hasattr(self, "_file_stabilization_extra_wait")
            else 0
        )

    @file_stabilization_extra_wait.setter
    def file_stabilization_extra_wait(self, extra_wait: float):
        """
        Set the extra wait.
        """
        if extra_wait < 0:
            raise ValueError(f"extra_wait can not be negative ({extra_wait})")
        self._file_stabilization_extra_wait = extra_wait

    @property
    def model_version(self) -> str:
        """
        Get the model version name.
        """
        return self._model_version

    @model_version.setter
    def model_version(self, model_version: str):
        """
        Set the model version name.
        """
        self._model_version = model_version

    @property
    def sound_path(self):
        """
        Get the sound path.
        """
        return self._sound_path

    @sound_path.setter
    def sound_path(self, sound_path: str):
        """
        Set the sound path.
        """
        self._sound_path = sound_path

    @property
    def deterrent_sound_file(self):
        """
        Get the deterrent sound file.
        """
        return self._deterrent_sound_file

    @deterrent_sound_file.setter
    def deterrent_sound_file(self, sound_file: str):
        """
        Set the deterrent sound file.
        """
        self._deterrent_sound_file = sound_file

    @property
    def model_file(self):
        """
        Get the location of the model file.
        """
        if self._model_file != "":
            return self._model_file
        return os.path.realpath(
            f"{self.base_output_directory}/"
            f"model_weights_{self.notebook_number}"
            f"_{self.model_version}"
            f"_tf{self.tf_compat}"
            f"_{self.image_dimensions[0]}"
            f"_{self.image_dimensions[1]}"
            ".keras"
        )

    @model_file.setter
    def model_file(self, filename: str):
        """
        Set the location of the model file.
        """
        self._model_file = filename

    @property
    def history_file(self):
        """
        Get the history file.
        """
        return os.path.realpath(
            f"{self.base_output_directory}/"
            f"model_history_{self.notebook_number}"
            f"_{self.model_version}"
            f"_tf{self.tf_compat}"
            f"_{self.image_dimensions[0]}"
            f"_{self.image_dimensions[1]}"
            ".pickle"
        )

    @property
    def settings_file(self) -> str:
        """
        Get the settings file.
        """
        return self._settings_file

    @settings_file.setter
    def settings_file(self, filename: str):
        """
        Set the settings file.
        """
        self._settings_file = filename

    @property
    def color_mode(self) -> str:
        """
        Get the color_mode.
        """
        return self._color_mode

    @color_mode.setter
    def color_mode(self, mode: str):
        """
        Set the color_mode.
        """
        if not isinstance(mode, str):
            raise TypeError("mode must be a string")
        if mode not in ["rgb", "grayscale"]:
            raise ValueError("color_mode must be either 'rgb' or 'grayscale'")
        self._color_mode = mode
        if mode == "grayscale":
            self._number_color_channels = 1
        elif mode == "rgb":
            self._number_color_channels = 3

    @property
    def number_color_channels(self) -> int:
        """
        The number of color channels.
        """
        return self._number_color_channels

    @number_color_channels.setter
    def number_color_channels(self, channels: int):
        """
        Set the number of color channels.
        """
        if channels not in [1, 3]:
            raise ValueError(f"illegal number of color channels ({channels})")
        self._number_color_channels = channels
        if channels == 1:
            self._color_mode = "grayscale"
        elif channels == 3:
            self._color_mode = "rgb"

    @property
    def image_dimensions(self) -> Tuple[int, int]:
        """
        Get the image dimensions.
        """
        return self._image_dimensions

    @image_dimensions.setter
    def image_dimensions(self, dimensions: Tuple[int, int]):
        """
        Set the image dimensions.
        """
        if not (
            isinstance(dimensions, tuple)
            and len(dimensions) == 2
            and all(isinstance(dim, int) for dim in dimensions)
        ):
            raise TypeError("image dimensions needs to be a tuple")
        if not all(x > 0 for x in dimensions):
            raise ValueError("image dimensions need to be positive")
        self._image_dimensions = copy.deepcopy(dimensions)

    @property
    def load_history_from_file(self) -> bool:
        """
        Load history from file.
        """
        return self._load_history_from_file

    @load_history_from_file.setter
    def load_history_from_file(self, load_history: bool):
        """
        Load history from file.
        """
        self._load_history_from_file = load_history

    @property
    def load_model_from_file(self) -> bool:
        """
        Load model from file.
        """
        return self._load_model_from_file

    @load_model_from_file.setter
    def load_model_from_file(self, load_model: bool):
        """
        Load model from file.
        """
        self._load_model_from_file = load_model

    @property
    def epochs(self) -> int:
        """
        The number of epochs.
        """
        return self._epochs

    @epochs.setter
    def epochs(self, epochs: int):
        """
        Set the number of epochs.
        """
        if not isinstance(epochs, int):
            raise TypeError("epochs must be int")
        if epochs < 1:
            raise ValueError("epochs needs to be a positive integer")
        self._epochs = epochs

    @property
    def lion_directories(self) -> list[str]:
        """
        The directories containing lion images.
        """
        return self._lion_directories

    @lion_directories.setter
    def lion_directories(self, lions: list[str]):
        """
        Set the lion directories.
        """
        self._lion_directories = copy.deepcopy(lions)

    @property
    def validation_lion_directories(self) -> list[str]:
        """
        The directories containing lion images for validation.
        """
        return self._validation_lion_directories

    @validation_lion_directories.setter
    def validation_lion_directories(self, lions: list[str]):
        """
        Set the lion directories for validation.
        """
        self._validation_lion_directories = copy.deepcopy(lions)

    @property
    def no_lion_directories(self) -> list[str]:
        """
        The directories containing no_lion images.
        """
        return self._no_lion_directories

    @no_lion_directories.setter
    def no_lion_directories(self, no_lions: list[str]):
        """
        Set the no_lion directories.
        """
        self._no_lion_directories = copy.deepcopy(no_lions)

    @property
    def validation_no_lion_directories(self) -> list[str]:
        """
        The directories containing no_lion images for validation.
        """
        return self._validation_no_lion_directories

    @validation_no_lion_directories.setter
    def validation_no_lion_directories(self, no_lions: list[str]):
        """
        Set the no_lion directories for validation.
        """
        self._validation_no_lion_directories = copy.deepcopy(no_lions)

    @property
    def model_function_name(self) -> str:
        """
        Get the model function name.
        """
        return self._model_function_name

    @model_function_name.setter
    def model_function_name(self, name: str):
        """
        Set the model function name.
        """
        self._model_function_name = name

    @property
    def with_augmentation(self) -> bool:
        """
        Get whether to augment training data.
        """
        return self._with_augmentation

    @with_augmentation.setter
    def with_augmentation(self, with_augmentation: bool):
        """
        Set whether to use augment training data.
        """
        self._with_augmentation = with_augmentation

    @property
    def batch_size(self) -> int:
        """
        Get the batch size.
        """
        return self._batch_size

    @batch_size.setter
    def batch_size(self, batch_size: int):
        """
        Set the batch size.
        """
        if not isinstance(batch_size, int):
            raise TypeError("batch_size must be int")
        if batch_size <= 0:
            raise ValueError("the batch-size needs to be a positive number")
        self._batch_size = batch_size

    @property
    def tf_compat(self) -> str:
        """
        Get the tensorflow compatibility version.

        Tensorflow changed their keras model file format from 2.15 to 2.17.
        Model files produced with tensorflow >= 2.15 to < 2.17 cannot be read
        with tensorflow >= 2.17. Model files therefore will be either in '2.15'
        or in '2.17' format.
        """
        return self._tf_compat

    @tf_compat.setter
    def tf_compat(self, compat: str):
        """
        Set the tensorflow compatibility version.

        This is either '2.15' or '2.17'.
        """
        if not isinstance(compat, str):
            raise TypeError("tf compat needs to be a string")
        if compat not in ["2.15", "2.17"]:
            raise ValueError("tf compat needs to be in [2.15, 2.17]")
        self._tf_compat = compat

    @property
    def play_sound(self) -> bool:
        """
        Get play-sound.
        """
        return self._play_sound

    @play_sound.setter
    def play_sound(self, play_sound: bool):
        """
        Set play-sound.
        """
        if not isinstance(play_sound, bool):
            raise TypeError("play_sound needs to be a bool")
        self._play_sound = play_sound

    @property
    def volume(self) -> int:
        """
        Get volume level (0-100).
        """
        return self._volume

    @volume.setter
    def volume(self, volume: int):
        """
        Set volume level (0-100).
        """
        if not isinstance(volume, int):
            raise TypeError("volume needs to be an int")
        if volume < 0 or volume > 100:
            raise ValueError("volume must be between 0 and 100")
        self._volume = volume
