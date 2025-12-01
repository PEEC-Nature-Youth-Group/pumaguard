"""Directory management routes for adding and removing watch folders."""

from __future__ import (
    annotations,
)

import logging
from typing import (
    TYPE_CHECKING,
)

from flask import (
    jsonify,
    request,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


def register_directories_routes(app: "Flask", webui: "WebUI") -> None:
    """Register directory endpoints for list, add, remove."""

    @app.route("/api/directories", methods=["GET"])
    def get_directories():
        return jsonify({"directories": webui.image_directories})

    @app.route("/api/directories", methods=["POST"])
    def add_directory():
        data = request.json
        directory = data.get("directory") if data else None
        if not directory:
            return jsonify({"error": "No directory provided"}), 400
        # Validate existence happens inside webui.add_image_directory
        if directory not in webui.image_directories:
            webui.image_directories.append(directory)
            logger.info("Added image directory: %s", directory)
            if webui.folder_manager is not None:
                webui.folder_manager.register_folder(
                    directory, webui.watch_method
                )
                logger.info(
                    "Registered folder with manager: %s (method: %s)",
                    directory,
                    webui.watch_method,
                )
        return jsonify(
            {"success": True, "directories": webui.image_directories}
        )

    @app.route("/api/directories/<int:index>", methods=["DELETE"])
    def remove_directory(index: int):
        if 0 <= index < len(webui.image_directories):
            removed = webui.image_directories.pop(index)
            logger.info("Removed image directory: %s", removed)
            return jsonify(
                {"success": True, "directories": webui.image_directories}
            )
        return jsonify({"error": "Invalid index"}), 400
