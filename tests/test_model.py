"""
Test the Model class.
"""

import os
from unittest import (
    TestCase,
)
from unittest.mock import (
    MagicMock,
    patch,
)

from pumaguard.model import (
    Model,
)
from pumaguard.presets import (
    Preset,
)


class TestModel(Model):
    """
    Test the Model class.
    """

    @property
    def model_type(self):
        """
        Return the type of the model.
        """
        return "TestModel"

    @staticmethod
    def model_description():
        """
        Return a description of the model.
        """
        return "This is a test model used for unit testing."

    @staticmethod
    def model_name():
        """
        Return the name of the model.
        """

    def raw_model(self, image_dimensions, number_color_channels):
        """
        Process raw model data given image dimensions and
         number of color channels.
        """


class TestModelClass(TestCase):
    """
    Test the Model class.
    """

    def test_download_model_weights(self, tmp_path, filename):
        """
        Test the download_model_weights method.
        """
        test_file = tmp_path / filename
        presets = Preset()
        model = TestModel(presets)

        mocked_response = MagicMock()
        mocked_response.iter_content.return_value = [b"testcontent"]
        mocked_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mocked_response):
            model._download_model_weights(str(test_file))
            assert os.path.isfile(
                test_file), "File should exist after download"
