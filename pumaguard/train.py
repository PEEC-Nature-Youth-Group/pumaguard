"""
This script trains a model.
"""

import argparse
import copy
import datetime
import logging
import shutil
import sys
import tempfile

import keras  # type: ignore
import yaml

from pumaguard.model_factory import (
    model_factory,
)
from pumaguard.models import (
    __MODELS__,
)
from pumaguard.presets import (
    Preset,
)
from pumaguard.stats import (
    print_training_stats,
)
from pumaguard.traininghistory import (
    TrainingHistory,
)
from pumaguard.utils import (
    create_datasets,
    organize_data,
)

logger = logging.getLogger("PumaGuard")


def train_model(
    training_dataset,
    validation_dataset,
    full_history,
    presets: Preset,
    model: keras.Model,
):
    """
    Train the model.
    """
    checkpoint = keras.callbacks.ModelCheckpoint(
        filepath=presets.model_file,
        monitor="val_accuracy",
        save_best_only=True,
        save_weights_only=False,
        verbose=1,
    )

    reduce_learning_rate = keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.75,  # New lr = lr * factor.
        patience=25,
        verbose=1,
        mode="min",
        min_lr=1e-8,  # Lower bound on the learning rate.
    )

    print(f"Training for {presets.epochs} epochs")
    start_time = datetime.datetime.now()
    print(start_time)
    model.fit(
        training_dataset,
        epochs=presets.epochs,
        validation_data=validation_dataset,
        callbacks=[
            checkpoint,
            reduce_learning_rate,
            full_history,
        ],
    )
    end_time = datetime.datetime.now()
    print(end_time)

    duration = (end_time - start_time).total_seconds()
    print(f"This run took {duration} seconds")

    if "duration" not in full_history.history:
        full_history.history["duration"] = []
    full_history.history["duration"].append(duration)

    print(
        f'total time {sum(full_history.history["duration"])} '
        f'for {len(full_history.history["accuracy"])} epochs'
    )


def configure_subparser(parser: argparse.ArgumentParser):
    """
    Return Parser the command line.
    """
    parser.add_argument(
        "--lion",
        help="Directory with lion images",
        nargs="+",
    )
    parser.add_argument(
        "--no-lion",
        help="Directory with images not showing lions",
        nargs="+",
    )
    parser.add_argument(
        "--validation-lion",
        help=(
            "Directory with lion images for validation "
            "(this disables the automatic splitting of training data)"
        ),
    )
    parser.add_argument(
        "--validation-no-lion",
        help=(
            "Directory with images not showing lions for validation "
            "(this disables the automatic splitting of training data)"
        ),
    )
    parser.add_argument(
        "--model-output",
        help="The output folder for the new model.",
        type=str,
    )
    parser.add_argument(
        "--no-load-previous-session",
        help="Do not load previous training session from file",
        action="store_true",
    )
    parser.add_argument(
        "--dump-settings",
        help="Print current settings to standard output",
        action="store_true",
    )
    parser.add_argument(
        "--alpha",
        help="Initial learning rate for the Adam optimizer",
        type=float,
    )
    parser.add_argument(
        "--epochs",
        help="How many epochs to train.",
        type=int,
    )
    parser.add_argument(
        "--batch-size",
        help="How many images to process at once.",
        type=int,
    )
    parser.add_argument(
        "--image-dimensions",
        help="The dimensions of the images",
        type=int,
        nargs=2,
    )
    parser.add_argument(
        "--model-function",
        help="The model function to use",
        type=str,
        choices=__MODELS__.keys(),
    )


def _configure_directories(presets: Preset, options: argparse.Namespace):
    lion_directories = options.lion if options.lion is not None else []
    if len(lion_directories) > 0:
        presets.lion_directories = copy.deepcopy(lion_directories)

    no_lion_directories = (
        options.no_lion if options.no_lion is not None else []
    )
    if len(no_lion_directories) > 0:
        presets.no_lion_directories = copy.deepcopy(no_lion_directories)

    validation_lion_directories = (
        options.validation_lion if options.validation_lion is not None else []
    )
    if len(validation_lion_directories) > 0:
        presets.validation_lion_directories = copy.deepcopy(
            validation_lion_directories
        )

    validation_no_lion_directories = (
        options.validation_no_lion
        if options.validation_no_lion is not None
        else []
    )
    if len(validation_no_lion_directories) > 0:
        presets.validation_no_lion_directories = copy.deepcopy(
            validation_no_lion_directories
        )

    logger.debug("getting lion images from    %s", presets.lion_directories)
    logger.debug("getting no-lion images from %s", presets.no_lion_directories)

    if (
        len(presets.validation_lion_directories) > 0
        or len(presets.validation_no_lion_directories) > 0
    ):
        logger.info("using validation data from directories")
        logger.debug(
            "getting validation lion images from    %s",
            presets.validation_lion_directories,
        )
        logger.debug(
            "getting validation no-lion images from %s",
            presets.validation_no_lion_directories,
        )


def _configure_model(presets: Preset, options: argparse.Namespace):
    if options.alpha is not None:
        presets.alpha = options.alpha

    if options.epochs is not None:
        presets.epochs = options.epochs

    if options.batch_size is not None:
        presets.batch_size = options.batch_size

    if options.image_dimensions is not None:
        presets.image_dimensions = tuple(options.image_dimensions)


def _configure_settings(presets: Preset, options: argparse.Namespace):
    if options.no_load_previous_session:
        logger.info("will not load previous weights and history")
        presets.load_history_from_file = False
        presets.load_model_from_file = False
    else:
        presets.load_history_from_file = True
        presets.load_model_from_file = True

    logger.info("model file    %s", presets.model_file)
    logger.info("history file  %s", presets.history_file)
    logger.info("settings file %s", presets.settings_file)

    if options.model_output is not None:
        logger.debug("setting model output to %s", options.model_output)
        try:
            shutil.copy(presets.model_file, options.model_output)
            shutil.copy(presets.history_file, options.model_output)
        except FileNotFoundError:
            logger.warning("unable to find previous model; ignoring")
        presets.base_output_directory = options.model_output


def main(options: argparse.Namespace, presets: Preset):
    """
    The main entry point.
    """

    _configure_directories(presets, options)
    _configure_model(presets, options)
    _configure_settings(presets, options)

    if options.dump_settings:
        print("# PumaGuard settings")
        print(yaml.safe_dump(dict(presets), indent=2))
        sys.exit(0)

    with open(presets.settings_file, "w", encoding="utf-8") as fd:
        fd.write("# PumaGuard settings\n")
        fd.write(yaml.safe_dump(dict(presets), indent=2))

    work_directory = tempfile.mkdtemp(prefix="pumaguard-work-")
    validation_directory = tempfile.mkdtemp(prefix="pumaguard-validation-")

    logger.debug("work directory is %s", work_directory)
    logger.debug("validation directory is %s", validation_directory)

    organize_data(
        presets=presets,
        work_directory=work_directory,
        validation_directory=validation_directory,
    )

    logger.info("using color_mode %s", presets.color_mode)
    logger.info("image dimensions %s", presets.image_dimensions)

    training_dataset, validation_dataset = create_datasets(
        presets=presets,
        training_directory=work_directory,
        validation_directory=validation_directory,
        color_mode=presets.color_mode,
    )

    full_history = TrainingHistory(presets)

    best_accuracy, best_val_accuracy, best_loss, best_val_loss, best_epoch = (
        full_history.get_best_epoch("accuracy")
    )
    logger.info(
        "Total time %.2f for %.2f epochs",
        sum(full_history.history["duration"]),
        len(full_history.history["accuracy"]),
    )
    logger.info(
        "Best epoch %d - accuracy: %.4f - val_accuracy: %.4f "
        "- loss: %.4f - val_loss: %.4f",
        best_epoch,
        best_accuracy,
        best_val_accuracy,
        best_loss,
        best_val_loss,
    )

    model = model_factory(presets).model
    train_model(
        training_dataset=training_dataset,
        validation_dataset=validation_dataset,
        model=model,
        presets=presets,
        full_history=full_history,
    )

    print_training_stats(full_history)
