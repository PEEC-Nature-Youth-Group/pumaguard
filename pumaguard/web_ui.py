"""
Web-UI for Pumaguard.
"""

import argparse
import logging
import os
import threading
import time
from pathlib import (
    Path,
)
from typing import (
    TypedDict,
)

import yaml
from flask import (
    Flask,
    jsonify,
    request,
    send_file,
    send_from_directory,
)
from flask_cors import (
    CORS,
)

from pumaguard.presets import (
    Preset,
)

logger = logging.getLogger(__name__)


class PhotoDict(TypedDict):
    """Type definition for photo metadata dictionary."""

    filename: str
    path: str
    directory: str
    size: int
    modified: float
    created: float


class WebUI:
    """
    The class for the WebUI.
    """

    def __init__(
        self,
        presets: Preset,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: bool = False,
    ):
        """
        Initialize the WebUI server.

        Args:
            host: The host to bind to (default: 127.0.0.1)
            port: The port to bind to (default: 5000)
            debug: Enable debug mode (default: False)
            presets: Preset instance to manage settings
        """
        self.host: str = host
        self.port: int = port
        self.debug: bool = debug
        self.app: Flask = Flask(__name__)
        CORS(self.app)
        self.server_thread: threading.Thread | None = None
        self._running: bool = False
        self.presets: Preset = presets
        self.image_directories: list[str] = []

        # Determine the Flutter build directory
        self.flutter_dir: Path = Path(__file__).parent / "web-ui-flutter"
        self.build_dir: Path = self.flutter_dir / "build" / "web"

        self._setup_routes()

    def _setup_routes(self):
        """
        Set up Flask routes to serve the Flutter web app and API.
        """

        @self.app.route("/")
        def index():
            """
            Serve the main index.html file.
            """
            if not self.build_dir.exists():
                return (
                    "Flutter web app not built. Please run "
                    + "'flutter build web' "
                    + f"in the {self.flutter_dir} directory first.",
                    500,
                )
            return send_file(self.build_dir / "index.html")

        @self.app.route("/<path:path>")
        def serve_static(path):
            """
            Serve static files (JS, CSS, assets, etc.).
            """
            if path.startswith("api/"):
                return jsonify({"error": "Not found"}), 404

            if not self.build_dir.exists():
                return (
                    "Flutter web app not built. Please run "
                    + "'flutter build web' "
                    + f"in the {self.flutter_dir} directory first.",
                    500,
                )

            file_path = self.build_dir / path
            if file_path.exists() and file_path.is_file():
                return send_from_directory(self.build_dir, path)
            return send_file(self.build_dir / "index.html")

        @self.app.route("/api/settings", methods=["GET"])
        def get_settings():
            """
            Get current settings.
            """
            return jsonify(dict(self.presets))

        @self.app.route("/api/settings", methods=["PUT"])
        def update_settings():
            """Update settings."""
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
                    logger.debug("Trying to update %s", key)
                    if key in allowed_settings:
                        logger.debug("Updating %s with %s", key, value)
                        setattr(self.presets, key, value)
                    else:
                        logger.debug("Unknown setting %s", key)
                        raise ValueError(f"Ignoring unknown setting {key}")

                logger.info("Settings updated successfully")
                return jsonify(
                    {"success": True, "message": "Settings updated"}
                )
            except ValueError as e:
                logger.error("Error updating settings: %s", e)
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/settings/save", methods=["POST"])
        def save_settings():
            """Save current settings to a YAML file."""
            data = request.json
            filepath = data.get("filepath") if data else None

            if not filepath:
                # Use default settings file
                filepath = self.presets.settings_file

            settings_dict = {}
            for key, value in self.presets:
                settings_dict[key] = value

            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(settings_dict, f, default_flow_style=False)

            logger.info("Settings saved to %s", filepath)
            return jsonify({"success": True, "filepath": filepath})

        @self.app.route("/api/settings/load", methods=["POST"])
        def load_settings():
            """Load settings from a YAML file."""
            data = request.json
            filepath = data.get("filepath") if data else None

            if not filepath:
                return jsonify({"error": "No filepath provided"}), 400

            self.presets.load(filepath)
            logger.info("Settings loaded from %s", filepath)
            return jsonify({"success": True, "message": "Settings loaded"})

        # Photos/Images API
        @self.app.route("/api/photos", methods=["GET"])
        def get_photos():
            """Get list of captured photos."""
            photos: list[PhotoDict] = []
            for directory in self.image_directories:
                if not os.path.exists(directory):
                    continue

                for filename in os.listdir(directory):
                    filepath = os.path.join(directory, filename)
                    if os.path.isfile(filepath):
                        # Check if it's an image file
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in [
                            ".jpg",
                            ".jpeg",
                            ".png",
                            ".gif",
                            ".bmp",
                            ".webp",
                        ]:
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

            # Sort by modified time, newest first
            photos.sort(key=lambda x: x["modified"], reverse=True)

            return jsonify({"photos": photos, "total": len(photos)})

        @self.app.route("/api/photos/<path:filepath>", methods=["GET"])
        def get_photo(filepath):
            """Get a specific photo."""
            # Security check: ensure the file is in one of the allowed
            # directories
            abs_filepath = os.path.abspath(filepath)
            allowed = False
            for directory in self.image_directories:
                abs_directory = os.path.abspath(directory)
                if abs_filepath.startswith(abs_directory):
                    allowed = True
                    break

            if not allowed:
                return jsonify({"error": "Access denied"}), 403

            if not os.path.exists(abs_filepath):
                return jsonify({"error": "File not found"}), 404

            directory = os.path.dirname(abs_filepath)
            filename = os.path.basename(abs_filepath)
            return send_from_directory(directory, filename)

        @self.app.route("/api/photos/<path:filepath>", methods=["DELETE"])
        def delete_photo(filepath):
            """Delete a photo."""
            # Security check: ensure the file is in one of the allowed
            # directories
            abs_filepath = os.path.abspath(filepath)
            allowed = False
            for directory in self.image_directories:
                abs_directory = os.path.abspath(directory)
                if abs_filepath.startswith(abs_directory):
                    allowed = True
                    break

            if not allowed:
                return jsonify({"error": "Access denied"}), 403

            if not os.path.exists(abs_filepath):
                return jsonify({"error": "File not found"}), 404

            os.remove(abs_filepath)
            logger.info("Deleted photo: %s", abs_filepath)
            return jsonify({"success": True, "message": "Photo deleted"})

        # Directories API
        @self.app.route("/api/directories", methods=["GET"])
        def get_directories():
            """Get list of image directories being monitored."""
            return jsonify({"directories": self.image_directories})

        @self.app.route("/api/directories", methods=["POST"])
        def add_directory():
            """Add a directory to monitor for images."""
            data = request.json
            directory = data.get("directory") if data else None

            if not directory:
                return jsonify({"error": "No directory provided"}), 400

            if not os.path.exists(directory):
                return jsonify({"error": "Directory does not exist"}), 400

            if directory not in self.image_directories:
                self.image_directories.append(directory)
                logger.info("Added image directory: %s", directory)

            return jsonify(
                {"success": True, "directories": self.image_directories}
            )

        @self.app.route("/api/directories/<int:index>", methods=["DELETE"])
        def remove_directory(index):
            """Remove a directory from watch list."""
            if 0 <= index < len(self.image_directories):
                removed = self.image_directories.pop(index)
                logger.info("Removed image directory: %s", removed)
                return jsonify(
                    {
                        "success": True,
                        "directories": self.image_directories,
                    }
                )
            return jsonify({"error": "Invalid index"}), 400

        # System/Status API
        @self.app.route("/api/status", methods=["GET"])
        def get_status():
            """Get server status."""
            return jsonify(
                {
                    "status": "running",
                    "version": "1.0.0",
                    "directories_count": len(self.image_directories),
                    "host": self.host,
                    "port": self.port,
                }
            )

    def add_image_directory(self, directory: str):
        """
        Add a directory to scan for images.

        Args:
            directory: Path to the directory containing captured images
        """
        if directory not in self.image_directories:
            self.image_directories.append(directory)
            logger.info("Added image directory: %s", directory)

    def _run_server(self):
        """Internal method to run the Flask server."""
        self.app.run(
            host=self.host,
            port=self.port,
            debug=self.debug,
            use_reloader=False,
        )

    def start(self):
        """
        Start the web-ui server.
        """
        if self._running:
            logger.warning("Server is already running")
            return

        logger.info(
            "Starting WebUI server on http://%s:%d", self.host, self.port
        )
        self._running = True

        if self.debug:
            self._run_server()
        else:
            self.server_thread = threading.Thread(
                target=self._run_server, daemon=True
            )
            self.server_thread.start()
            logger.info("WebUI server started successfully")

    def stop(self):
        """
        Stop the web-ui server.
        """
        if not self._running:
            logger.warning("Server is not running")
            return

        self._running = False
        logger.info(
            "WebUI server stop requested (will stop when main program exits)"
        )


# Convenience function for quick start
def main():
    """
    Start the WebUI server from command line.
    """
    parser = argparse.ArgumentParser(description="Pumaguard Web UI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to bind to"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode"
    )
    parser.add_argument(
        "--settings", type=str, help="Load settings from YAML file"
    )
    parser.add_argument(
        "--image-dir",
        type=str,
        action="append",
        help=(
            "Directory containing captured images "
            + "(can be used multiple times)"
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Load presets if specified
    presets = Preset()
    if args.settings:
        presets.load(args.settings)

    web_ui = WebUI(
        presets=presets, host=args.host, port=args.port, debug=args.debug
    )
    logger.debug("Serving UI from %s", web_ui.flutter_dir)

    # Add image directories
    if args.image_dir:
        for directory in args.image_dir:
            web_ui.add_image_directory(directory)

    web_ui.start()

    if not args.debug:
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            web_ui.stop()


if __name__ == "__main__":
    main()
