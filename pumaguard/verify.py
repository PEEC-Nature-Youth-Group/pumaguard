"""
This script verifies models against a standard set of images.
"""

# pylint: disable=redefined-outer-name

import argparse
import logging
import math
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


def get_accuracy(predictions: list[tuple[str, float, int]]) -> float:
    """
    Get the accuracy of the model.
    """
    confusion_matrix = {
        'TP': 0.0, 'TN': 0.0, 'FP': 0.0, 'FN': 0.0,
    }
    number_lion = 0
    number_no_lion = 0
    for _, prediction, label in predictions:
        if label == 0:
            if prediction >= 0:
                confusion_matrix['TP'] += 1 - prediction
                confusion_matrix['FN'] += prediction
                number_lion += 1
            else:
                logger.warning('predicted label < 0!')
        elif label == 1:
            if prediction >= 0:
                confusion_matrix['TN'] += prediction
                confusion_matrix['FP'] += 1 - prediction
                number_no_lion += 1
            else:
                logger.warning('predicted label < 0!')
    total = sum(confusion_matrix.values())
    logger.debug('total = %.2f', total)
    logger.debug('%d lion and %d no-lion images', number_lion, number_no_lion)
    logger.debug('confusion matrix: %s', confusion_matrix)
    return (confusion_matrix['TP'] + confusion_matrix['TN']) / len(predictions)


def get_binary_accuracy(predictions: list[tuple[str, float, int]]) -> float:
    """
    Get the accuracy of the model.
    """
    confusion_matrix = [[0, 0], [0, 0]]
    for _, prediction, label in predictions:
        prediction = round(prediction)
        confusion_matrix[label][prediction] += 1
    logger.debug('binary confusion matrix: %s', confusion_matrix)
    return (confusion_matrix[0][0] + confusion_matrix[1][1]) / len(predictions)


def get_crossentropy_loss(predictions: list[tuple[str, float, int]]) -> float:
    """
    Get the log-loss (crossentropy loss) of the model.
    """
    loss: float = 0
    epsilon = 1e-15
    for _, prediction, label in predictions:
        prediction = max(epsilon, min(1 - epsilon, prediction))
        loss += label * math.log(prediction) + \
            (1 - label) * math.log(1 - prediction)
    return -loss / len(predictions)


def get_mean_squared_error(predictions: list[tuple[str, float, int]]) -> float:
    """
    Get the mean squared error of the model.
    """
    error: float = 0
    for _, prediction, label in predictions:
        error += (label - prediction)**2
    return error / len(predictions)


def verify_model(presets: Preset, model: keras.Model):
    """
    Verify a model by calculating its accuracy across a standard set of images.
    """
    logger.info('verifying model')
    lion_directory = os.path.join(presets.verification_path, 'lion')
    lions = sorted(os.listdir(lion_directory))
    no_lion_directory = os.path.join(presets.verification_path, 'no-lion')
    no_lions = sorted(os.listdir(no_lion_directory))
    logger.debug('%d lions and %d no lions', len(lions), len(no_lions))
    predictions = []
    number_false_positives = 0
    number_false_negatives = 0
    for lion in lions:
        filename = os.path.relpath(os.path.join(lion_directory, lion), '.')
        logger.debug('classifying %s', filename)
        prediction = classify_image(presets, model, filename)
        predictions.append((filename, prediction, 0))
        is_correct = prediction < 0.5
        if not is_correct:
            number_false_negatives += 1
        logger.info('Predicted %s: label %.4f, %6.2f%% lion: %s',
                    filename, prediction, 100*(1 - prediction),
                    'correct' if is_correct else 'incorrect')
    for no_lion in no_lions:
        filename = os.path.relpath(
            os.path.join(no_lion_directory, no_lion), '.')
        logger.debug('classifying %s', filename)
        prediction = classify_image(presets, model, filename)
        predictions.append((filename, prediction, 1))
        is_correct = prediction >= 0.5
        if not is_correct:
            number_false_positives += 1
        logger.info('Predicted %s: label %.4f, %6.2f%% lion: %s',
                    filename, prediction, 100*(1 - prediction),
                    'correct' if is_correct else 'incorrect')
    print(f'number false positives = {number_false_positives}')
    print(f'number false negatives = {number_false_negatives}')
    print('accuracy           = '
          f'{100 * get_accuracy(predictions):.2f}%')
    print('binary accuracy    = '
          f'{100 * get_binary_accuracy(predictions):.2f}%')
    print('crossentropy loss  = '
          f'{get_crossentropy_loss(predictions):.4f}')
    print('mean squared error = '
          f'{get_mean_squared_error(predictions):.4f}')


def main(presets: Preset):
    """
    Main entry point
    """

    logger.debug('loading model from %s', presets.model_file)
    model = model_factory(presets).model

    verify_model(presets, model)
