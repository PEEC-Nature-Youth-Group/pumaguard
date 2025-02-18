"""
The Conv2D model.
"""

from typing import (
    Tuple,
)

import keras  # type: ignore

from pumaguard.model import (
    Model,
)


class Conv2DModel(Model):
    """
    A simple model using a single Conv2D layer.
    """

    @staticmethod
    def model_name() -> str:
        """
        Get the model name.
        """
        return "conv2d"

    @staticmethod
    def model_description() -> str:
        """
        Get a description of the model.
        """
        return "A simple model using a single Conv2D layer."

    @property
    def model_type(self) -> str:
        """
        Get the model type.
        """
        return "pre-trained"

    def raw_model(self,
                  image_dimensions: Tuple[int, int],
                  number_color_channels: int) -> keras.Model:
        """
        The simple model using a single Conv2D layer.
        """
        return keras.Sequential([
            keras.Input(shape=(*image_dimensions, number_color_channels)),
            keras.layers.Conv2D(1, (3, 3), activation="relu"),
            keras.layers.Flatten(),
            keras.layers.Dense(1, activation="sigmoid")
        ])
