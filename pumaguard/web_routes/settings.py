"""Settings routes for loading, saving, and updating presets."""

from __future__ import (
    annotations,
)

import logging
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
