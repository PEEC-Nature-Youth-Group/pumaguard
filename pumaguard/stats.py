"""
Module for statistics and plotting.
"""

import matplotlib.pyplot as plt


def plot_training_progress(filename, full_history):
    """
    Plot the training progress and store in file.
    """
    plt.figure(figsize=(18, 10))
    plt.subplot(1, 2, 1)
    plt.plot(full_history.history["accuracy"], label="Training Accuracy")
    plt.plot(full_history.history["val_accuracy"], label="Validation Accuracy")
    plt.legend(loc="lower right")
    plt.ylabel("Accuracy")
    plt.ylim([min(plt.ylim()), 1])
    plt.title("Training and Validation Accuracy")

    plt.subplot(1, 2, 2)
    plt.plot(full_history.history["loss"], label="Training Loss")
    plt.plot(full_history.history["val_loss"], label="Validation Loss")
    plt.legend(loc="upper right")
    plt.ylabel("Cross Entropy")
    plt.ylim([0, 1.0])
    plt.title("Training and Validation Loss")

    print("Created plot of learning history")
    plt.savefig(filename)
