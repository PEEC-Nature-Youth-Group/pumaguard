"""
CLI commands for managing models.
"""

import argparse
import logging

from pumaguard.presets import (
    Preset,
)

logger = logging.getLogger("PumaGuard")


def configure_subparser(parser: argparse.ArgumentParser):
    """
    Parses command line arguments.
    """
    logger.debug("parser = %s", parser.usage)


def main(options: argparse.Namespace, presets: Preset):
    """
    Main entry point.
    """
    logger.debug("options: %s", options)
    logger.debug("presets: %s", presets)
