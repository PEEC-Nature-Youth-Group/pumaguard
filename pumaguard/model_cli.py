"""
CLI commands for managing models.
"""

import argparse
import logging

from pumaguard.model_downloader import (
    clear_model_cache,
    list_available_models,
)
from pumaguard.presets import (
    Preset,
)

logger = logging.getLogger("PumaGuard")


def configure_subparser(parser: argparse.ArgumentParser):
    """
    Parses command line arguments.
    """
    subparsers = parser.add_subparsers(dest="model_action")
    subparsers.add_parser(
        "list",
        help="List available models",
    )
    subparsers.add_parser(
        "clear",
        help="Clear model cache",
    )


def main(
    args: argparse.Namespace, presets: Preset
):  # pylint: disable=unused-argument
    """
    Main entry point.
    """
    if args.model_action == "list":
        logger.info(list_available_models())
    elif args.model_action == "clear":
        clear_model_cache()
    else:
        logger.error("What do you want to do with the models?")
