"""
Test Presets class
"""

import os
import tempfile
import unittest
from pathlib import (
    Path,
)
from unittest.mock import (
    mock_open,
    patch,
)

import yaml

from pumaguard.presets import (
    Preset,
    get_default_settings_file,
)


class TestBasePreset(unittest.TestCase):
    """
    Test the base class.
    """

    def setUp(self):
        self.base_preset = Preset()

    def test_image_dimensions_default(self):
        """
        Test the default value of image dimensions.
        """
        self.assertEqual(len(self.base_preset.image_dimensions), 2)
        self.assertEqual(self.base_preset.image_dimensions, (128, 128))

    def test_image_dimensions_failure(self):
        """
        Test various failures of image dimensions.
        """
        with self.assertRaises(TypeError) as type_error:
            self.base_preset.image_dimensions = 1  # type: ignore
        self.assertEqual(
            str(type_error.exception), "image dimensions needs to be a tuple"
        )
        with self.assertRaises(ValueError) as value_error:
            self.base_preset.image_dimensions = (-1, 2)
        self.assertEqual(
            str(value_error.exception), "image dimensions need to be positive"
        )

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
notebook: 10
epochs: 2400
image-dimensions: [128, 128]
with-augmentation: True
batch-size: 2
model-function: xception
model-version: light-test
alpha: 1e-3
base-output-directory: /path/to/output
verification-path: /path/to/verification
lion-directories:
    - /path/to/lion
no-lion-directories:
    - /path/to/no_lion
""",
    )
    def test_load(self, mock_file):  # pylint: disable=unused-argument
        """
        Test loading settings from file.
        """
        self.base_preset.load("/fake/path/to/settings.yaml")
        self.assertEqual(self.base_preset.notebook_number, 10)
        self.assertEqual(self.base_preset.epochs, 2400)
        self.assertEqual(self.base_preset.image_dimensions, (128, 128))
        self.assertEqual(self.base_preset.model_version, "light-test")
        self.assertEqual(
            self.base_preset.verification_path, "/path/to/verification"
        )
        self.assertEqual(
            self.base_preset.base_output_directory, "/path/to/output"
        )
        self.assertIn("/path/to/lion", self.base_preset.lion_directories)
        self.assertIn("/path/to/no_lion", self.base_preset.no_lion_directories)
        self.assertTrue(hasattr(self.base_preset, "with_augmentation"))
        self.assertEqual(self.base_preset.batch_size, 2)
        self.assertEqual(self.base_preset.alpha, 1e-3)
        self.assertEqual(self.base_preset.model_function_name, "xception")
        self.assertEqual(self.base_preset.validation_lion_directories, [])
        self.assertEqual(self.base_preset.validation_no_lion_directories, [])

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
image-dimensions: [128, 128]
cameras:
    - hostname: camera1
      ip_address: 192.168.1.100
      mac_address: aa:bb:cc:dd:ee:01
      last_seen: "2024-01-15T10:00:00Z"
      status: connected
    - hostname: camera2
      ip_address: 192.168.1.101
      mac_address: aa:bb:cc:dd:ee:02
      last_seen: "2024-01-15T10:05:00Z"
      status: disconnected
plugs:
    - hostname: plug1
      ip_address: 192.168.1.200
      mac_address: ff:ee:dd:cc:bb:01
      last_seen: "2024-01-15T09:00:00Z"
      status: connected
      mode: off
""",
    )
    def test_load_cameras_and_plugs(self, mock_file):  # pylint: disable=unused-argument
        """
        Test loading cameras and plugs from settings file.
        """
        self.base_preset.load("/fake/path/to/settings.yaml")

        # Verify cameras were loaded
        self.assertEqual(len(self.base_preset.cameras), 2)
        self.assertEqual(self.base_preset.cameras[0]["hostname"], "camera1")
        self.assertEqual(
            self.base_preset.cameras[0]["ip_address"], "192.168.1.100"
        )
        self.assertEqual(
            self.base_preset.cameras[0]["mac_address"], "aa:bb:cc:dd:ee:01"
        )
        self.assertEqual(self.base_preset.cameras[1]["hostname"], "camera2")

        # Verify plugs were loaded
        self.assertEqual(len(self.base_preset.plugs), 1)
        self.assertEqual(self.base_preset.plugs[0]["hostname"], "plug1")
        self.assertEqual(
            self.base_preset.plugs[0]["ip_address"], "192.168.1.200"
        )
        self.assertEqual(
            self.base_preset.plugs[0]["mac_address"], "ff:ee:dd:cc:bb:01"
        )
        # YAML parses 'off' as False (boolean)
        self.assertEqual(self.base_preset.plugs[0]["mode"], False)

    def test_serialize_cameras_and_plugs(self):
        """
        Test that cameras and plugs are included in serialization.
        """
        self.base_preset.cameras = [
            {
                "hostname": "test-camera",
                "ip_address": "192.168.1.50",
                "mac_address": "11:22:33:44:55:66",
                "last_seen": "2024-01-15T12:00:00Z",
                "status": "connected",
            }
        ]
        self.base_preset.plugs = [
            {
                "hostname": "test-plug",
                "ip_address": "192.168.1.51",
                "mac_address": "66:55:44:33:22:11",
                "last_seen": "2024-01-15T11:00:00Z",
                "status": "connected",
                "mode": "on",
            }
        ]

        # Convert to dict (this is what yaml.dump uses)
        serialized = dict(self.base_preset)

        # Verify cameras and plugs are in the serialized data
        self.assertIn("cameras", serialized)
        self.assertIn("plugs", serialized)
        self.assertEqual(len(serialized["cameras"]), 1)
        self.assertEqual(len(serialized["plugs"]), 1)
        self.assertEqual(serialized["cameras"][0]["hostname"], "test-camera")
        self.assertEqual(serialized["plugs"][0]["hostname"], "test-plug")

    def test_tf_compat(self):
        """
        Test tf compatiblity.
        """
        self.base_preset.tf_compat = "2.15"
        self.assertEqual(self.base_preset.tf_compat, "2.15")
        with self.assertRaises(TypeError) as type_error:
            self.base_preset.tf_compat = 1  # type:ignore
        self.assertEqual(
            str(type_error.exception), "tf compat needs to be a string"
        )
        with self.assertRaises(ValueError) as value_error:
            self.base_preset.tf_compat = "2.16"
        self.assertEqual(
            str(value_error.exception), "tf compat needs to be in [2.15, 2.17]"
        )


class TestSettingsFileLocation(unittest.TestCase):
    """
    Test settings file location detection for different environments.
    """

    def test_snap_environment(self):
        """
        Test that settings file uses SNAP_USER_DATA when in snap.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            env_patch = {"SNAP_USER_DATA": tmpdir}
            with patch.dict(os.environ, env_patch, clear=False):
                settings_file = get_default_settings_file()
                expected_path = str(
                    Path(tmpdir) / "pumaguard" / "pumaguard-settings.yaml"
                )
                self.assertEqual(settings_file, expected_path)
                # Verify directory was created
                self.assertTrue(Path(tmpdir, "pumaguard").exists())

    def test_snap_environment_with_existing_file(self):
        """
        Test that existing snap settings file is found.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the snap settings file
            snap_config_dir = Path(tmpdir) / "pumaguard"
            snap_config_dir.mkdir(parents=True, exist_ok=True)
            snap_settings_file = snap_config_dir / "pumaguard-settings.yaml"
            snap_settings_file.touch()

            env_patch = {"SNAP_USER_DATA": tmpdir}
            with patch.dict(os.environ, env_patch, clear=False):
                settings_file = get_default_settings_file()
                self.assertEqual(settings_file, str(snap_settings_file))
                self.assertTrue(Path(settings_file).exists())

    def test_xdg_environment_without_snap(self):
        """
        Test settings file uses XDG_CONFIG_HOME when not in snap.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with custom XDG_CONFIG_HOME and no SNAP_USER_DATA
            env_vars = {"XDG_CONFIG_HOME": tmpdir}
            # Explicitly exclude SNAP_USER_DATA from environment
            with patch.dict(os.environ, env_vars, clear=True):
                settings_file = get_default_settings_file()
                expected_path = str(
                    Path(tmpdir) / "pumaguard" / "pumaguard-settings.yaml"
                )
                self.assertEqual(settings_file, expected_path)

    def test_snap_takes_precedence_over_xdg(self):
        """
        Test SNAP_USER_DATA takes precedence over XDG_CONFIG_HOME.
        """
        with tempfile.TemporaryDirectory() as snap_dir:
            with tempfile.TemporaryDirectory() as xdg_dir:
                env_vars = {
                    "SNAP_USER_DATA": snap_dir,
                    "XDG_CONFIG_HOME": xdg_dir,
                }

                with patch.dict(os.environ, env_vars, clear=False):
                    settings_file = get_default_settings_file()
                    # Should use snap directory, not XDG
                    expected_snap_path = str(
                        Path(snap_dir)
                        / "pumaguard"
                        / "pumaguard-settings.yaml"
                    )
                    self.assertEqual(settings_file, expected_snap_path)
                    self.assertNotIn(xdg_dir, settings_file)


class TestDeterrentSoundFiles(unittest.TestCase):
    """
    Test the deterrent_sound_files property and backwards compatibility.
    """

    def setUp(self):
        self.preset = Preset()

    def test_default_sound_files_is_list(self):
        """
        Test that deterrent_sound_files defaults to a list.
        """
        self.assertIsInstance(self.preset.deterrent_sound_files, list)
        self.assertEqual(len(self.preset.deterrent_sound_files), 1)
        self.assertEqual(
            self.preset.deterrent_sound_files[0], "deterrent_puma.mp3"
        )

    def test_set_multiple_sound_files(self):
        """
        Test setting multiple sound files.
        """
        sound_files = ["sound1.mp3", "sound2.mp3", "sound3.mp3"]
        self.preset.deterrent_sound_files = sound_files
        self.assertEqual(self.preset.deterrent_sound_files, sound_files)

    def test_cannot_set_empty_list(self):
        """
        Test that setting an empty list raises ValueError.
        """
        with self.assertRaises(ValueError) as error:
            self.preset.deterrent_sound_files = []
        self.assertEqual(
            str(error.exception), "At least one sound file must be provided"
        )

    def test_must_be_list(self):
        """
        Test that deterrent_sound_files must be a list.
        """
        with self.assertRaises(TypeError) as error:
            # type: ignore
            self.preset.deterrent_sound_files = "single_sound.mp3"
        self.assertEqual(
            str(error.exception), "deterrent_sound_files must be a list"
        )

    def test_all_elements_must_be_strings(self):
        """
        Test that all elements in the list must be strings.
        """
        with self.assertRaises(TypeError) as error:
            self.preset.deterrent_sound_files = [
                "sound1.mp3",
                123,
            ]  # type: ignore
        self.assertEqual(
            str(error.exception), "All sound files must be strings"
        )

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
image-dimensions: [128, 128]
deterrent-sound-files:
    - sound1.mp3
    - sound2.mp3
    - sound3.mp3
""",
    )
    def test_load_multiple_sound_files(self, mock_file):  # pylint: disable=unused-argument
        """
        Test loading multiple sound files from settings.
        """
        self.preset.load("/fake/path/to/settings.yaml")
        self.assertEqual(len(self.preset.deterrent_sound_files), 3)
        self.assertEqual(self.preset.deterrent_sound_files[0], "sound1.mp3")
        self.assertEqual(self.preset.deterrent_sound_files[1], "sound2.mp3")
        self.assertEqual(self.preset.deterrent_sound_files[2], "sound3.mp3")

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
image-dimensions: [128, 128]
deterrent-sound-file: old_format_sound.mp3
""",
    )
    def test_load_backwards_compatible_single_file(self, mock_file):  # pylint: disable=unused-argument
        """
        Test backwards compatibility with old single file format.
        """
        self.preset.load("/fake/path/to/settings.yaml")
        self.assertIsInstance(self.preset.deterrent_sound_files, list)
        self.assertEqual(len(self.preset.deterrent_sound_files), 1)
        self.assertEqual(
            self.preset.deterrent_sound_files[0], "old_format_sound.mp3"
        )

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
image-dimensions: [128, 128]
deterrent-sound-file: old_format_sound.mp3
deterrent-sound-files:
    - new_format1.mp3
    - new_format2.mp3
""",
    )
    def test_new_format_takes_precedence(self, mock_file):  # pylint: disable=unused-argument
        """
        Test that new format takes precedence when both are present.
        """
        self.preset.load("/fake/path/to/settings.yaml")
        self.assertEqual(len(self.preset.deterrent_sound_files), 2)
        self.assertEqual(
            self.preset.deterrent_sound_files[0], "new_format1.mp3"
        )
        self.assertEqual(
            self.preset.deterrent_sound_files[1], "new_format2.mp3"
        )

    def test_serialize_sound_files_list(self):
        """
        Test that sound files list is properly serialized.
        """
        self.preset.deterrent_sound_files = [
            "sound1.mp3",
            "sound2.mp3",
            "sound3.mp3",
        ]
        serialized = dict(self.preset)
        self.assertIn("deterrent-sound-files", serialized)
        self.assertEqual(len(serialized["deterrent-sound-files"]), 3)
        self.assertEqual(serialized["deterrent-sound-files"][0], "sound1.mp3")
        self.assertEqual(serialized["deterrent-sound-files"][1], "sound2.mp3")
        self.assertEqual(serialized["deterrent-sound-files"][2], "sound3.mp3")


class TestPresetSave(unittest.TestCase):
    """
    Test the Preset.save() method writes to disk correctly.
    """

    def setUp(self):
        self.preset = Preset()

    def test_save_writes_to_settings_file(self):
        """Test that save() writes settings to the configured file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            settings_file = f.name

        try:
            self.preset.settings_file = settings_file
            self.preset.yolo_min_size = 0.05
            self.preset.yolo_conf_thresh = 0.30
            self.preset.epochs = 100

            # Save settings
            self.preset.save()

            # Verify file exists
            self.assertTrue(Path(settings_file).exists())

            # Load and verify contents
            with open(settings_file, encoding="utf-8") as f:
                saved_data = yaml.safe_load(f)

            self.assertEqual(saved_data["YOLO-min-size"], 0.05)
            self.assertEqual(saved_data["YOLO-conf-thresh"], 0.30)
            self.assertEqual(saved_data["epochs"], 100)

        finally:
            # Cleanup
            if Path(settings_file).exists():
                Path(settings_file).unlink()

    def test_save_persists_cameras(self):
        """Test that save() persists camera list."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            settings_file = f.name

        try:
            self.preset.settings_file = settings_file
            self.preset.cameras = [
                {
                    "hostname": "camera1",
                    "ip_address": "192.168.1.100",
                    "mac_address": "aa:bb:cc:dd:ee:01",
                    "last_seen": "2024-01-15T10:00:00Z",
                    "status": "connected",
                },
                {
                    "hostname": "camera2",
                    "ip_address": "192.168.1.101",
                    "mac_address": "aa:bb:cc:dd:ee:02",
                    "last_seen": "2024-01-15T10:05:00Z",
                    "status": "disconnected",
                },
            ]

            # Save settings
            self.preset.save()

            # Load and verify contents
            with open(settings_file, encoding="utf-8") as f:
                saved_data = yaml.safe_load(f)

            self.assertEqual(len(saved_data["cameras"]), 2)
            self.assertEqual(saved_data["cameras"][0]["hostname"], "camera1")
            self.assertEqual(
                saved_data["cameras"][0]["mac_address"], "aa:bb:cc:dd:ee:01"
            )
            self.assertEqual(saved_data["cameras"][1]["hostname"], "camera2")

        finally:
            # Cleanup
            if Path(settings_file).exists():
                Path(settings_file).unlink()

    def test_save_persists_plugs(self):
        """Test that save() persists plug list."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            settings_file = f.name

        try:
            self.preset.settings_file = settings_file
            self.preset.plugs = [
                {
                    "hostname": "plug1",
                    "ip_address": "192.168.1.200",
                    "mac_address": "ff:ee:dd:cc:bb:01",
                    "last_seen": "2024-01-15T09:00:00Z",
                    "status": "connected",
                    "mode": "off",
                }
            ]

            # Save settings
            self.preset.save()

            # Load and verify contents
            with open(settings_file, encoding="utf-8") as f:
                saved_data = yaml.safe_load(f)

            self.assertEqual(len(saved_data["plugs"]), 1)
            self.assertEqual(saved_data["plugs"][0]["hostname"], "plug1")
            self.assertEqual(
                saved_data["plugs"][0]["mac_address"], "ff:ee:dd:cc:bb:01"
            )
            self.assertEqual(saved_data["plugs"][0]["mode"], "off")

        finally:
            # Cleanup
            if Path(settings_file).exists():
                Path(settings_file).unlink()

    def test_save_and_load_roundtrip(self):
        """Test that save() and load() work correctly together."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            settings_file = f.name

        try:
            # Save with first preset
            preset1 = Preset()
            preset1.settings_file = settings_file
            preset1.yolo_min_size = 0.03
            preset1.epochs = 250
            preset1.cameras = [
                {
                    "hostname": "test-camera",
                    "ip_address": "192.168.1.50",
                    "mac_address": "11:22:33:44:55:66",
                    "last_seen": "2024-01-15T12:00:00Z",
                    "status": "connected",
                }
            ]
            preset1.save()

            # Load with second preset
            preset2 = Preset()
            preset2.load(settings_file)

            # Verify all settings were persisted
            self.assertEqual(preset2.yolo_min_size, 0.03)
            self.assertEqual(preset2.epochs, 250)
            self.assertEqual(len(preset2.cameras), 1)
            self.assertEqual(preset2.cameras[0]["hostname"], "test-camera")
            self.assertEqual(
                preset2.cameras[0]["mac_address"], "11:22:33:44:55:66"
            )

        finally:
            # Cleanup
            if Path(settings_file).exists():
                Path(settings_file).unlink()

    def test_save_persists_plug_heartbeat_settings(self):
        """Test that save() persists plug heartbeat settings."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            settings_file = f.name

        try:
            self.preset.settings_file = settings_file
            self.preset.plug_heartbeat_enabled = False
            self.preset.plug_heartbeat_interval = 120
            self.preset.plug_heartbeat_timeout = 10

            # Save settings
            self.preset.save()

            # Load and verify contents
            with open(settings_file, encoding="utf-8") as f:
                saved_data = yaml.safe_load(f)

            self.assertEqual(saved_data["plug-heartbeat-enabled"], False)
            self.assertEqual(saved_data["plug-heartbeat-interval"], 120)
            self.assertEqual(saved_data["plug-heartbeat-timeout"], 10)

        finally:
            # Cleanup
            if Path(settings_file).exists():
                Path(settings_file).unlink()
