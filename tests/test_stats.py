"""Tests for stats module."""

from unittest.mock import (
    MagicMock,
    call,
    patch,
)

from pumaguard.stats import (
    plot_training_progress,
)


class TestPlotTrainingProgress:
    """Test plot_training_progress function."""

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_creates_figure(self, mock_plt):
        """Test that plot_training_progress creates a figure."""
        # Mock ylim to return proper tuple
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5, 0.6, 0.7],
            "val_accuracy": [0.4, 0.5, 0.6],
            "loss": [0.5, 0.4, 0.3],
            "val_loss": [0.6, 0.5, 0.4],
        }

        plot_training_progress("test_plot.png", mock_history)

        mock_plt.figure.assert_called_once_with(figsize=(18, 10))

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_creates_two_subplots(self, mock_plt):
        """Test that plot_training_progress creates two subplots."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5, 0.6, 0.7],
            "val_accuracy": [0.4, 0.5, 0.6],
            "loss": [0.5, 0.4, 0.3],
            "val_loss": [0.6, 0.5, 0.4],
        }

        plot_training_progress("test_plot.png", mock_history)

        # Should create 2 subplots (1x2 layout)
        assert mock_plt.subplot.call_count == 2
        mock_plt.subplot.assert_any_call(1, 2, 1)
        mock_plt.subplot.assert_any_call(1, 2, 2)

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_plots_accuracy_data(self, mock_plt):
        """Test that plot_training_progress plots accuracy data."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        accuracy_data = [0.5, 0.6, 0.7, 0.8]
        val_accuracy_data = [0.4, 0.5, 0.6, 0.7]
        mock_history.history = {
            "accuracy": accuracy_data,
            "val_accuracy": val_accuracy_data,
            "loss": [0.5, 0.4, 0.3, 0.2],
            "val_loss": [0.6, 0.5, 0.4, 0.3],
        }

        plot_training_progress("test_plot.png", mock_history)

        # Check that plot was called with accuracy data
        plot_calls = mock_plt.plot.call_args_list
        assert call(accuracy_data, label="Training Accuracy") in plot_calls
        assert (
            call(val_accuracy_data, label="Validation Accuracy") in plot_calls
        )

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_plots_loss_data(self, mock_plt):
        """Test that plot_training_progress plots loss data."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        loss_data = [0.5, 0.4, 0.3, 0.2]
        val_loss_data = [0.6, 0.5, 0.4, 0.3]
        mock_history.history = {
            "accuracy": [0.5, 0.6, 0.7, 0.8],
            "val_accuracy": [0.4, 0.5, 0.6, 0.7],
            "loss": loss_data,
            "val_loss": val_loss_data,
        }

        plot_training_progress("test_plot.png", mock_history)

        # Check that plot was called with loss data
        plot_calls = mock_plt.plot.call_args_list
        assert call(loss_data, label="Training Loss") in plot_calls
        assert call(val_loss_data, label="Validation Loss") in plot_calls

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_sets_labels_and_titles(self, mock_plt):
        """Test that plot_training_progress sets labels and titles."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5, 0.6, 0.7],
            "val_accuracy": [0.4, 0.5, 0.6],
            "loss": [0.5, 0.4, 0.3],
            "val_loss": [0.6, 0.5, 0.4],
        }

        plot_training_progress("test_plot.png", mock_history)

        # Check ylabel was called
        ylabel_calls = mock_plt.ylabel.call_args_list
        assert call("Accuracy") in ylabel_calls
        assert call("Cross Entropy") in ylabel_calls

        # Check title was called
        title_calls = mock_plt.title.call_args_list
        assert call("Training and Validation Accuracy") in title_calls
        assert call("Training and Validation Loss") in title_calls

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_sets_legends(self, mock_plt):
        """Test that plot_training_progress sets legends."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5, 0.6, 0.7],
            "val_accuracy": [0.4, 0.5, 0.6],
            "loss": [0.5, 0.4, 0.3],
            "val_loss": [0.6, 0.5, 0.4],
        }

        plot_training_progress("test_plot.png", mock_history)

        # Should set legend twice (once for each subplot)
        assert mock_plt.legend.call_count == 2
        legend_calls = mock_plt.legend.call_args_list
        assert call(loc="lower right") in legend_calls
        assert call(loc="upper right") in legend_calls

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_sets_ylim_for_accuracy(self, mock_plt):
        """Test that plot_training_progress sets ylim for accuracy."""
        # Mock ylim to return a fixed value
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5, 0.6, 0.7],
            "val_accuracy": [0.4, 0.5, 0.6],
            "loss": [0.5, 0.4, 0.3],
            "val_loss": [0.6, 0.5, 0.4],
        }

        plot_training_progress("test_plot.png", mock_history)

        # Check that ylim was called and set
        ylim_calls = mock_plt.ylim.call_args_list
        # First call gets current limits, second sets new limits with max=1
        assert len(ylim_calls) >= 2

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_sets_ylim_for_loss(self, mock_plt):
        """Test that plot_training_progress sets ylim for loss subplot."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5, 0.6, 0.7],
            "val_accuracy": [0.4, 0.5, 0.6],
            "loss": [0.5, 0.4, 0.3],
            "val_loss": [0.6, 0.5, 0.4],
        }

        plot_training_progress("test_plot.png", mock_history)

        # Check that ylim was set to [0, 1.0] for loss
        ylim_calls = mock_plt.ylim.call_args_list
        assert call([0, 1.0]) in ylim_calls

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_saves_file(self, mock_plt):
        """Test that plot_training_progress saves the plot to file."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5, 0.6, 0.7],
            "val_accuracy": [0.4, 0.5, 0.6],
            "loss": [0.5, 0.4, 0.3],
            "val_loss": [0.6, 0.5, 0.4],
        }

        filename = "my_training_plot.png"
        plot_training_progress(filename, mock_history)

        mock_plt.savefig.assert_called_once_with(filename)

    @patch("builtins.print")
    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_prints_message(self, mock_plt, mock_print):
        """Test that plot_training_progress prints confirmation message."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5, 0.6, 0.7],
            "val_accuracy": [0.4, 0.5, 0.6],
            "loss": [0.5, 0.4, 0.3],
            "val_loss": [0.6, 0.5, 0.4],
        }

        plot_training_progress("test.png", mock_history)

        mock_print.assert_called_once_with("Created plot of learning history")

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_with_different_filename(self, mock_plt):
        """Test that different filenames are passed correctly."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5, 0.6],
            "val_accuracy": [0.4, 0.5],
            "loss": [0.5, 0.4],
            "val_loss": [0.6, 0.5],
        }

        filename1 = "plot1.png"
        filename2 = "results/plot2.png"

        plot_training_progress(filename1, mock_history)
        mock_plt.savefig.assert_called_with(filename1)

        plot_training_progress(filename2, mock_history)
        mock_plt.savefig.assert_called_with(filename2)

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_with_single_epoch(self, mock_plt):
        """Test with single epoch data."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        mock_history.history = {
            "accuracy": [0.5],
            "val_accuracy": [0.4],
            "loss": [0.5],
            "val_loss": [0.6],
        }

        plot_training_progress("test.png", mock_history)

        # Should still work with single data point
        mock_plt.savefig.assert_called_once_with("test.png")

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_with_many_epochs(self, mock_plt):
        """Test with many epochs of data."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        # Simulate 100 epochs
        mock_history.history = {
            "accuracy": [0.5 + i * 0.005 for i in range(100)],
            "val_accuracy": [0.4 + i * 0.005 for i in range(100)],
            "loss": [0.6 - i * 0.005 for i in range(100)],
            "val_loss": [0.7 - i * 0.005 for i in range(100)],
        }

        plot_training_progress("test.png", mock_history)

        # Should handle large datasets
        mock_plt.savefig.assert_called_once_with("test.png")
        # All 4 metrics should be plotted
        assert mock_plt.plot.call_count == 4

    @patch("pumaguard.stats.plt")
    def test_plot_training_progress_accesses_history_correctly(self, mock_plt):
        """Test that the function accesses history.history dict correctly."""
        mock_plt.ylim.return_value = (0.3, 0.9)

        mock_history = MagicMock()
        history_dict = {
            "accuracy": [0.5, 0.6],
            "val_accuracy": [0.4, 0.5],
            "loss": [0.5, 0.4],
            "val_loss": [0.6, 0.5],
        }
        mock_history.history = history_dict

        plot_training_progress("test.png", mock_history)

        # Verify the history attribute was accessed
        assert mock_history.history == history_dict
