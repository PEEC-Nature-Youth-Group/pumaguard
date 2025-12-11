"""Settings routes for loading, saving, and updating presets."""

from __future__ import (
    annotations,
)

import logging
import os
from typing import (
    TYPE_CHECKING,
)

import yaml
from flask import (
    jsonify,
    request,
)
from yaml.representer import (
    YAMLError,
)

from pumaguard.model_downloader import (
    MODEL_REGISTRY,
    get_models_directory,
    list_available_models,
    verify_file_checksum,
)
from pumaguard.sound import (
    is_playing,
    playsound,
    stop_sound,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


def register_settings_routes(app: "Flask", webui: "WebUI") -> None:
    """Register settings endpoints for GET, PUT, save, and load."""

    @app.route("/api/settings", methods=["GET"])
    def get_settings():
        return jsonify(dict(webui.presets))

    @app.route("/api/settings", methods=["PUT"])
    def update_settings():
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400

            allowed_settings = [
                "YOLO-min-size",
                "YOLO-conf-thresh",
                "YOLO-max-dets",
                "YOLO-model-filename",
                "classifier-model-filename",
                "deterrent-sound-file",
                "file-stabilization-extra-wait",
                "play-sound",
                "volume",
                "camera-url",
            ]

            if len(data) == 0:
                raise ValueError("Did not receive any settings")

            for key, value in data.items():
                if key in allowed_settings:
                    logger.info(
                        "Updating setting %s with value %s", key, value
                    )
                    attr_name = key.replace("-", "_").replace("YOLO_", "yolo_")
                    setattr(webui.presets, attr_name, value)
                    # Log verification of volume setting
                    if key == "volume":
                        logger.info(
                            "Volume setting updated to %d, verified: %d",
                            value,
                            webui.presets.volume,
                        )
                else:
                    logger.debug("Skipping unknown/read-only setting: %s", key)

            try:
                filepath = webui.presets.settings_file
                settings_dict = dict(webui.presets)
                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.dump(settings_dict, f, default_flow_style=False)
                logger.info(
                    "Settings updated and saved to %s (volume: %d)",
                    filepath,
                    webui.presets.volume,
                )
            except YAMLError:
                logger.exception("Error saving settings")
                return (
                    jsonify(
                        {
                            "error": (
                                "Settings updated but failed to save due "
                                "to an internal error"
                            )
                        }
                    ),
                    500,
                )

            return jsonify(
                {"success": True, "message": "Settings updated and saved"}
            )
        except ValueError as e:  # pragma: no cover (unexpected)
            logger.error("Error updating settings: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/save", methods=["POST"])
    def save_settings():
        data = request.json
        filepath = data.get("filepath") if data else None
        if not filepath:
            filepath = webui.presets.settings_file
        settings_dict = dict(webui.presets)
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(settings_dict, f, default_flow_style=False)
        logger.info("Settings saved to %s", filepath)
        return jsonify({"success": True, "filepath": filepath})

    @app.route("/api/settings/load", methods=["POST"])
    def load_settings():
        data = request.json
        filepath = data.get("filepath") if data else None
        if not filepath:
            return jsonify({"error": "No filepath provided"}), 400
        webui.presets.load(filepath)
        logger.info("Settings loaded from %s", filepath)
        return jsonify({"success": True, "message": "Settings loaded"})

    @app.route("/api/settings/test-sound", methods=["POST"])
    def test_sound():
        """Test the configured deterrent sound."""
        try:
            sound_file = webui.presets.deterrent_sound_file
            if not sound_file:
                return (
                    jsonify({"error": "No sound file configured"}),
                    400,
                )

            # Combine sound_path with deterrent_sound_file
            sound_file_path = os.path.join(
                webui.presets.sound_path, sound_file
            )

            # Check if file exists
            if not os.path.exists(sound_file_path):
                return (
                    jsonify(
                        {"error": (f"Sound file not found: {sound_file_path}")}
                    ),
                    404,
                )

            # Play the sound with configured volume (non-blocking)
            volume = webui.presets.volume
            logger.info(
                "Testing sound playback: file=%s, volume=%d",
                sound_file_path,
                volume,
            )
            logger.debug(
                "Current presets.volume value before playsound: %d",
                webui.presets.volume,
            )
            playsound(sound_file_path, volume, blocking=False)
            return jsonify(
                {
                    "success": True,
                    "message": f"Sound started: {sound_file}",
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error testing sound")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/stop-sound", methods=["POST"])
    def stop_test_sound():
        """Stop the currently playing test sound."""
        try:
            stopped = stop_sound()
            if stopped:
                logger.info("Sound playback stopped")
                return jsonify(
                    {
                        "success": True,
                        "message": "Sound stopped",
                    }
                )
            return jsonify(
                {
                    "success": True,
                    "message": "No sound was playing",
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error stopping sound")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/sound-status", methods=["GET"])
    def get_sound_status():
        """Check if a sound is currently playing."""
        try:
            playing = is_playing()
            return jsonify(
                {
                    "playing": playing,
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error checking sound status")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/models/available", methods=["GET"])
    def get_available_models():
        """Get list of available models with cache status.

        Query parameters:
            type: 'classifier' (*.h5 files) or 'yolo' (*.pt files)
                  Default: 'classifier'
        """
        try:
            model_type = request.args.get("type", "classifier")
            models_dir = get_models_directory()
            available_models = list_available_models()

            # Filter based on model type
            if model_type == "yolo":
                filtered_models = [
                    model
                    for model in available_models
                    if model.endswith(".pt")
                ]
            else:  # Default to classifier
                filtered_models = [
                    model
                    for model in available_models
                    if model.endswith(".h5")
                ]

            model_list = []
            for model_name in filtered_models:
                model_path = models_dir / model_name
                is_cached = False

                # Check if model exists and verify checksum
                if model_path.exists():
                    model_info = MODEL_REGISTRY[model_name]
                    sha256 = model_info.get("sha256")
                    if isinstance(sha256, str):
                        is_cached = verify_file_checksum(model_path, sha256)

                # Get model size info
                size_mb = None
                if model_path.exists():
                    size_mb = model_path.stat().st_size / (1024 * 1024)

                model_list.append(
                    {
                        "name": model_name,
                        "cached": is_cached,
                        "size_mb": size_mb,
                    }
                )

            # Sort models: cached first, then by name
            model_list.sort(key=lambda x: (not x["cached"], x["name"]))

            return jsonify({"models": model_list})

        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error getting available models")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/sounds/available", methods=["GET"])
    def get_available_sounds():
        """Get list of available sound files with file sizes."""
        try:
            sound_path = webui.presets.sound_path
            if not os.path.exists(sound_path):
                return (
                    jsonify({"error": f"Sound path not found: {sound_path}"}),
                    404,
                )

            # Supported audio formats
            audio_extensions = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}

            sound_files = []
            for filename in os.listdir(sound_path):
                filepath = os.path.join(sound_path, filename)
                if os.path.isfile(filepath):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in audio_extensions:
                        size_mb = os.path.getsize(filepath) / (1024 * 1024)
                        sound_files.append(
                            {
                                "name": filename,
                                "size_mb": size_mb,
                            }
                        )

            # Sort by name
            sound_files.sort(key=lambda x: x["name"])

            return jsonify({"sounds": sound_files})

        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error getting available sounds")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/camera/url", methods=["GET"])
    def get_camera_url():
        """Get the configured camera URL."""
        try:
            camera_url = webui.presets.camera_url
            logger.info("Camera URL requested: '%s'", camera_url)
            return jsonify({"camera_url": camera_url})
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error getting camera URL")
            return jsonify({"error": str(e)}), 500
