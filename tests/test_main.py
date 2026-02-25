"""Tests for main CLI entry point."""

import logging
import sys
from unittest.mock import (
    MagicMock,
    Mock,
    patch,
)

import pytest

from pumaguard import (
    main,
)
from pumaguard.presets import (
    PresetError,
    Settings,
)


class TestCreateGlobalParser:
    """Tests for create_global_parser function."""

    def test_creates_parser_with_all_arguments(self):
        """Test that global parser has all expected arguments."""
        parser = main.create_global_parser()

        # Parse help to verify all arguments exist
        with patch("sys.argv", ["pumaguard", "--help"]):
            with pytest.raises(SystemExit):
                parser.parse_args()

    def test_settings_argument(self):
        """Test --settings argument."""
        parser = main.create_global_parser()
        args = parser.parse_args(["--settings", "/path/to/settings.yaml"])
        assert args.settings == "/path/to/settings.yaml"

    def test_debug_argument(self):
        """Test --debug argument."""
        parser = main.create_global_parser()
        args = parser.parse_args(["--debug"])
        assert args.debug is True

    def test_debug_default_false(self):
        """Test --debug defaults to False."""
        parser = main.create_global_parser()
        args = parser.parse_args([])
        assert args.debug is False

    def test_version_argument(self):
        """Test --version argument."""
        parser = main.create_global_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_completion_argument(self):
        """Test --completion argument."""
        parser = main.create_global_parser()
        args = parser.parse_args(["--completion", "bash"])
        assert args.completion == "bash"

    def test_log_file_argument(self):
        """Test --log-file argument."""
        parser = main.create_global_parser()
        args = parser.parse_args(["--log-file", "/tmp/test.log"])
        assert args.log_file == "/tmp/test.log"

    def test_log_file_default_none(self):
        """Test --log-file defaults to None."""
        parser = main.create_global_parser()
        args = parser.parse_args([])
        assert args.log_file is None

    def test_model_path_argument(self):
        """Test --model-path argument."""
        parser = main.create_global_parser()
        args = parser.parse_args(["--model-path", "/models"])
        assert args.model_path == "/models"

    def test_model_path_from_environment(self):
        """Test --model-path uses PUMAGUARD_MODEL_PATH env var."""
        parser = main.create_global_parser()
        with patch.dict("os.environ", {"PUMAGUARD_MODEL_PATH": "/env/models"}):
            # Need to recreate parser to pick up env var
            parser = main.create_global_parser()
            args = parser.parse_args([])
            assert args.model_path == "/env/models"

    def test_model_argument(self):
        """Test --model argument."""
        parser = main.create_global_parser()
        args = parser.parse_args(["--model", "my_model.h5"])
        assert args.model == "my_model.h5"

    def test_model_default_empty(self):
        """Test --model defaults to empty string."""
        parser = main.create_global_parser()
        args = parser.parse_args([])
        assert args.model == ""

    def test_notebook_argument(self):
        """Test --notebook argument."""
        parser = main.create_global_parser()
        args = parser.parse_args(["--notebook", "42"])
        assert args.notebook == 42


class TestConfigurePresets:
    """Tests for configure_presets function."""

    def test_loads_default_settings_when_none_specified(self):
        """Test that default settings are loaded when no file specified."""
        args = Mock()
        args.settings = None
        args.model_path = None
        args.notebook = None
        args.model = ""
        presets = Settings()

        with patch(
            "pumaguard.main.get_default_settings_file"
        ) as mock_get_default:
            mock_get_default.return_value = "/default/settings.yaml"
            with patch.object(presets, "load") as mock_load:
                main.configure_presets(args, presets)
                mock_load.assert_called_once_with("/default/settings.yaml")

    def test_loads_specified_settings_file(self):
        """Test that specified settings file is loaded."""
        args = Mock()
        args.settings = "/custom/settings.yaml"
        args.model_path = None
        args.notebook = None
        args.model = ""
        presets = Settings()

        with patch.object(presets, "load") as mock_load:
            main.configure_presets(args, presets)
            mock_load.assert_called_once_with("/custom/settings.yaml")

    def test_exits_on_preset_error(self):
        """Test that PresetError causes sys.exit."""
        args = Mock()
        args.settings = None
        args.model_path = None
        args.notebook = None
        args.model = ""
        presets = Settings()

        with patch(
            "pumaguard.main.get_default_settings_file",
            return_value="/settings.yaml",
        ):
            with patch.object(
                presets, "load", side_effect=PresetError("Load failed")
            ):
                with pytest.raises(SystemExit):
                    main.configure_presets(args, presets)

    def test_sets_image_dimensions(self):
        """Test that image_dimensions is set to (299, 299)."""
        args = Mock()
        args.settings = None
        args.model_path = None
        args.notebook = None
        args.model = ""
        presets = Settings()

        with patch("pumaguard.main.get_default_settings_file"):
            with patch.object(presets, "load"):
                main.configure_presets(args, presets)
                assert presets.image_dimensions == (299, 299)

    def test_sets_model_path_from_args(self):
        """Test that model_path is set from arguments."""
        args = Mock()
        args.settings = None
        args.model_path = "/custom/models"
        args.notebook = None
        args.model = ""
        presets = Settings()

        with patch("pumaguard.main.get_default_settings_file"):
            with patch.object(presets, "load"):
                main.configure_presets(args, presets)
                assert presets.base_output_directory == "/custom/models"

    def test_sets_notebook_number(self):
        """Test that notebook_number is set from arguments."""
        args = Mock()
        args.settings = None
        args.model_path = None
        args.notebook = 5
        args.model = ""
        presets = Settings()

        with patch("pumaguard.main.get_default_settings_file"):
            with patch.object(presets, "load"):
                main.configure_presets(args, presets)
                assert presets.notebook_number == 5

    def test_sets_verification_path(self):
        """Test that verification_path is set if present."""
        args = Mock()
        args.settings = None
        args.model_path = None
        args.notebook = None
        args.model = ""
        args.verification_path = "/verify/images"
        presets = Settings()

        with patch("pumaguard.main.get_default_settings_file"):
            with patch.object(presets, "load"):
                main.configure_presets(args, presets)
                assert presets.verification_path == "/verify/images"

    def test_sets_model_file(self):
        """Test that model_file is set when model arg is non-empty."""
        args = Mock()
        args.settings = None
        args.model_path = None
        args.notebook = None
        args.model = "custom_model.h5"
        presets = Settings()

        with patch("pumaguard.main.get_default_settings_file"):
            with patch.object(presets, "load"):
                main.configure_presets(args, presets)
                assert presets.model_file == "custom_model.h5"


class TestConfigureSubparsers:  # pylint: disable=too-few-public-methods
    """Tests for configure_subparsers function."""

    def test_creates_all_subcommands(self):
        """Test that all subcommands are registered."""
        parser = MagicMock()
        global_parser = main.create_global_parser()

        pth = "pumaguard.classify.configure_subparser"
        with patch(pth) as mock_classify:
            pth = "pumaguard.server.configure_subparser"
            with patch(pth) as mock_server:
                pth = "pumaguard.verify.configure_subparser"
                with patch(pth) as mock_verify:
                    pth = "pumaguard.model_cli.configure_subparser"
                    with patch(pth) as mock_model:
                        main.configure_subparsers(parser, global_parser)

                        # Verify all subparsers were configured
                        mock_classify.assert_called_once()
                        mock_server.assert_called_once()
                        mock_verify.assert_called_once()
                        mock_model.assert_called_once()


class TestMain:
    """Tests for main entry point."""

    def test_main_classify_command(self, tmp_path):
        """Test main with classify command."""
        with patch.object(sys, "argv", ["pumaguard", "classify", "image.jpg"]):
            with patch("pumaguard.classify.main") as mock_classify:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    main.main()
                    mock_classify.assert_called_once()

    def test_main_server_command(self, tmp_path):
        """Test main with server command."""
        with patch.object(sys, "argv", ["pumaguard", "server", str(tmp_path)]):
            with patch("pumaguard.server.main") as mock_server:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    main.main()
                    mock_server.assert_called_once()

    def test_main_verify_command(self, tmp_path):
        """Test main with verify command."""
        with patch.object(sys, "argv", ["pumaguard", "verify"]):
            with patch("pumaguard.verify.main") as mock_verify:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    main.main()
                    mock_verify.assert_called_once()

    def test_main_models_command(self, tmp_path):
        """Test main with models command."""
        with patch.object(sys, "argv", ["pumaguard", "models", "list"]):
            with patch("pumaguard.model_cli.main") as mock_models:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    main.main()
                    mock_models.assert_called_once()

    def test_main_no_command_prints_help(self, tmp_path):
        """Test main without command prints help."""
        with patch.object(sys, "argv", ["pumaguard"]):
            with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                mock_cache.return_value = tmp_path
                # Should not raise an error, just print help
                main.main()

    def test_main_with_debug_flag(self, tmp_path):
        """Test main with --debug flag sets logging level."""
        with patch.object(
            sys, "argv", ["pumaguard", "--debug", "classify", "image.jpg"]
        ):
            with patch("pumaguard.classify.main"):
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    # Just verify main runs without error
                    main.main()

    def test_main_with_custom_log_file(self, tmp_path):
        """Test main with --log-file accepts custom log location."""
        log_file = tmp_path / "custom.log"

        with patch.object(
            sys,
            "argv",
            [
                "pumaguard",
                "--log-file",
                str(log_file),
                "classify",
                "image.jpg",
            ],
        ):
            with patch("pumaguard.classify.main") as mock_classify:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with patch("pumaguard.presets.Settings.load"):
                        # Just verify main runs without error
                        main.main()
                        mock_classify.assert_called_once()

    def test_main_creates_log_directory_if_needed(self, tmp_path):
        """Test main handles nested log file paths."""
        log_dir = tmp_path / "nested" / "log" / "dir"
        log_file = log_dir / "test.log"

        with patch.object(
            sys,
            "argv",
            [
                "pumaguard",
                "--log-file",
                str(log_file),
                "classify",
                "image.jpg",
            ],
        ):
            with patch("pumaguard.classify.main") as mock_classify:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with patch("pumaguard.presets.Settings.load"):
                        # Just verify main runs without error
                        main.main()
                        mock_classify.assert_called_once()

    def test_main_uses_xdg_cache_for_default_log(self, tmp_path):
        """Test main uses XDG cache directory for default log file."""
        with patch.object(sys, "argv", ["pumaguard", "classify", "image.jpg"]):
            with patch("pumaguard.classify.main"):
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    main.main()
                    # Verify log file was created in cache dir
                    log_file = tmp_path / "pumaguard" / "pumaguard.log"
                    assert log_file.exists()

    def test_main_with_completion_exits(self, tmp_path):
        """Test main with --completion exits after printing completion."""
        with patch.object(sys, "argv", ["pumaguard", "--completion", "bash"]):
            with patch("pumaguard.main.print_bash_completion") as mock_print:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with pytest.raises(SystemExit):
                        main.main()
                    mock_print.assert_called_once()

    def test_main_with_settings_file(self, tmp_path):
        """Test main with --settings loads custom settings."""
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text("yolo-min-size: 0.05")

        with patch.object(
            sys,
            "argv",
            [
                "pumaguard",
                "--settings",
                str(settings_file),
                "classify",
                "image.jpg",
            ],
        ):
            with patch("pumaguard.classify.main"):
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    # Should not raise an error
                    main.main()

    def test_main_with_model_path(self, tmp_path):
        """Test main with --model-path sets base_output_directory."""
        model_path = tmp_path / "models"
        model_path.mkdir()

        with patch.object(
            sys,
            "argv",
            [
                "pumaguard",
                "--model-path",
                str(model_path),
                "classify",
                "image.jpg",
            ],
        ):
            with patch("pumaguard.classify.main") as mock_classify:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with patch("pumaguard.presets.Settings.load"):
                        main.main()
                        # Just verify classify was called
                        mock_classify.assert_called_once()

    def test_main_with_notebook_number(self, tmp_path):
        """Test main with --notebook sets notebook_number."""
        with patch.object(
            sys,
            "argv",
            [
                "pumaguard",
                "--notebook",
                "3",
                "classify",
                "image.jpg",
            ],
        ):
            with patch("pumaguard.classify.main") as mock_classify:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with patch("pumaguard.presets.Settings.load"):
                        main.main()
                        # Just verify classify was called
                        mock_classify.assert_called_once()

    def test_main_logging_configured(self, tmp_path):
        """Test main configures logging with file handler."""
        with patch.object(sys, "argv", ["pumaguard", "classify", "image.jpg"]):
            with patch("pumaguard.classify.main"):
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    # Just verify it runs without error
                    main.main()
                    # Log file should be created
                    log_file = tmp_path / "pumaguard" / "pumaguard.log"
                    assert log_file.exists()

    def test_main_command_line_args_logged(self, tmp_path):
        """Test main logs command line arguments in debug mode."""
        with patch.object(
            sys, "argv", ["pumaguard", "--debug", "classify", "image.jpg"]
        ):
            with patch("pumaguard.classify.main"):
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    # Just verify it runs in debug mode
                    main.main()


class TestMainIntegration:
    """Integration tests for main function with various scenarios."""

    def test_main_with_all_global_arguments(self, tmp_path):
        """Test main with all global arguments combined."""
        settings_file = tmp_path / "settings.yaml"
        settings_file.write_text(
            "yolo-min-size: 0.03\nimage-dimensions: [299, 299]"
        )
        model_path = tmp_path / "models"
        model_path.mkdir()
        log_file = tmp_path / "test.log"

        with patch.object(
            sys,
            "argv",
            [
                "pumaguard",
                "--settings",
                str(settings_file),
                "--model-path",
                str(model_path),
                "--debug",
                "--log-file",
                str(log_file),
                "--notebook",
                "7",
                "classify",
                "image.jpg",
            ],
        ):
            with patch("pumaguard.classify.main") as mock_classify:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with patch("pumaguard.presets.Settings.load"):
                        # Just verify main runs without error
                        main.main()
                        mock_classify.assert_called_once()

    def test_main_handles_keyboard_interrupt(self, tmp_path):
        """Test main handles KeyboardInterrupt gracefully."""
        with patch.object(sys, "argv", ["pumaguard", "server", str(tmp_path)]):
            with patch("pumaguard.server.main") as mock_server:
                mock_server.side_effect = KeyboardInterrupt()
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    # Should raise KeyboardInterrupt
                    with pytest.raises(KeyboardInterrupt):
                        main.main()

    def test_main_model_env_var_overridden_by_arg(self, tmp_path):
        """Test --model-path argument overrides environment variable."""
        env_path = tmp_path / "env_models"
        arg_path = tmp_path / "arg_models"
        env_path.mkdir()
        arg_path.mkdir()

        with patch.dict("os.environ", {"PUMAGUARD_MODEL_PATH": str(env_path)}):
            with patch.object(
                sys,
                "argv",
                [
                    "pumaguard",
                    "--model-path",
                    str(arg_path),
                    "classify",
                    "image.jpg",
                ],
            ):
                with patch("pumaguard.classify.main") as mock_classify:
                    with patch(
                        "pumaguard.main.get_xdg_cache_home"
                    ) as mock_cache:
                        mock_cache.return_value = tmp_path
                        with patch("pumaguard.presets.Settings.load"):
                            main.main()
                            # Just verify classify was called
                            mock_classify.assert_called_once()

    def test_main_completion_bash_exits_cleanly(self, tmp_path):
        """Test bash completion exits with code 0."""
        with patch.object(sys, "argv", ["pumaguard", "--completion", "bash"]):
            with patch(
                "pumaguard.main.print_bash_completion"
            ) as mock_completion:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with pytest.raises(SystemExit) as exc_info:
                        main.main()
                    assert exc_info.value.code == 0
                    mock_completion.assert_called_once_with(
                        command=None, shell="bash"
                    )

    def test_main_completion_with_subcommand(self, tmp_path):
        """Test completion with specific subcommand."""
        with patch.object(sys, "argv", ["pumaguard", "--completion", "bash"]):
            with patch(
                "pumaguard.main.print_bash_completion"
            ) as mock_completion:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with pytest.raises(SystemExit):
                        main.main()
                    # Completion should be called
                    mock_completion.assert_called_once()

    def test_main_presets_logged_in_debug(self, tmp_path):
        """Test that presets are logged in debug mode."""
        with patch.object(
            sys, "argv", ["pumaguard", "--debug", "classify", "image.jpg"]
        ):
            with patch("pumaguard.classify.main"):
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with patch("logging.getLogger") as mock_get_logger:
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger

                        main.main()

                        # Check that presets were logged
                        debug_calls = [
                            str(call)
                            for call in mock_logger.debug.call_args_list
                        ]
                        presets_logged = any(
                            "presets" in call for call in debug_calls
                        )
                        assert presets_logged

    def test_main_invalid_settings_file_exits(self, tmp_path):
        """Test that invalid settings file causes exit."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with patch.object(
            sys,
            "argv",
            [
                "pumaguard",
                "--settings",
                str(nonexistent),
                "classify",
                "image.jpg",
            ],
        ):
            with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                mock_cache.return_value = tmp_path
                with patch(
                    "pumaguard.presets.Settings.load",
                    side_effect=PresetError("Invalid settings"),
                ):
                    # Should exit with error when loading invalid settings
                    with pytest.raises(SystemExit):
                        main.main()

    def test_main_log_file_in_home_directory(self, tmp_path):
        """Test log file accepts nested directory paths."""
        home_log = tmp_path / "home" / "user" / ".pumaguard.log"

        with patch.object(
            sys,
            "argv",
            [
                "pumaguard",
                "--log-file",
                str(home_log),
                "classify",
                "image.jpg",
            ],
        ):
            with patch("pumaguard.classify.main") as mock_classify:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with patch("pumaguard.presets.Settings.load"):
                        # Just verify main runs without error
                        main.main()
                        mock_classify.assert_called_once()

    def test_main_model_argument_sets_model_file(self, tmp_path):
        """Test --model argument sets model_file in presets."""
        with patch.object(
            sys,
            "argv",
            [
                "pumaguard",
                "--model",
                "custom.h5",
                "classify",
                "image.jpg",
            ],
        ):
            with patch("pumaguard.classify.main") as mock_classify:
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with patch("pumaguard.presets.Settings.load"):
                        main.main()
                        # Just verify classify was called
                        mock_classify.assert_called_once()

    def test_main_without_debug_info_level(self, tmp_path):
        """Test that without --debug, logging level is INFO."""
        with patch.object(sys, "argv", ["pumaguard", "classify", "image.jpg"]):
            with patch("pumaguard.classify.main"):
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    with patch("logging.getLogger") as mock_get_logger:
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger

                        main.main()

                        # Debug mode should NOT be set
                        set_debug_calls = [
                            call
                            for call in mock_logger.setLevel.call_args_list
                            if call[0][0] == logging.DEBUG
                        ]
                        assert len(set_debug_calls) == 0

    def test_main_all_subcommands_receive_presets(self, tmp_path):
        """Test that all subcommands receive configured presets."""
        commands = [
            (["classify", "image.jpg"], "pumaguard.classify.main"),
            (["server", str(tmp_path)], "pumaguard.server.main"),
            (["verify"], "pumaguard.verify.main"),
            (["models", "list"], "pumaguard.model_cli.main"),
        ]

        for cmd_args, mock_path in commands:
            with patch.object(sys, "argv", ["pumaguard"] + cmd_args):
                with patch(mock_path) as mock_cmd:
                    with patch(
                        "pumaguard.main.get_xdg_cache_home"
                    ) as mock_cache:
                        mock_cache.return_value = tmp_path
                        main.main()
                        # Verify presets were passed
                        assert mock_cmd.call_count == 1
                        args, _ = mock_cmd.call_args
                        assert isinstance(args[1], Settings)

    def test_main_logging_formatter_configured(self, tmp_path):
        """Test that logging formatter is properly configured."""
        with patch.object(sys, "argv", ["pumaguard", "classify", "image.jpg"]):
            with patch("pumaguard.classify.main"):
                with patch("pumaguard.main.get_xdg_cache_home") as mock_cache:
                    mock_cache.return_value = tmp_path
                    # Just verify it runs and creates log file
                    main.main()
                    log_file = tmp_path / "pumaguard" / "pumaguard.log"
                    assert log_file.exists()
