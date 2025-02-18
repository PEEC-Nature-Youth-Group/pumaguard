"""
The light model.
"""

from typing import (
    Tuple,
)

import keras  # type: ignore

from pumaguard.model import (
    Model,
)


class LightModel1(Model):
    """
    A light model.
    """

    @staticmethod
    def model_name() -> str:
        """
        Get the model name.
        """
        return 'light-model'

    @staticmethod
    def model_description() -> str:
        """
        Get a description of the model.
        """
        return ('A "light model" which is loosely based on the '
                'Xception model and constructs a CNN.')

    @property
    def model_type(self) -> str:
        """
        Get the model type.
        """
        return 'light'

    def raw_model(self,
                  image_dimensions: Tuple[int, int],
                  number_color_channels: int) -> keras.Model:
        """
        Define the "light model" which is loosely based on the Xception model
        and constructs a CNN.

        Note, the light model does not run properly on a TPU runtime. The loss
        function results in `nan` after only one epoch. It does work on GPU
        runtimes though.
        """
        inputs = keras.Input(
            shape=(*image_dimensions, number_color_channels))

        # Entry block
        x = keras.layers.Rescaling(1.0 / 255)(inputs)
        x = keras.layers.Conv2D(128, 1, strides=2, padding="same")(x)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.Activation("relu")(x)

        previous_block_activation = x  # Set aside residual

        for size in [256, 512, 728]:
            x = keras.layers.Activation("relu")(x)
            x = keras.layers.SeparableConv2D(size, 1, padding="same")(x)
            x = keras.layers.BatchNormalization()(x)

            x = keras.layers.Activation("relu")(x)
            x = keras.layers.SeparableConv2D(size, 1, padding="same")(x)
            x = keras.layers.BatchNormalization()(x)

            x = keras.layers.MaxPooling2D(1, strides=2, padding="same")(x)

            # Project residual
            residual = keras.layers.Conv2D(size, 1, strides=2, padding="same")(
                previous_block_activation
            )
            x = keras.layers.add([x, residual])  # Add back residual
            previous_block_activation = x  # Set aside next residual

        x = keras.layers.SeparableConv2D(1024, 1, padding="same")(x)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.Activation("relu")(x)

        x = keras.layers.GlobalAveragePooling2D()(x)

        x = keras.layers.Dropout(0.1)(x)

        outputs = keras.layers.Dense(1, activation=None)(x)

        return keras.Model(inputs, outputs)
