"""
Folders routes for browsing and listing images.
"""

from __future__ import (
    annotations,
)

import os
from typing import (
    TYPE_CHECKING,
    cast,
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
        """Get all browsable folders (watched + classification outputs)."""
        folders = []
        # Combine both watched and classification directories
        all_directories = (
            webui.image_directories + webui.classification_directories
        )
        for directory in all_directories:
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
        """Get images from a folder (watched or classification output)."""
        # Try to resolve folder_path relative to allowed directories
        abs_folder = None
        resolved_base = None
        all_directories = (
            webui.image_directories + webui.classification_directories
        )

        # Flask's <path:> converter strips leading slash, add it back
        # if it looks like an absolute path was intended
        if not folder_path.startswith(
            "/"
        ) and not folder_path.startswith("\\"):
            folder_path = "/" + folder_path

        # Normalize the requested path
        normalized_folder_path = os.path.realpath(
            os.path.normpath(folder_path)
        )

        for directory in all_directories:
            abs_directory = os.path.realpath(os.path.normpath(directory))

            # Check if the requested path IS the directory itself
            if normalized_folder_path == abs_directory:
                abs_folder = abs_directory
                resolved_base = abs_directory
                break

            # Check if requested path is a subdirectory
            candidate_folder = os.path.realpath(
                os.path.join(abs_directory, folder_path)
            )
            try:
                common = os.path.commonpath([candidate_folder, abs_directory])
                if common == abs_directory:
                    abs_folder = candidate_folder
                    resolved_base = abs_directory
                    break
            except ValueError:
                # Different drives on Windows
                continue
        debug_paths = os.environ.get("PG_DEBUG_PATHS") in {"1", "true", "True"}
        
        if abs_folder is None:
            # Ensure file is within the allowed folder
            error_response = {"error": "Access denied"}
            if debug_paths:
                error_response["_requested"] = folder_path
                error_response["_normalized"] = normalized_folder_path
                error_response["_allowed_dirs"] = all_directories
            return jsonify(error_response), 403
        if not os.path.exists(abs_folder) or not os.path.isdir(abs_folder):
            error_response = {"error": "Folder not found"}
            if debug_paths:
                error_response["_requested"] = folder_path
                error_response["_resolved"] = abs_folder
                error_response["_exists"] = os.path.exists(abs_folder)
                error_response["_is_dir"] = os.path.isdir(abs_folder) if os.path.exists(abs_folder) else None
            return jsonify(error_response), 404
        images = []
        debug_paths = os.environ.get("PG_DEBUG_PATHS") in {"1", "true", "True"}
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
                    rel_file_path = os.path.relpath(
                        resolved_filepath, resolved_base
                    )
                    item = {
                        "filename": filename,
                        "path": rel_file_path,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "created": stat.st_ctime,
                    }
                    if debug_paths:
                        item["_abs"] = resolved_filepath
                        item["_base"] = resolved_base
                        item["_folder_abs"] = abs_folder
                    images.append(item)

        images.sort(key=lambda x: cast(float, x["modified"]), reverse=True)
        # Return only relative folder path to root and the root directory name
        if resolved_base is not None:
            rel_folder_path = os.path.relpath(abs_folder, resolved_base)
            folder_name = os.path.basename(resolved_base)
        else:
            rel_folder_path = ""
            folder_name = ""
        return jsonify(
            {
                "images": images,
                "folder": rel_folder_path,
                "base": folder_name,
            }
        )
