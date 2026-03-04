"""Photos routes for listing, fetching, and deleting images."""

from __future__ import (
    annotations,
)

import logging
import os
from typing import (
    TYPE_CHECKING,
    Any,
)

from flask import (
    jsonify,
)
from flask import request as flask_request
from flask import (
    send_from_directory,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# Sub-directory created inside each image directory to store cached thumbnails.
# The leading dot keeps it out of the image listings.
_THUMB_DIR = ".thumbs"


def generate_thumbnail(
    source_path: str,
    max_width: int,
    max_height: int,
) -> str | None:
    """
    Return the path of a cached thumbnail for *source_path*, generating it
    with Pillow if it does not exist yet or is stale.

    Thumbnails are stored in a ``.thumbs/`` sub-directory inside the same
    directory as the source image, named
    ``{stem}_{max_width}x{max_height}.jpg``.

    Args:
        source_path: Absolute path to the source image.
        max_width:   Maximum width of the thumbnail in pixels.
        max_height:  Maximum height of the thumbnail in pixels.

    Returns:
        Absolute path to the thumbnail file, or ``None`` if generation failed.
    """
    try:
        from PIL import Image  # pylint: disable=import-outside-toplevel
    except ImportError:
        logger.warning("Pillow is not installed; thumbnails not available")
        return None

    try:
        source_dir = os.path.dirname(source_path)
        source_name = os.path.basename(source_path)
        stem = os.path.splitext(source_name)[0]

        thumb_dir = os.path.join(source_dir, _THUMB_DIR)
        os.makedirs(thumb_dir, exist_ok=True)

        thumb_name = f"{stem}_{max_width}x{max_height}.jpg"
        thumb_path = os.path.join(thumb_dir, thumb_name)

        # Re-use the cached thumbnail if it exists and is newer than the
        # source image (mtime comparison avoids stale thumbnails after
        # in-place replacement of an image file).
        if os.path.exists(thumb_path):
            source_mtime = os.path.getmtime(source_path)
            thumb_mtime = os.path.getmtime(thumb_path)
            if thumb_mtime >= source_mtime:
                return thumb_path

        with Image.open(source_path) as img_file:
            # Convert palette / RGBA modes to RGB so JPEG encoding works.
            # Use a separate variable so mypy keeps the ImageFile / Image
            # types distinct (convert() returns the base Image, not ImageFile).
            work: Image.Image = (
                img_file.convert("RGB")
                if img_file.mode not in ("RGB", "L")
                else img_file
            )
            work.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            work.save(thumb_path, "JPEG", quality=85, optimize=True)

        logger.debug(
            "Generated thumbnail %s (%dx%d)", thumb_path, max_width, max_height
        )
        return thumb_path

    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "Failed to generate thumbnail for %s: %s", source_path, exc
        )
        return None


def _resolve_image_path(
    filepath: str,
    all_directories: list[str],
) -> str | None:
    """
    Safely resolve *filepath* against *all_directories* and return the
    absolute path only if it is contained within one of the allowed
    directories and the file exists.

    Returns ``None`` if access should be denied.
    """
    for directory in all_directories:
        abs_directory = os.path.realpath(directory)
        joined_path = os.path.join(abs_directory, filepath)
        candidate = os.path.realpath(joined_path)
        try:
            common = os.path.commonpath([candidate, abs_directory])
            if common == abs_directory and os.path.exists(candidate):
                return candidate
        except ValueError:
            # Different drives on Windows
            continue
    return None


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
        """
        Serve a photo file, optionally as a thumbnail.

        Query parameters:
            thumbnail: ``true`` to request a thumbnail (default: ``false``)
            width:     Maximum thumbnail width in pixels (default: ``320``)
            height:    Maximum thumbnail height in pixels (default: ``320``)

        When ``thumbnail=true`` is present the server generates a JPEG
        thumbnail using Pillow and caches it in a ``.thumbs/`` sub-directory
        next to the source image.  Subsequent requests for the same size are
        served from the cache with no re-encoding overhead.

        Falls back to serving the full-resolution image if Pillow is not
        available or thumbnail generation fails.
        """
        all_directories = (
            webui.image_directories + webui.classification_directories
        )
        abs_filepath = _resolve_image_path(filepath, all_directories)

        debug_paths = os.environ.get("PG_DEBUG_PATHS") in {
            "1",
            "true",
            "True",
        }

        if abs_filepath is None:
            payload: dict[str, Any] = {"error": "Access denied"}
            if debug_paths:
                payload["_tried_bases"] = all_directories
                payload["_requested"] = filepath
            return jsonify(payload), 403

        if not os.path.isfile(abs_filepath):
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

        # --- Thumbnail handling -----------------------------------------

        want_thumbnail = (
            flask_request.args.get("thumbnail", "false").lower() == "true"
        )

        if want_thumbnail:
            try:
                max_width = int(flask_request.args.get("width", "320"))
                max_height = int(flask_request.args.get("height", "320"))
            except ValueError:
                max_width = 320
                max_height = 320

            thumb_path = generate_thumbnail(
                abs_filepath, max_width, max_height
            )
            if thumb_path is not None:
                return send_from_directory(
                    os.path.dirname(thumb_path),
                    os.path.basename(thumb_path),
                )
            # Fall through to full-resolution serving if generation failed.
            logger.debug(
                "Thumbnail generation failed for %s; serving full image",
                abs_filepath,
            )
        # ----------------------------------------------------------------

        directory = os.path.dirname(abs_filepath)
        filename = os.path.basename(abs_filepath)
        return send_from_directory(directory, filename)

    @app.route("/api/photos/<path:filepath>", methods=["DELETE"])
    def delete_photo(filepath: str):
        """
        Delete a photo and its cached thumbnails.
        """
        all_directories = (
            webui.image_directories + webui.classification_directories
        )
        abs_filepath = _resolve_image_path(filepath, all_directories)

        if abs_filepath is None:
            return jsonify({"error": "Access denied"}), 403

        if not os.path.isfile(abs_filepath):
            return jsonify({"error": "File not found"}), 404

        ext = os.path.splitext(abs_filepath)[1].lower()
        if ext not in IMAGE_EXTS:
            return jsonify({"error": "Access denied"}), 403

        # Delete cached thumbnails for this image before removing the source.
        _delete_thumbnails(abs_filepath)

        os.remove(abs_filepath)

        # Notify SSE clients that an image was deleted.
        if webui.image_notification_callback is not None:
            webui.image_notification_callback(
                "image_deleted",
                {"path": filepath},
            )
        return jsonify({"success": True, "message": "Photo deleted"})


def _delete_thumbnails(source_path: str) -> None:
    """
    Remove all cached thumbnails for *source_path* from its ``.thumbs/``
    sub-directory.  Failures are logged but not raised so that the caller
    can continue with source-image deletion regardless.
    """
    source_dir = os.path.dirname(source_path)
    stem = os.path.splitext(os.path.basename(source_path))[0]
    thumb_dir = os.path.join(source_dir, _THUMB_DIR)

    if not os.path.isdir(thumb_dir):
        return

    prefix = f"{stem}_"
    for entry in os.listdir(thumb_dir):
        if entry.startswith(prefix) and entry.endswith(".jpg"):
            try:
                os.remove(os.path.join(thumb_dir, entry))
                logger.debug("Deleted thumbnail %s", entry)
            except OSError as exc:
                logger.warning("Could not delete thumbnail %s: %s", entry, exc)
