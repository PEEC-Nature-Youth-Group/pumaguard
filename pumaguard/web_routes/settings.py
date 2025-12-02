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
    playsound,
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
            ]

            if len(data) == 0:
                raise ValueError("Did not receive any settings")

            for key, value in data.items():
                if key in allowed_settings:
                    logger.debug("Updating %s with %s", key, value)
                    attr_name = key.replace("-", "_").replace("YOLO_", "yolo_")
                    setattr(webui.presets, attr_name, value)
                else:
                    logger.debug("Skipping unknown/read-only setting: %s", key)

            try:
                filepath = webui.presets.settings_file
                settings_dict = dict(webui.presets)
                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.dump(settings_dict, f, default_flow_style=False)
                logger.info("Settings updated and saved to %s", filepath)
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

            # Play the sound
            logger.info("Testing sound playback: %s", sound_file_path)
            playsound(sound_file_path)
            return jsonify(
                {
                    "success": True,
                    "message": f"Sound played: {sound_file}",
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error testing sound")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/models/available", methods=["GET"])
    def get_available_models():
        """Get list of available classifier models with cache status."""
        try:
            models_dir = get_models_directory()
            available_models = list_available_models()

            # Filter to only classifier models (*.h5 files)
            classifier_models = [
                model for model in available_models if model.endswith(".h5")
            ]

            model_list = []
            for model_name in classifier_models:
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
