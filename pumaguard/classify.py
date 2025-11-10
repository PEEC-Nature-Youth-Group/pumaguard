"""
This script classifies images.
"""

# pylint: disable=redefined-outer-name

import argparse
import logging
from pathlib import (
    Path,
)

import PIL

from pumaguard.presets import (
    Preset,
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


def main(options: argparse.Namespace, presets: Preset):
    """
    Main entry point
    """

    logger.debug("starting classify")

    for image_file in options.image:
        image_path = Path(image_file)
        try:
            with PIL.Image.open(image_path) as img:
                image = img.convert("RGB")
        except OSError as e:
            logger.error("Could not open file: %s", e)
        prediction = classify_image_two_stage(
            presets=presets, image_path=image_path, image=image
        )
        if prediction >= 0:
            print(
                f"Predicted {image}: {100 * prediction:6.2f}% lion "
                f"({'lion' if prediction > 0.5 else 'no lion'})"
            )
        else:
            logger.warning("predicted label < 0!")
