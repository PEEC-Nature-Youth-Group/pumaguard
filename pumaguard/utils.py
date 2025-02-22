"""
Some utility functions.
"""

import datetime
import glob
import hashlib
import logging
import os
import shutil

import keras  # type: ignore
import numpy as np
import tensorflow as tf  # type: ignore
from PIL import (
    Image,
)

from pumaguard.presets import (
    Preset,
)

logger = logging.getLogger('PumaGuard')


def get_duration(start_time: datetime.datetime,
                 end_time: datetime.datetime) -> float:
    """
    Get duration between start and end time in seconds.

    Args:
        start_time (datetime.timezone): The start time.
        end_time (datetime.timezone): The end time.

    Returns:
        float: The duration in seconds.
    """
    duration = end_time - start_time
    return duration / datetime.timedelta(microseconds=1) / 1e6


def copy_images(work_directory, lion_images, no_lion_images):
    """
    Copy images to work directory.
    """
    print(f'Copying images to working directory '
          f'{os.path.realpath(work_directory)}')
    for image in lion_images:
        shutil.copy(image, f'{work_directory}/lion')
    for image in no_lion_images:
        shutil.copy(image, f'{work_directory}/no_lion')
    print('Copied all images')


def organize_data(presets: Preset, work_directory: str,
                  validation_directory: str):
    """
    Organizes the data and splits it into training and validation datasets.
    """
    logger.debug('organizing training data, work directory is %s, '
                 'validation directory is %s',
                 work_directory, validation_directory)

    logger.debug('lion images in    %s', presets.lion_directories)
    logger.debug('no-lion images in %s', presets.no_lion_directories)
    lion_images = []
    for lion in presets.lion_directories:
        lion_images += glob.glob(os.path.join(lion, '*JPG'))
    no_lion_images = []
    for no_lion in presets.no_lion_directories:
        no_lion_images += glob.glob(os.path.join(no_lion, '*JPG'))

    print(f'Found {len(lion_images)} images tagged as `lion`')
    print(f'Found {len(no_lion_images)} images tagged as `no-lion`')
    print(f'In total {len(lion_images) + len(no_lion_images)} images')

    shutil.rmtree(work_directory, ignore_errors=True)
    os.makedirs(f'{work_directory}/lion')
    os.makedirs(f'{work_directory}/no_lion')

    copy_images(work_directory=work_directory,
                lion_images=lion_images,
                no_lion_images=no_lion_images)

    if len(presets.validation_lion_directories) == 0 and \
            len(presets.validation_no_lion_directories) == 0:
        return

    logger.debug('validation lion images in    %s',
                 presets.validation_lion_directories)
    logger.debug('validation no-lion images in %s',
                 presets.validation_no_lion_directories)
    lion_images = []
    for lion in presets.validation_lion_directories:
        lion_images += glob.glob(os.path.join(lion, '*JPG'))
    no_lion_images = []
    for no_lion in presets.validation_no_lion_directories:
        no_lion_images += glob.glob(os.path.join(no_lion, '*JPG'))

    print(f'Found {len(lion_images)} images tagged as `lion`')
    print(f'Found {len(no_lion_images)} images tagged as `no-lion`')
    print(f'In total {len(lion_images) + len(no_lion_images)} images')

    shutil.rmtree(validation_directory, ignore_errors=True)
    os.makedirs(f'{validation_directory}/lion')
    os.makedirs(f'{validation_directory}/no_lion')

    copy_images(work_directory=validation_directory,
                lion_images=lion_images,
                no_lion_images=no_lion_images)


def image_augmentation(image, with_augmentation: bool, augmentation_layers):
    """
    Use augmentation if `with_augmentation` is set to True
    """
    if with_augmentation:
        for layer in augmentation_layers:
            image = layer(image)
    return image


def create_datasets(presets: Preset, training_directory: str,
                    validation_directory: str,
                    color_mode: str):
    """
    Create the training and validation datasets.
    """
    # Define augmentation layers which are used in some of the runs
    augmentation_layers = [
        keras.layers.RandomFlip('horizontal'),
        keras.layers.RandomRotation(0.01),
        keras.layers.RandomZoom(0.05),
        keras.layers.RandomBrightness((-0.1, 0.1)),
        keras.layers.RandomContrast(0.1),
        # keras.layers.RandomCrop(200, 200),
        # keras.layers.Rescaling(1./255),
    ]

    with_validation_split = len(presets.validation_lion_directories) == 0 and \
        len(presets.validation_no_lion_directories) == 0

    # Create datasets(training, validation)
    datasets = \
        keras.preprocessing.image_dataset_from_directory(
            training_directory,
            batch_size=presets.batch_size,
            validation_split=(0.2 if with_validation_split else None),
            subset=('both' if with_validation_split else None),
            # Seed is always the same in order to ensure that we can reproduce
            # the same training session
            seed=123,
            shuffle=True,
            image_size=presets.image_dimensions,
            color_mode=color_mode,
        )

    if with_validation_split:
        training_dataset = datasets[0]
        validation_dataset = datasets[1]
    else:
        training_dataset = datasets
        validation_dataset = \
            keras.preprocessing.image_dataset_from_directory(
                validation_directory,
                batch_size=presets.batch_size,
                seed=123,
                shuffle=True,
                image_size=presets.image_dimensions,
                color_mode=color_mode,
            )

    training_dataset = training_dataset.map(
        lambda img, label: (image_augmentation(
            image=img,
            with_augmentation=presets.with_augmentation,
            augmentation_layers=augmentation_layers), label),
        num_parallel_calls=tf.data.AUTOTUNE,
    )

    training_dataset = training_dataset.prefetch(tf.data.AUTOTUNE)
    validation_dataset = validation_dataset.prefetch(tf.data.AUTOTUNE)

    return training_dataset, validation_dataset


def get_md5(filepath: str) -> str:
    """
    Compute the MD5 hash for a file.
    """
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()


def get_sha256(filepath: str) -> str:
    """
    Compute the SHA-256 hash for a file.
    """
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()


def classify_image(presets: Preset, model: keras.Model,
                   image_path: str) -> float:
    """
    Classify the image and print out the result.

    Args:
        presets (BasePreset): An instance of the BasePreset class containing
        image processing settings.

        model (keras.Model): A pre-trained Keras model used for image
        classification.

        image_path (str): The file path to the image to be classified.

    Returns:
        float: The classification result as a float value.

    Prints:
        The color mode being used, the image being classified, and the time
        taken for classification.
    """
    logger.debug('using color_mode "%s"', presets.color_mode)
    logger.debug('classifying image %s', image_path)

    try:
        if presets.color_mode == 'rgb':
            img = Image.open(image_path).convert('RGB')
        elif presets.color_mode == 'grayscale':
            img = Image.open(image_path).convert('L')
        else:
            raise ValueError(f'unknown color mode {presets.color_mode}')
    except FileNotFoundError as e:
        logger.error('file not found: %s', e)
        raise

    logger.debug('image loaded, classifying now...')

    start_time = datetime.datetime.now()

    img = img.resize(presets.image_dimensions)
    img_array = np.array(img)
    # img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    if presets.color_mode == 'grayscale':
        img_array = np.expand_dims(img_array, axis=-1)

    prediction = model.predict(img_array)

    end_time = datetime.datetime.now()

    logger.debug('Classification took %.2f seconds',
                 get_duration(start_time, end_time))
    logger.debug('predicted label %.2f', prediction[0][0])
    return prediction[0][0]


def print_bash_completion(command: str, shell: str):
    """
    Print bash completion script.
    """
    command_string = ''
    if command is not None:
        command_string = f'{command}-'
    shell_suffix = ''
    if shell == 'bash':
        shell_suffix = 'sh'
    else:
        raise ValueError(f'unknown shell {shell}')
    completions_file = os.path.join(os.path.dirname(
        __file__), 'completions',
        f'pumaguard-{command_string}completions.{shell_suffix}')
    with open(completions_file, encoding='utf-8') as fd:
        print(fd.read())
