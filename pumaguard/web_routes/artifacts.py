"""Artifacts routes for intermediate visualizations and CSVs."""

from __future__ import (
    annotations,
)

import os
from typing import (
    TYPE_CHECKING,
)

from flask import (
    jsonify,
    request,
    send_from_directory,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def register_artifacts_routes(app: "Flask", webui: "WebUI") -> None:
    """Register artifacts endpoints for list and download."""

    @app.route("/api/artifacts", methods=["GET"])
    def list_artifacts():
        base_dir = os.path.realpath(
            os.path.normpath(webui.presets.intermediate_dir)
        )
        if not os.path.exists(base_dir):
            return jsonify(
                {"artifacts": [], "total": 0, "directory": base_dir}
            )
        ext_param = request.args.get("ext", default=None, type=str)
        ext_filter: set[str] | None = None
        if ext_param:
            parts = [
                p.strip().lower() for p in ext_param.split(",") if p.strip()
            ]
            ext_filter = {p if p.startswith(".") else f".{p}" for p in parts}
        limit = request.args.get("limit", default=None, type=int)
        entries: list[dict[str, object]] = []
        try:
            for filename in os.listdir(base_dir):
                filepath = os.path.join(base_dir, filename)
                if not os.path.isfile(filepath):
                    continue
                ext = os.path.splitext(filename)[1].lower()
                if ext_filter is not None and ext not in ext_filter:
                    continue
                stat = os.stat(filepath)
                kind = (
                    "image"
                    if ext in IMAGE_EXTS
                    else ("csv" if ext == ".csv" else "file")
                )
                entries.append(
                    {
                        "filename": filename,
                        "path": filepath,
                        "ext": ext,
                        "kind": kind,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "created": stat.st_ctime,
                    }
                )
        except OSError:
            return jsonify({"error": "Failed to read artifacts"}), 500
        entries.sort(key=lambda x: x["modified"], reverse=True)  # type: ignore
        if limit is not None and limit > 0:
            entries = entries[:limit]
        return jsonify(
            {
                "artifacts": entries,
                "total": len(entries),
                "directory": base_dir,
            }
        )

    @app.route("/api/artifacts/<path:filepath>", methods=["GET"])
    def get_artifact(filepath: str):
        base_dir = os.path.realpath(
            os.path.normpath(webui.presets.intermediate_dir)
        )
        abs_filepath = os.path.realpath(os.path.normpath(filepath))
        if os.path.commonpath([abs_filepath, base_dir]) != base_dir:
            return jsonify({"error": "Access denied"}), 403
        if not os.path.exists(abs_filepath) or not os.path.isfile(
            abs_filepath
        ):
            return jsonify({"error": "File not found"}), 404
        directory = os.path.dirname(abs_filepath)
        filename = os.path.basename(abs_filepath)
        as_attachment = (
            request.args.get("download", default="false").lower() == "true"
        )
        return send_from_directory(
            directory, filename, as_attachment=as_attachment
        )
