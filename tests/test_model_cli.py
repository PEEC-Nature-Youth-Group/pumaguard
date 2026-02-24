"""Tests for model CLI commands."""

# pylint: disable=redefined-outer-name,unused-argument
# Pytest fixtures intentionally redefine names, some used for setup

import argparse
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from pumaguard.model_cli import (
    configure_subparser,
    main,
)
from pumaguard.presets import (
    Settings,
)


@pytest.fixture
def mock_presets():
    """Create a mock Settings instance."""
    return MagicMock(spec=Settings)


@pytest.fixture
def parser():
    """Create an ArgumentParser with model subparser configured."""
    parser = argparse.ArgumentParser()
    configure_subparser(parser)
    return parser


def test_configure_subparser_creates_subparsers(parser):
    """Test that configure_subparser creates the model subparsers."""
    # Parse with list action
    args = parser.parse_args(["list"])
    assert args.model_action == "list"

    # Parse with clear action
    args = parser.parse_args(["clear"])
    assert args.model_action == "clear"

    # Parse with export action
    args = parser.parse_args(["export"])
    assert args.model_action == "export"

    # Parse with cache action
    args = parser.parse_args(["cache"])
    assert args.model_action == "cache"


def test_configure_subparser_list_help(parser):
    """Test that list subparser has help text."""
    # This will raise SystemExit with help text
    with pytest.raises(SystemExit):
        parser.parse_args(["list", "--help"])


def test_configure_subparser_clear_help(parser):
    """Test that clear subparser has help text."""
    with pytest.raises(SystemExit):
        parser.parse_args(["clear", "--help"])


def test_configure_subparser_export_help(parser):
    """Test that export subparser has help text."""
    with pytest.raises(SystemExit):
        parser.parse_args(["export", "--help"])


def test_configure_subparser_cache_help(parser):
    """Test that cache subparser has help text."""
    with pytest.raises(SystemExit):
        parser.parse_args(["cache", "--help"])


@patch("pumaguard.model_cli.list_available_models")
def test_main_list_action(mock_list, parser, mock_presets):
    """Test main with list action."""
    mock_list.return_value = ["model1.h5", "model2.h5", "yolov8s.pt"]

    args = parser.parse_args(["list"])
    main(args, mock_presets)

    mock_list.assert_called_once()


@patch("pumaguard.model_cli.list_available_models")
def test_main_list_action_empty(mock_list, parser, mock_presets):
    """Test main with list action when no models available."""
    mock_list.return_value = []

    args = parser.parse_args(["list"])
    main(args, mock_presets)

    mock_list.assert_called_once()


@patch("pumaguard.model_cli.list_available_models")
def test_main_list_action_logs_models(mock_list, parser, mock_presets, caplog):
    """Test main with list action logs model names."""
    mock_list.return_value = ["model1.h5", "model2.h5"]

    args = parser.parse_args(["list"])

    with caplog.at_level("INFO"):
        main(args, mock_presets)

    # Check that models were logged
    assert "Available Models" in caplog.text
    assert "model1.h5" in caplog.text
    assert "model2.h5" in caplog.text


@patch("pumaguard.model_cli.clear_model_cache")
def test_main_clear_action(mock_clear, parser, mock_presets):
    """Test main with clear action."""
    args = parser.parse_args(["clear"])
    main(args, mock_presets)

    mock_clear.assert_called_once()


@patch("pumaguard.model_cli.export_registry")
def test_main_export_action(mock_export, parser, mock_presets):
    """Test main with export action."""
    args = parser.parse_args(["export"])
    main(args, mock_presets)

    mock_export.assert_called_once()


@patch("pumaguard.model_cli.cache_models")
def test_main_cache_action(mock_cache, parser, mock_presets):
    """Test main with cache action."""
    args = parser.parse_args(["cache"])
    main(args, mock_presets)

    mock_cache.assert_called_once()


def test_main_no_action(parser, mock_presets, caplog):
    """Test main with no action specified."""
    # Create args namespace without model_action
    args = argparse.Namespace(model_action=None)

    with caplog.at_level("ERROR"):
        main(args, mock_presets)

    assert "What do you want to do with the models?" in caplog.text


def test_main_invalid_action(parser, mock_presets, caplog):
    """Test main with invalid action."""
    # Create args namespace with invalid action
    args = argparse.Namespace(model_action="invalid")

    with caplog.at_level("ERROR"):
        main(args, mock_presets)

    assert "What do you want to do with the models?" in caplog.text


@patch("pumaguard.model_cli.clear_model_cache")
def test_main_clear_action_exception_handling(
    mock_clear, parser, mock_presets
):
    """Test main handles exceptions during clear action."""
    mock_clear.side_effect = Exception("Clear failed")

    args = parser.parse_args(["clear"])

    # Should propagate exception
    with pytest.raises(Exception, match="Clear failed"):
        main(args, mock_presets)


@patch("pumaguard.model_cli.export_registry")
def test_main_export_action_exception_handling(
    mock_export, parser, mock_presets
):
    """Test main handles exceptions during export action."""
    mock_export.side_effect = Exception("Export failed")

    args = parser.parse_args(["export"])

    # Should propagate exception
    with pytest.raises(Exception, match="Export failed"):
        main(args, mock_presets)


@patch("pumaguard.model_cli.cache_models")
def test_main_cache_action_exception_handling(
    mock_cache, parser, mock_presets
):
    """Test main handles exceptions during cache action."""
    mock_cache.side_effect = Exception("Cache failed")

    args = parser.parse_args(["cache"])

    # Should propagate exception
    with pytest.raises(Exception, match="Cache failed"):
        main(args, mock_presets)


@patch("pumaguard.model_cli.list_available_models")
def test_main_list_action_with_many_models(
    mock_list, parser, mock_presets, caplog
):
    """Test main with list action when many models available."""
    many_models = [f"model{i}.h5" for i in range(10)]
    mock_list.return_value = many_models

    args = parser.parse_args(["list"])

    with caplog.at_level("INFO"):
        main(args, mock_presets)

    # Verify all models are logged
    for model in many_models:
        assert model in caplog.text


def test_configure_subparser_no_extra_arguments():
    """Test that subparsers don't accept extra arguments."""
    parser = argparse.ArgumentParser()
    configure_subparser(parser)

    # list should not accept extra arguments
    with pytest.raises(SystemExit):
        parser.parse_args(["list", "extra_arg"])


def test_configure_subparser_preserves_dest():
    """Test that subparsers use correct dest for model_action."""
    parser = argparse.ArgumentParser()
    configure_subparser(parser)

    args = parser.parse_args(["list"])
    assert hasattr(args, "model_action")
    assert args.model_action == "list"


@patch("pumaguard.model_cli.list_available_models")
def test_main_list_single_model(mock_list, parser, mock_presets, caplog):
    """Test main with list action when only one model available."""
    mock_list.return_value = ["single_model.h5"]

    args = parser.parse_args(["list"])

    with caplog.at_level("INFO"):
        main(args, mock_presets)

    assert "Available Models" in caplog.text
    assert "single_model.h5" in caplog.text


def test_parser_accepts_only_valid_actions():
    """Test that parser only accepts defined actions."""
    parser = argparse.ArgumentParser()
    configure_subparser(parser)

    # Valid actions should work
    valid_actions = ["list", "clear", "export", "cache"]
    for action in valid_actions:
        args = parser.parse_args([action])
        assert args.model_action == action

    # Invalid action should fail
    with pytest.raises(SystemExit):
        parser.parse_args(["invalid_action"])
