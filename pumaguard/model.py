"""
The Model class.
"""

import logging
import os
from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Any,
    Tuple,
)

import keras  # type: ignore
import requests
import tensorflow as tf  # type: ignore

from pumaguard.presets import (
    Preset,
)
from pumaguard.utils import (
    get_md5,
)

logger = logging.getLogger('PumaGuard')


class Model(ABC):
    """
    The base class for Models.
    """

    _distribution_strategy = None
    _initialized = False
    _instance: Any = None
    _model = None

    def __new__(cls, presets: Preset):
        """
        Create a new model. Note that there will only be one instance of
        this class.
        """
        if cls._instance is None:
            cls._instance = super(Model, cls).__new__(cls)
        return cls._instance

    def __init__(self, presets: Preset):
        if not self._initialized:
            self._initialized = True
            self._presets = presets

    def _initialize(self):
        """
        Initialize the model.
        """
        self._distribution_strategy = self._initialize_tensorflow()
        logger.debug('initializing new model')
        self._model = self._compile_model(
            distribution_strategy=self._distribution_strategy,
            load_model_from_file=self._presets.load_model_from_file,
            model_file=self._presets.model_file,
            image_dimensions=self._presets.image_dimensions,
            number_color_channels=self._presets.number_color_channels,
            alpha=self._presets.alpha,
        )

    @abstractmethod
    def raw_model(self,
                  image_dimensions: Tuple[int, int],
                  number_color_channels: int) -> keras.Model:
        """
        The uncompiled Keras model.
        """

    @staticmethod
    @abstractmethod
    def model_name() -> str:
        """
        Get the model name.
        """

    @staticmethod
    @abstractmethod
    def model_description() -> str:
        """
        Get a description of the model.
        """

    @property
    @abstractmethod
    def model_type(self) -> str:
        """
        Get the model type.
        """

    @property
    def model(self) -> keras.Model:
        """
        Get the compiled model.
        """
        if self._model is None:
            self._initialize()
        return self._model

    def _initialize_tensorflow(self) -> tf.distribute.Strategy:
        """
        Initialize Tensorflow on available hardware.

        Try different backends in the following order: TPU, GPU, CPU and use
        the first one available.

        Returns:
            tf.distribute.Strategy: The distribution strategy object after
            initialization.
        """
        logger.info("Tensorflow version %s", tf.__version__)
        logger.info('Trying to connect to a TPU')
        try:
            tpu = tf.distribute.cluster_resolver.TPUClusterResolver()
            tf.config.experimental_connect_to_cluster(tpu)
            tf.tpu.experimental.initialize_tpu_system(tpu)
            logger.info(
                'Running on a TPU with %d cores',
                tpu.num_accelerators()["TPU"])
            return tf.distribute.TPUStrategy(tpu)
        except ValueError:
            logger.warning(
                "WARNING: Not connected to a TPU runtime; Will try GPU")
            if tf.config.list_physical_devices('GPU'):
                logger.info('Running on %d GPUs', len(
                    tf.config.list_physical_devices("GPU")))
                return tf.distribute.MirroredStrategy()
            logger.warning('WARNING: Not connected to TPU or GPU runtime; '
                           'Will use CPU context')
            return tf.distribute.get_strategy()

    def _load_model(self, filename: str) -> keras.Model:
        """
        Load a model from file.
        """
        os.stat(filename)
        logger.debug('loading model from file %s', filename)
        model = keras.models.load_model(filename)
        logger.debug('loaded model from file')
        logger.info('loaded model version %s', get_md5(filename))
        return model

    def _download_model_weights(self, filename: str):
        logger.info('downloading model weights %s from '
                    'https://github.com/PEEC-Nature-Youth-Group'
                    '/pumaguard-models', filename)
        commit = 'main'

        # https://github.com/PEEC-Nature-Youth-Group/pumaguard-models/blob/main/model_history_12_pre-trained_tf2.17_512_512.pickle

        url = ('https://github.com/'
               'PEEC-Nature-Youth-Group/pumaguard-models/blob/'
               f'{commit}/{os.path.basename(filename)}')

        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(filename, 'wb') as out_file:
            for chunk in response.iter_content(chunk_size=8192):
                out_file.write(chunk)
        logger.info('download complete')

    def _compile_model(self,  # pylint: disable=too-many-arguments,too-many-positional-arguments
                       distribution_strategy: tf.distribute.Strategy,
                       load_model_from_file: bool = False,
                       model_file: str = '',
                       image_dimensions: Tuple[int, int] = (128, 128),
                       number_color_channels: int = 3,
                       alpha: float = 1e-5) -> keras.Model:
        """
        Create the model.
        """
        with distribution_strategy.scope():
            if load_model_from_file:
                logger.info('looking for model at %s', model_file)
                model_file_exists = os.path.isfile(model_file)
                if model_file_exists:
                    model = self._load_model(model_file)
                else:
                    logger.info('model not found, downloading...')
                    self._download_model_weights(model_file)
                    if not os.path.isfile(model_file):
                        raise FileNotFoundError(
                            f'could not download {model_file}')
                    model = self._load_model(model_file)
            else:
                logger.debug('not loading previous weights')
                logger.info('creating new %s model',
                            self.model_name)
                model = self.raw_model(
                    image_dimensions=image_dimensions,
                    number_color_channels=number_color_channels)

            logger.debug('Compiling model')
            model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=alpha),
                loss='binary_crossentropy',
                metrics=['accuracy'],
            )
            logger.info('Number of layers in the model: %d', len(model.layers))
            model.summary()

        return model
