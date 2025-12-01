"""Sync routes for checksums and batch downloading."""

from __future__ import (
    annotations,
)

import hashlib
import io
import os
import zipfile
from typing import (
    TYPE_CHECKING,
)

from flask import (
    jsonify,
    request,
    send_file,
    send_from_directory,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )


def _calculate_file_checksum(filepath: str) -> str:
    """Calculate SHA256 checksum of file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def register_sync_routes(app: "Flask", webui: "WebUI") -> None:
    """Register sync endpoints for file checksums and downloads."""

    @app.route("/api/sync/checksums", methods=["POST"])
    def calculate_checksums():
        data = request.json
        if not data or "files" not in data:
            return jsonify({"error": "No files provided"}), 400
        client_files = data["files"]
        files_to_download = []
        for filepath, client_checksum in client_files.items():
            # Resolve and validate within allowed directories
            abs_filepath = os.path.realpath(os.path.normpath(filepath))
            allowed = False
            for directory in webui.image_directories:
                abs_directory = os.path.realpath(os.path.normpath(directory))
                try:
                    common = os.path.commonpath([abs_filepath, abs_directory])
                    if common == abs_directory:
                        allowed = True
                        break
                except ValueError:
                    # Different drives on Windows
                    continue
            if not allowed:
                continue
            if not os.path.exists(abs_filepath):
                continue
            server_checksum = _calculate_file_checksum(abs_filepath)
            if server_checksum != client_checksum:
                stat = os.stat(abs_filepath)
                files_to_download.append(
                    {
                        "path": filepath,
                        "checksum": server_checksum,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    }
                )
        return jsonify(
            {
                "files_to_download": files_to_download,
                "total": len(files_to_download),
            }
        )

    @app.route("/api/sync/download", methods=["POST"])
    def download_files():
        data = request.json
        if not data or "files" not in data:
            return jsonify({"error": "No files provided"}), 400
        file_paths = data["files"]
        validated_files = []
        for filepath in file_paths:
            # Resolve and validate within allowed directories
            abs_filepath = os.path.realpath(os.path.normpath(filepath))
            allowed = False
            for directory in webui.image_directories:
                # Ensure allowed directories are normalized and real paths
                abs_directory = os.path.realpath(os.path.normpath(directory))
                try:
                    common = os.path.commonpath([abs_filepath, abs_directory])
                    if common == abs_directory and os.path.isfile(
                        abs_filepath
                    ):
                        allowed = True
                        break
                except ValueError:
                    # Different drives on Windows
                    continue
            if allowed and os.path.exists(abs_filepath):
                validated_files.append(abs_filepath)
        if not validated_files:
            return jsonify({"error": "No valid files to download"}), 400
        if len(validated_files) == 1:
            directory = os.path.dirname(validated_files[0])
            filename = os.path.basename(validated_files[0])
            return send_from_directory(directory, filename, as_attachment=True)
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for filepath in validated_files:
                arcname = os.path.basename(filepath)
                zf.write(filepath, arcname)
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name="pumaguard_images.zip",
        )
