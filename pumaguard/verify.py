"""
This script verifies models against a standard set of images.
"""

# pylint: disable=redefined-outer-name

import argparse
import logging
import os

import keras  # type: ignore

from pumaguard.model_factory import (
    model_factory,
)
from pumaguard.presets import (
    Preset,
)
from pumaguard.utils import (
    classify_image,
)

logger = logging.getLogger('PumaGuard')


def configure_subparser(parser: argparse.ArgumentParser):
    """
    Parse the commandline
    """
    parser.add_argument(
        '--data-path',
        help=('Where the image data for training and classification are '
              'stored (default = %(default)s)'),
        type=str,
        default=os.getenv(
            'PUMAGUARD_DATA_PATH',
            default=os.path.join(os.path.dirname(__file__), '../data')),
    )
    parser.add_argument(
        '--verification-path',
        help='Path to verification data set (default = %(default)s)',
        default='stable/stable_test',
    )
    parser.add_argument(
        'image',
        metavar='FILE',
        help='An image to classify.',
        nargs='*',
        type=str,
    )


def verify_model(presets: Preset, model: keras.Model):
    """
    Verify a model by calculating its accuracy across a standard set of images.
    """
    logger.info('verifying model')
    lion_directory = os.path.join(
        presets.base_data_directory, presets.verification_path, 'lion')
    lions = os.listdir(lion_directory)
    no_lion_directory = os.path.join(
        presets.base_data_directory, presets.verification_path, 'no-lion')
    no_lions = os.listdir(no_lion_directory)
    confusion = {
        'TP': 0.0, 'TN': 0.0, 'FP': 0.0, 'FN': 0.0,
    }
    for lion in lions:
        logger.debug('classifying %s', os.path.join(lion_directory, lion))
        prediction = classify_image(presets, model, os.path.join(
            lion_directory, lion))
        if prediction >= 0:
            print(f'Predicted {lion}: {100*(1 - prediction):6.2f}% lion')
            confusion['TP'] += 1 - prediction
            confusion['FN'] += prediction
        else:
            logger.warning('predicted label < 0!')
    for no_lion in no_lions:
        logger.debug('classifying %s', os.path.join(
            no_lion_directory, no_lion))
        prediction = classify_image(presets, model, os.path.join(
            no_lion_directory, no_lion))
        if prediction >= 0:
            print(
                f'Predicted {no_lion}: {100*(1 - prediction):6.2f}% lion')
            confusion['TN'] += prediction
            confusion['FP'] += 1 - prediction
        else:
            logger.warning('predicted label < 0!')
    total = sum(confusion.values())
    logger.debug(confusion)
    logger.debug(total)
    logger.debug('%d lions and %d no lions', len(lions), len(no_lions))
    accuracy = (confusion['TP'] + confusion['TN']) / total
    print(f'accuracy = {100 * accuracy:.2f}%')


def main(presets: Preset):
    """
    Main entry point
    """

    logger.debug('loading model from %s', presets.model_file)
    model = model_factory(presets).model

    verify_model(presets, model)
