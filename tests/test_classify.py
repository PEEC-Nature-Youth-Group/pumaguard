"""Tests for classify module."""

import argparse
import logging
from unittest.mock import (
    MagicMock,
    patch,
)

from pumaguard.classify import (
    configure_subparser,
    main,
)
from pumaguard.presets import (
    Settings,
)


class TestConfigureSubparser:
    """Test configure_subparser function."""

    def test_configure_subparser_adds_image_argument(self):
        """Test that configure_subparser adds the image argument."""
        parser = argparse.ArgumentParser()
        configure_subparser(parser)

        # Parse with image arguments
        args = parser.parse_args(["image1.jpg", "image2.jpg"])
        assert args.image == ["image1.jpg", "image2.jpg"]

    def test_configure_subparser_accepts_no_images(self):
        """Test that configure_subparser accepts no images."""
        parser = argparse.ArgumentParser()
        configure_subparser(parser)

        # Parse with no arguments
        args = parser.parse_args([])
        assert args.image == []

    def test_configure_subparser_accepts_single_image(self):
        """Test that configure_subparser accepts a single image."""
        parser = argparse.ArgumentParser()
        configure_subparser(parser)

        # Parse with single argument
        args = parser.parse_args(["single.jpg"])
        assert args.image == ["single.jpg"]


class TestMain:
    """Test main function."""

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_classifies_images_with_lion_detection(
        self, mock_classify, capsys
    ):
        """Test main classifies images and prints lion detection."""
        mock_classify.return_value = 0.75  # 75% lion probability
        presets = MagicMock(spec=Settings)

        options = argparse.Namespace(image=["test_image.jpg"])
        main(options, presets)

        mock_classify.assert_called_once_with(
            presets=presets, image_path="test_image.jpg"
        )

        captured = capsys.readouterr()
        assert "test_image.jpg" in captured.out
        assert "75.00% lion" in captured.out
        assert "(lion)" in captured.out

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_classifies_images_without_lion_detection(
        self, mock_classify, capsys
    ):
        """Test main classifies images and prints no lion detection."""
        mock_classify.return_value = 0.25  # 25% lion probability
        presets = MagicMock(spec=Settings)

        options = argparse.Namespace(image=["test_image.jpg"])
        main(options, presets)

        mock_classify.assert_called_once_with(
            presets=presets, image_path="test_image.jpg"
        )

        captured = capsys.readouterr()
        assert "test_image.jpg" in captured.out
        assert "25.00% lion" in captured.out
        assert "(no lion)" in captured.out

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_classifies_boundary_case_exactly_50_percent(
        self, mock_classify, capsys
    ):
        """Test main with exactly 50% probability (boundary case)."""
        mock_classify.return_value = 0.5
        presets = MagicMock(spec=Settings)

        options = argparse.Namespace(image=["test_image.jpg"])
        main(options, presets)

        captured = capsys.readouterr()
        assert "50.00% lion" in captured.out
        assert "(no lion)" in captured.out  # 0.5 is not > 0.5

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_classifies_boundary_case_just_above_threshold(
        self, mock_classify, capsys
    ):
        """Test main with just above 50% probability."""
        mock_classify.return_value = 0.51
        presets = MagicMock(spec=Settings)

        options = argparse.Namespace(image=["test_image.jpg"])
        main(options, presets)

        captured = capsys.readouterr()
        assert "51.00% lion" in captured.out
        assert "(lion)" in captured.out

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_classifies_multiple_images(self, mock_classify, capsys):
        """Test main classifies multiple images."""
        mock_classify.side_effect = [0.8, 0.3, 0.6]
        presets = MagicMock(spec=Settings)

        options = argparse.Namespace(
            image=["image1.jpg", "image2.jpg", "image3.jpg"]
        )
        main(options, presets)

        assert mock_classify.call_count == 3
        captured = capsys.readouterr()
        assert "image1.jpg" in captured.out
        assert "80.00% lion" in captured.out
        assert "image2.jpg" in captured.out
        assert "30.00% lion" in captured.out
        assert "image3.jpg" in captured.out
        assert "60.00% lion" in captured.out

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_handles_negative_prediction(
        self, mock_classify, caplog, capsys
    ):
        """Test main handles negative prediction values."""
        mock_classify.return_value = -1
        presets = MagicMock(spec=Settings)

        with caplog.at_level(logging.WARNING):
            options = argparse.Namespace(image=["test_image.jpg"])
            main(options, presets)

        # Should log warning but not print prediction
        assert "predicted label < 0!" in caplog.text
        captured = capsys.readouterr()
        assert "test_image.jpg" not in captured.out

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_handles_zero_prediction(self, mock_classify, capsys):
        """Test main handles zero prediction."""
        mock_classify.return_value = 0.0
        presets = MagicMock(spec=Settings)

        options = argparse.Namespace(image=["test_image.jpg"])
        main(options, presets)

        captured = capsys.readouterr()
        assert "test_image.jpg" in captured.out
        assert "0.00% lion" in captured.out
        assert "(no lion)" in captured.out

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_handles_one_prediction(self, mock_classify, capsys):
        """Test main handles 100% prediction."""
        mock_classify.return_value = 1.0
        presets = MagicMock(spec=Settings)

        options = argparse.Namespace(image=["test_image.jpg"])
        main(options, presets)

        captured = capsys.readouterr()
        assert "test_image.jpg" in captured.out
        assert "100.00% lion" in captured.out
        assert "(lion)" in captured.out

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_with_empty_image_list(self, mock_classify):
        """Test main with empty image list."""
        presets = MagicMock(spec=Settings)

        options = argparse.Namespace(image=[])
        main(options, presets)

        # Should not call classify if no images
        mock_classify.assert_not_called()

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_handles_mixed_predictions(
        self, mock_classify, caplog, capsys
    ):
        """Test main handles mix of valid and invalid predictions."""
        mock_classify.side_effect = [0.7, -1, 0.4]
        presets = MagicMock(spec=Settings)

        with caplog.at_level(logging.WARNING):
            options = argparse.Namespace(
                image=["image1.jpg", "image2.jpg", "image3.jpg"]
            )
            main(options, presets)

        captured = capsys.readouterr()
        # Valid predictions should be printed
        assert "image1.jpg" in captured.out
        assert "70.00% lion" in captured.out
        assert "image3.jpg" in captured.out
        assert "40.00% lion" in captured.out

        # Invalid prediction should be logged
        assert "predicted label < 0!" in caplog.text

    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_calls_with_correct_parameters(self, mock_classify):
        """Test main passes correct parameters to classify function."""
        mock_classify.return_value = 0.5
        presets = MagicMock(spec=Settings)
        image_path = "specific_path/to/image.jpg"

        options = argparse.Namespace(image=[image_path])
        main(options, presets)

        mock_classify.assert_called_once_with(
            presets=presets, image_path=image_path
        )

    @patch("pumaguard.classify.logger")
    @patch("pumaguard.classify.classify_image_two_stage")
    def test_main_logs_debug_message(self, mock_classify, mock_logger):
        """Test main logs debug message at start."""
        mock_classify.return_value = 0.5
        presets = MagicMock(spec=Settings)

        options = argparse.Namespace(image=["test.jpg"])
        main(options, presets)

        mock_logger.debug.assert_called_once_with("starting classify")
