"""
The training history.
"""

import logging
import os
import pickle

import keras  # type: ignore

from pumaguard.presets import (
    Preset,
)

logger = logging.getLogger("PumaGuard")


class TrainingHistory(keras.callbacks.Callback):
    """
    This class stores the training history
    """

    def __init__(self, presets: Preset):
        super().__init__()
        self.presets = presets
        self.history = {}
        self.number_epochs = 0
        history_file_exists = os.path.isfile(presets.history_file)
        if history_file_exists and presets.load_history_from_file:
            logger.info("loading history from file %s", presets.history_file)
            with open(presets.history_file, "rb") as f:
                self.history = pickle.load(f)
                keys = list(self.history.keys())
                self.number_epochs = len(self.history[keys[0]])
                logger.info(
                    "loaded history of %d previous epochs", self.number_epochs
                )
                last_output = f"Epoch {self.number_epochs}: "
                for key in keys:
                    if len(self.history[key]) > 0:
                        last_output += f"{key}: {self.history[key][-1]:.4f}"
                    if key != keys[-1]:
                        last_output += " - "
                logger.info(last_output)
        else:
            logger.info("Creating new history file %s", presets.history_file)
        for key in ["duration", "accuracy"]:
            if key not in self.history:
                self.history[key] = []

    def on_train_begin(self, logs=None):
        """
        Called at the beginning of training.

        Args:
            logs (dict): Currently no data is passed to this argument for this
                method but that may change in the future.
        """
        keys = list(self.history.keys())
        if len(keys) == 0:
            self.number_epochs = 0
        else:
            self.number_epochs = len(self.history[keys[0]])
        print(
            f"Starting new training with {self.number_epochs} "
            "previous epochs"
        )

    def on_epoch_end(self, epoch, logs=None):
        """
        Called at the end of each epoch.

        Arguments:
            epoch (int): The current epoch.

        Keyword Arguments:
            logs (dict): A dictionary of logs from the training process.
        """
        if "batch_size" not in self.history:
            self.history["batch_size"] = []
        self.history["batch_size"].append(self.presets.batch_size)
        for key in logs:
            if key not in self.history:
                self.history[key] = []
            self.history[key].append(logs[key])
        with open(self.presets.history_file, "wb") as f:
            pickle.dump(self.history, f)
            logger.info(
                "Epoch %d: history pickled and saved to file",
                epoch + self.number_epochs + 1,
            )

    def get_best_epoch(self, key):
        """
        get_best_epoch Get the best epoch so far.

        Arguments:
            history -- _description_
            key -- _description_

        Returns:
            _description_
        """
        max_value = 0
        max_epoch = 0
        if key not in self.history or len(self.history[key]) == 0:
            return 0, 0, 0, 0, 0
        for epoch in range(len(self.history[key])):
            value = self.history[key][epoch]
            if value >= max_value:  # We want the last, best value
                max_value = value
                max_epoch = epoch
        return (
            self.history["accuracy"][max_epoch],
            self.history["val_accuracy"][max_epoch],
            self.history["loss"][max_epoch],
            self.history["val_loss"][max_epoch],
            max_epoch,
        )
