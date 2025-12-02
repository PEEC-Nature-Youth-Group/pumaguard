"""Photos routes for listing, fetching, and deleting images."""

from __future__ import (
    annotations,
)

import os
from typing import (
    TYPE_CHECKING,
)

from flask import (
    jsonify,
    send_from_directory,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


def register_photos_routes(app: "Flask", webui: "WebUI") -> None:
    """Register photo endpoints for list, get, and delete."""

    @app.route("/api/photos", methods=["GET"])
    def get_photos():
        """List all photos from watched and classification directories."""
        photos: list[dict] = []
        all_directories = (
            webui.image_directories + webui.classification_directories
        )
        for directory in all_directories:
            if not os.path.exists(directory):
                continue
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in IMAGE_EXTS:
                        stat = os.stat(filepath)
                        photos.append(
                            {
                                "filename": filename,
                                "path": filepath,
                                "directory": directory,
                                "size": stat.st_size,
                                "modified": stat.st_mtime,
                                "created": stat.st_ctime,
                            }
                        )
        photos.sort(key=lambda x: x["modified"], reverse=True)
        return jsonify({"photos": photos, "total": len(photos)})

    @app.route("/api/photos/<path:filepath>", methods=["GET"])
    def get_photo(filepath: str):
        # Safely resolve user provided path against allowed directories
        abs_filepath = None
        all_directories = (
            webui.image_directories + webui.classification_directories
        )
        for directory in all_directories:
            abs_directory = os.path.realpath(directory)
            joined_path = os.path.join(abs_directory, filepath)
            candidate = os.path.realpath(joined_path)
            try:
                common = os.path.commonpath([candidate, abs_directory])
                if common == abs_directory and os.path.exists(candidate):
                    abs_filepath = candidate
                    break
            except ValueError:
                # Different drives on Windows
                continue
        debug_paths = os.environ.get("PG_DEBUG_PATHS") in {"1", "true", "True"}
        if abs_filepath is None:
            payload = {"error": "Access denied"}
            if debug_paths:
                payload["_tried_bases"] = all_directories
                payload["_requested"] = filepath
            return jsonify(payload), 403
        if not os.path.exists(abs_filepath) or not os.path.isfile(
            abs_filepath
        ):
            payload = {"error": "File not found"}
            if debug_paths:
                payload["_resolved"] = abs_filepath
            return jsonify(payload), 404
        ext = os.path.splitext(abs_filepath)[1].lower()
        if ext not in IMAGE_EXTS:
            payload = {"error": "Access denied"}
            if debug_paths:
                payload["_ext"] = ext
            return jsonify(payload), 403
        directory = os.path.dirname(abs_filepath)
        filename = os.path.basename(abs_filepath)
        return send_from_directory(directory, filename)

    @app.route("/api/photos/<path:filepath>", methods=["DELETE"])
    def delete_photo(filepath: str):
        # Safely resolve user provided path against allowed directories
        abs_filepath = None
        all_directories = (
            webui.image_directories + webui.classification_directories
        )
        for directory in all_directories:
            abs_directory = os.path.realpath(directory)
            joined_path = os.path.join(abs_directory, filepath)
            candidate = os.path.realpath(joined_path)
            try:
                common = os.path.commonpath([candidate, abs_directory])
                if common == abs_directory and os.path.exists(candidate):
                    abs_filepath = candidate
                    break
            except ValueError:
                # Different drives on Windows
                continue
        if abs_filepath is None:
            return jsonify({"error": "Access denied"}), 403
        if not os.path.exists(abs_filepath) or not os.path.isfile(
            abs_filepath
        ):
            return jsonify({"error": "File not found"}), 404
        ext = os.path.splitext(abs_filepath)[1].lower()
        if ext not in IMAGE_EXTS:
            return jsonify({"error": "Access denied"}), 403
        os.remove(abs_filepath)
        return jsonify({"success": True, "message": "Photo deleted"})
