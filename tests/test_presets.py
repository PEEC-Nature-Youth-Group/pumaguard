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
