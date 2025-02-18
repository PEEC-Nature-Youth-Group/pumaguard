"""
The MobileNetV3 model.
"""

from typing import (
    Tuple,
)

import keras  # type: ignore
import tensorflow as tf  # type: ignore

from pumaguard.model import (
    Model,
)


class MobileNetV3Model(Model):
    """
    The MobileNetV3 model (MobileNetV3Small).
    """

    @staticmethod
    def model_name() -> str:
        """
        Get the model name.
        """
        return 'mobilenetv3'

    @staticmethod
    def model_description() -> str:
        """
        Get a description of the model.
        """
        return 'A pre-trained model based on MobileNetV3Small.'

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
        The pre-trained model (MobileNetV3Small).
        """

        inputs = keras.Input(
            shape=(*image_dimensions, number_color_channels))

        if number_color_channels == 1:
            converted_inputs = keras.layers.Lambda(
                tf.image.grayscale_to_rgb)(inputs)
        else:
            converted_inputs = inputs

        base_model = keras.applications.MobileNetV3Small(
            weights='imagenet',
            include_top=False,
            input_tensor=converted_inputs,
        )

        # We do not want to change the weights in the MobileNetV3Small model
        # (imagenet weights are frozen)
        base_model.trainable = False

        # Average pooling takes the outputs of the MobileNetV3Small model and
        # brings it into one output. The sigmoid layer makes sure that one
        # output is between 0-1. We will train all parameters in these last
        # two layers
        return keras.Sequential([
            base_model,
            keras.layers.GlobalAveragePooling2D(),
            keras.layers.Dense(1, activation='sigmoid'),
        ])
