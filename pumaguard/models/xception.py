"""
The pre-trained model.
"""

from typing import (
    Tuple,
)

import keras  # type: ignore
import tensorflow as tf  # type: ignore

from pumaguard.model import (
    Model,
)


class XceptionModel(Model):
    """
    The pre-trained model (Xception).
    """

    @staticmethod
    def model_name() -> str:
        """
        Get the model name.
        """
        return 'xception'

    @staticmethod
    def model_description() -> str:
        """
        Get a description of the model.
        """
        return 'A pre-trained model based on the Xception model.'

    @property
    def model_type(self) -> str:
        """
        Get the model type.
        """
        return 'pre-trained'

    def raw_model(self,
                  image_dimensions: Tuple[int, int],
                  number_color_channels: int) -> keras.Model:
        """
        The pre-trained model (Xception).
        """

        inputs = keras.Input(
            shape=(*image_dimensions, number_color_channels))

        if number_color_channels == 1:
            converted_inputs = keras.layers.Lambda(
                tf.image.grayscale_to_rgb)(inputs)
        else:
            converted_inputs = inputs

        base_model = keras.applications.Xception(
            weights='imagenet',
            include_top=False,
            input_tensor=converted_inputs,
        )

        # We do not want to change the weights in the Xception model (imagenet
        # weights are frozen)
        base_model.trainable = False

        # Average pooling takes the 2,048 outputs of the Xception model and
        # brings it into one output. The sigmoid layer makes sure that one
        # output is between 0-1. We will train all parameters in these last
        # two layers
        return keras.Sequential([
            base_model,
            keras.layers.GlobalAveragePooling2D(),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dense(1, activation='sigmoid'),
        ])
