"""
This script classifies images.
"""

# pylint: disable=redefined-outer-name

import argparse
import logging

from pumaguard.presets import (
    Settings,
)
from pumaguard.utils import (
    classify_image_two_stage,
)

logger = logging.getLogger("PumaGuard")


def configure_subparser(parser: argparse.ArgumentParser):
    """
    Parse the commandline
    """
    parser.add_argument(
        "image",
        metavar="FILE",
        help="An image to classify.",
        nargs="*",
        type=str,
    )


def main(options: argparse.Namespace, presets: Settings):
    """
    Main entry point
    """

    logger.debug("starting classify")

    for image_path in options.image:
        prediction = classify_image_two_stage(
            presets=presets, image_path=image_path
        )
        if prediction >= 0:
            print(
                f"Predicted {image_path}: {100 * prediction:6.2f}% lion "
                + f"({'lion' if prediction > 0.5 else 'no lion'})"
            )
        else:
            logger.warning("predicted label < 0!")
