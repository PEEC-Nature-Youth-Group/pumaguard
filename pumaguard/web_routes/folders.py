"""Folders routes for browsing and listing images."""

from __future__ import (
    annotations,
)

import os
from typing import (
    TYPE_CHECKING,
)

from flask import (
    jsonify,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


def register_folders_routes(app: "Flask", webui: "WebUI") -> None:
    """Register folder endpoints for list and browse images."""

    @app.route("/api/folders", methods=["GET"])
    def get_folders():
        folders = []
        for directory in webui.image_directories:
            if not os.path.exists(directory):
                continue
            image_count = 0
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in IMAGE_EXTS:
                        image_count += 1
            folders.append(
                {
                    "path": directory,
                    "name": os.path.basename(directory),
                    "image_count": image_count,
                }
            )
        return jsonify({"folders": folders})

    @app.route("/api/folders/<path:folder_path>/images", methods=["GET"])
    def get_folder_images(folder_path: str):
        # Resolve to absolute path and validate it's within allowed directories
        abs_folder = os.path.realpath(os.path.normpath(folder_path))
        allowed = False
        for directory in webui.image_directories:
            abs_directory = os.path.realpath(os.path.normpath(directory))
            try:
                common = os.path.commonpath([abs_folder, abs_directory])
                if common == abs_directory:
                    allowed = True
                    break
            except ValueError:
                # Different drives on Windows
                continue
        if not allowed:
            return jsonify({"error": "Access denied"}), 403
        if not os.path.exists(abs_folder) or not os.path.isdir(abs_folder):
            return jsonify({"error": "Folder not found"}), 404
        images = []
        for filename in os.listdir(abs_folder):
            filepath = os.path.join(abs_folder, filename)
            resolved_filepath = os.path.realpath(os.path.normpath(filepath))
            if (
                os.path.commonpath([resolved_filepath, abs_folder])
                != abs_folder
            ):
                continue
            if os.path.isfile(resolved_filepath):
                ext = os.path.splitext(filename)[1].lower()
                if ext in IMAGE_EXTS:
                    stat = os.stat(resolved_filepath)
                    images.append(
                        {
                            "filename": filename,
                            "path": resolved_filepath,
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                            "created": stat.st_ctime,
                        }
                    )
        images.sort(key=lambda x: x["modified"], reverse=True)
        return jsonify({"images": images, "folder": abs_folder})
