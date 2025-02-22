"""
Test Presets class
"""

import unittest
from unittest.mock import (
    mock_open,
    patch,
)

from pumaguard.presets import (
    Preset,
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
        self.assertEqual(str(type_error.exception),
                         'image dimensions needs to be a tuple')
        with self.assertRaises(ValueError) as value_error:
            self.base_preset.image_dimensions = (-1, 2)
        self.assertEqual(str(value_error.exception),
                         'image dimensions need to be positive')

    @patch('builtins.open', new_callable=mock_open, read_data='''
notebook: 10
epochs: 2400
image-dimensions: [128, 128]
with-augmentation: True
batch-size: 2
model-function: xception
model-version: light-test
alpha: 1e-3
base-data-directory: /path/to/data
base-output-directory: /path/to/output
verification-path: /path/to/verification
lion-directories:
    - lion
no-lion-directories:
    - no_lion
''')
    def test_load(self, mock_file):  # pylint: disable=unused-argument
        """
        Test loading settings from file.
        """
        self.base_preset.load('/fake/path/to/settings.yaml')
        self.assertEqual(self.base_preset.notebook_number, 10)
        self.assertEqual(self.base_preset.epochs, 2400)
        self.assertEqual(self.base_preset.image_dimensions, (128, 128))
        self.assertEqual(self.base_preset.model_version, 'light-test')
        self.assertEqual(self.base_preset.base_data_directory, '/path/to/data')
        self.assertEqual(self.base_preset.verification_path,
                         '/path/to/verification')
        self.assertEqual(
            self.base_preset.base_output_directory, '/path/to/output')
        self.assertIn('/path/to/data/lion', self.base_preset.lion_directories)
        self.assertIn('/path/to/data/no_lion',
                      self.base_preset.no_lion_directories)
        self.assertTrue(hasattr(self.base_preset, 'with_augmentation'))
        self.assertEqual(self.base_preset.batch_size, 2)
        self.assertEqual(self.base_preset.alpha, 1e-3)
        self.assertEqual(self.base_preset.model_function_name, 'xception')
        self.assertEqual(self.base_preset.validation_lion_directories, [])
        self.assertEqual(self.base_preset.validation_no_lion_directories, [])

    def test_tf_compat(self):
        """
        Test tf compatiblity.
        """
        self.base_preset.tf_compat = '2.15'
        self.assertEqual(self.base_preset.tf_compat, '2.15')
        with self.assertRaises(TypeError) as type_error:
            self.base_preset.tf_compat = 1  # type:ignore
        self.assertEqual(str(type_error.exception),
                         'tf compat needs to be a string')
        with self.assertRaises(ValueError) as value_error:
            self.base_preset.tf_compat = '2.16'
        self.assertEqual(str(value_error.exception),
                         'tf compat needs to be in [2.15, 2.17]')
