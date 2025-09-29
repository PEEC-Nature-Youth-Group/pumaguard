"""
This module provides analysis functions for the PumaGuard project.
"""

import argparse
import logging

from pumaguard.presets import (
    Preset,
)
from pumaguard.stats import (
    print_training_stats,
)
from pumaguard.traininghistory import (
    TrainingHistory,
)

logger = logging.getLogger("PumaGuard")


def configure_subparser(parser: argparse.ArgumentParser):
    """
    Configure the parser for the analyze sub-command.
    """
    parser.add_argument(
        "--history",
        help="Path to the history file",
        type=str,
    )


def main(presets: Preset):
    """
    Main entry point.
    """

    logger.info("Analyzing model")

    full_history = TrainingHistory(presets)
    print_training_stats(full_history)
