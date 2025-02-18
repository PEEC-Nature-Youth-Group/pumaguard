"""
The light-3 model.
"""

from typing import (
    Tuple,
)

import keras  # type: ignore

from pumaguard.model import (
    Model,
)


class LightModel3(Model):
    """
    Ultra-light CNN model for binary image classification (<10k params).
    """

    @staticmethod
    def model_name() -> str:
        """
        Get the model name.
        """
        return 'light-3-model'

    @staticmethod
    def model_description() -> str:
        """
        Get a description of the model.
        """
        return ('Ultra-light CNN model for binary image '
                'classification (<10k params).')

    @property
    def model_type(self) -> str:
        """
        Get the model type.
        """
        return 'light-3'

    def raw_model(self,
                  image_dimensions: Tuple[int, int],
                  number_color_channels: int) -> keras.Model:
        """
        Ultra-light CNN model for binary image classification (<10k params).
        """
        return keras.Sequential([
            keras.Input(shape=(*image_dimensions, number_color_channels)),
            keras.layers.Conv2D(
                8,
                (3, 3),
                activation='relu',
                padding='same',
                strides=(2, 2)),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(
                16,
                (3, 3),
                activation='relu',
                padding='same',
                strides=(2, 2)),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(8, activation='relu'),
            keras.layers.Dense(1, activation='sigmoid')
        ])
