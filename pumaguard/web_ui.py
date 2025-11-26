"""
Web-UI for Pumaguard.
"""

import argparse
import hashlib
import io
import logging
import os
import socket
import threading
import time
import zipfile
from pathlib import (
    Path,
)
from typing import (
    TYPE_CHECKING,
    TypedDict,
)

import yaml

if TYPE_CHECKING:
    from pumaguard.server import (
        FolderManager,
    )

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
from yaml.representer import (
    YAMLError,
)
from zeroconf import (
    ServiceInfo,
    Zeroconf,
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

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        presets: Preset,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: bool = False,
        mdns_enabled: bool = True,
        mdns_name: str = "pumaguard",
        folder_manager: "FolderManager | None" = None,
        watch_method: str = "os",
    ):
        """
        Initialize the WebUI server.

        Args:
            host: The host to bind to (default: 127.0.0.1)
            port: The port to bind to (default: 5000)
            debug: Enable debug mode (default: False)
            presets: Preset instance to manage settings
            mdns_enabled: Enable mDNS/Zeroconf service advertisement
                          (default: True)
            mdns_name: mDNS service name (default: pumaguard)
            folder_manager: FolderManager instance to register new folders
            watch_method: Watch method for new folders (default: os)
        """
        self.host: str = host
        self.port: int = port
        self.debug: bool = debug
        self.mdns_enabled: bool = mdns_enabled
        self.mdns_name: str = mdns_name
        self.folder_manager = folder_manager
        self.watch_method: str = watch_method
        self.app: Flask = Flask(__name__)

        # Configure CORS to allow all origins (for development and container
        # access), This allows the web app to work when accessed from any
        # IP/hostname
        CORS(
            self.app,
            resources={r"/*": {"origins": "*"}},
            allow_headers=["Content-Type"],
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        )

        self.server_thread: threading.Thread | None = None
        self._running: bool = False
        self.presets: Preset = presets
        self.image_directories: list[str] = []

        # mDNS/Zeroconf support
        self.zeroconf: Zeroconf | None = None
        self.service_info: ServiceInfo | None = None

        # Determine the Flutter build directory
        # Try multiple locations for flexibility:
        # 1. Package data location (installed): pumaguard-ui/ (built files
        #    copied here)
        # 2. Development location: ../../pumaguard-ui/build/web
        # 3. Old location (legacy): web-ui-flutter/build/web

        # Package data location - built files copied directly to pumaguard-ui/
        pkg_build_dir = Path(__file__).parent / "pumaguard-ui"

        # Development location (relative to package directory)
        dev_build_dir = (
            Path(__file__).parent.parent.parent
            / "pumaguard-ui"
            / "build"
            / "web"
        )

        # Legacy location
        old_build_dir = (
            Path(__file__).parent / "web-ui-flutter" / "build" / "web"
        )

        # Choose the first one that exists and has index.html
        if pkg_build_dir.exists() and (pkg_build_dir / "index.html").exists():
            self.flutter_dir = pkg_build_dir
            self.build_dir = pkg_build_dir
        elif (
            dev_build_dir.exists() and (dev_build_dir / "index.html").exists()
        ):
            self.flutter_dir = dev_build_dir.parent.parent
            self.build_dir = dev_build_dir
        elif (
            old_build_dir.exists() and (old_build_dir / "index.html").exists()
        ):
            self.flutter_dir = old_build_dir.parent.parent
            self.build_dir = old_build_dir
        else:
            # Default to package location even if not built yet
            self.flutter_dir = pkg_build_dir
            self.build_dir = pkg_build_dir

        self._setup_routes()

    def _calculate_file_checksum(self, filepath: str) -> str:
        """
        Calculate SHA256 checksum of a file.

        Args:
            filepath: Path to the file

        Returns:
            Hexadecimal checksum string
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

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
                    if key in allowed_settings:
                        logger.debug("Updating %s with %s", key, value)
                        # Convert hyphenated names to underscored attribute
                        # names
                        attr_name = key.replace("-", "_").replace(
                            "YOLO_", "yolo_"
                        )
                        setattr(self.presets, attr_name, value)
                    else:
                        logger.debug(
                            "Skipping unknown/read-only setting: %s", key
                        )

                # Auto-save settings to disk after updating
                try:
                    filepath = self.presets.settings_file
                    settings_dict = {}
                    for key, value in self.presets:
                        settings_dict[key] = value

                    with open(filepath, "w", encoding="utf-8") as f:
                        yaml.dump(settings_dict, f, default_flow_style=False)

                    logger.info("Settings updated and saved to %s", filepath)
                except YAMLError:
                    logger.exception(
                        "Error saving settings"
                    )  # logs stack trace too
                    return (
                        jsonify(
                            {
                                "error": "Settings updated but failed to save due to an internal error"  # pylint: disable=line-too-long
                            }
                        ),
                        500,
                    )

                return jsonify(
                    {"success": True, "message": "Settings updated and saved"}
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

        # Folder Browser API
        @self.app.route("/api/folders", methods=["GET"])
        def get_folders():
            """Get list of watched folders with image counts."""
            folders = []
            for directory in self.image_directories:
                if not os.path.exists(directory):
                    continue

                # Count images in folder
                image_count = 0
                for filename in os.listdir(directory):
                    filepath = os.path.join(directory, filename)
                    if os.path.isfile(filepath):
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in [
                            ".jpg",
                            ".jpeg",
                            ".png",
                            ".gif",
                            ".bmp",
                            ".webp",
                        ]:
                            image_count += 1

                folders.append(
                    {
                        "path": directory,
                        "name": os.path.basename(directory),
                        "image_count": image_count,
                    }
                )

            return jsonify({"folders": folders})

        @self.app.route(
            "/api/folders/<path:folder_path>/images", methods=["GET"]
        )
        def get_folder_images(folder_path):
            """Get list of images in a specific folder."""
            # Security check: ensure the folder is in allowed directories
            # Normalize and resolve symlinks for both folder_path and allowed
            # directories
            abs_folder = os.path.realpath(os.path.normpath(folder_path))
            allowed = False
            for directory in self.image_directories:
                abs_directory = os.path.realpath(os.path.normpath(directory))
                # Ensure abs_folder is contained in abs_directory
                common = os.path.commonpath([abs_folder, abs_directory])
                if common == abs_directory:
                    allowed = True
                    break

            if not allowed:
                return jsonify({"error": "Access denied"}), 403

            if not os.path.exists(abs_folder):
                return jsonify({"error": "Folder not found"}), 404

            images = []
            for filename in os.listdir(abs_folder):
                filepath = os.path.join(abs_folder, filename)
                # Security: resolve and ensure file is in allowed folder
                resolved_filepath = os.path.realpath(
                    os.path.normpath(filepath)
                )
                if (
                    os.path.commonpath([resolved_filepath, abs_folder])
                    != abs_folder
                ):
                    continue
                if os.path.isfile(resolved_filepath):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".gif",
                        ".bmp",
                        ".webp",
                    ]:
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

            # Sort by modified time, newest first
            images.sort(key=lambda x: x["modified"], reverse=True)

            return jsonify({"images": images, "folder": abs_folder})

        @self.app.route("/api/sync/checksums", methods=["POST"])
        def calculate_checksums():
            """
            Calculate checksums for requested files.
            Client sends list of files with their checksums,
            server returns which files need to be downloaded.
            """
            data = request.json
            if not data or "files" not in data:
                return jsonify({"error": "No files provided"}), 400

            client_files = data["files"]  # Dict of {filepath: checksum}
            files_to_download = []

            for filepath, client_checksum in client_files.items():
                # Security check
                abs_filepath = os.path.abspath(filepath)
                allowed = False
                for directory in self.image_directories:
                    abs_directory = os.path.abspath(directory)
                    if abs_filepath.startswith(abs_directory):
                        allowed = True
                        break

                if not allowed:
                    continue

                if not os.path.exists(abs_filepath):
                    continue

                # Calculate server-side checksum
                server_checksum = self._calculate_file_checksum(abs_filepath)

                # If checksums don't match or client doesn't have it, mark for
                # download
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

        @self.app.route("/api/sync/download", methods=["POST"])
        def download_files():
            """
            Download multiple files as a ZIP archive.
            """
            data = request.json
            if not data or "files" not in data:
                return jsonify({"error": "No files provided"}), 400

            file_paths = data["files"]

            # Validate all files
            validated_files = []
            for filepath in file_paths:
                abs_filepath = os.path.abspath(filepath)
                allowed = False
                for directory in self.image_directories:
                    abs_directory = os.path.abspath(directory)
                    if abs_filepath.startswith(abs_directory):
                        allowed = True
                        break

                if allowed and os.path.exists(abs_filepath):
                    validated_files.append(abs_filepath)

            if not validated_files:
                return jsonify({"error": "No valid files to download"}), 400

            # For single file, return it directly
            if len(validated_files) == 1:
                directory = os.path.dirname(validated_files[0])
                filename = os.path.basename(validated_files[0])
                return send_from_directory(
                    directory, filename, as_attachment=True
                )

            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
                for filepath in validated_files:
                    # Use relative path in zip to maintain folder structure
                    arcname = os.path.basename(filepath)
                    zf.write(filepath, arcname)

            memory_file.seek(0)
            return send_file(
                memory_file,
                mimetype="application/zip",
                as_attachment=True,
                download_name="pumaguard_images.zip",
            )

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

                # Register with FolderManager to start watching
                if self.folder_manager is not None:
                    self.folder_manager.register_folder(
                        directory, self.watch_method
                    )
                    logger.info(
                        "Registered folder with manager: %s (method: %s)",
                        directory,
                        self.watch_method,
                    )

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
            # Add request info to help debug CORS and origin issues
            origin = request.headers.get("Origin", "No Origin header")
            host = request.headers.get("Host", "No Host header")

            logger.debug(
                "API status called - Origin: %s, Host: %s", origin, host
            )

            return jsonify(
                {
                    "status": "running",
                    "version": "1.0.0",
                    "directories_count": len(self.image_directories),
                    "host": self.host,
                    "port": self.port,
                    "request_origin": origin,
                    "request_host": host,
                }
            )

        @self.app.route("/api/diagnostic", methods=["GET"])
        def get_diagnostic():
            """
            Get diagnostic information to help debug URL detection issues.
            """
            # Get all relevant request information
            diagnostic_info = {
                "server": {
                    "host": self.host,
                    "port": self.port,
                    "flutter_dir": str(self.flutter_dir),
                    "build_dir": str(self.build_dir),
                    "build_exists": self.build_dir.exists(),
                    "mdns_enabled": self.mdns_enabled,
                    "mdns_name": self.mdns_name if self.mdns_enabled else None,
                    "mdns_url": (
                        f"http://{self.mdns_name}.local:{self.port}"
                        if self.mdns_enabled
                        else None
                    ),
                    "local_ip": self._get_local_ip(),
                },
                "request": {
                    "url": request.url,
                    "base_url": request.base_url,
                    "host": request.headers.get("Host", "N/A"),
                    "origin": request.headers.get("Origin", "N/A"),
                    "referer": request.headers.get("Referer", "N/A"),
                    "user_agent": request.headers.get("User-Agent", "N/A"),
                },
                "expected_behavior": {
                    "flutter_app_should_detect": f"{request.scheme}://{request.host}",  # pylint: disable=line-too-long
                    "api_calls_should_go_to": f"{request.scheme}://{request.host}/api/...",  # pylint: disable=line-too-long
                },
                "troubleshooting": {
                    "if_api_calls_go_to_localhost": "Browser is using cached old JavaScript - clear cache",  # pylint: disable=line-too-long
                    "if_page_doesnt_load": "Check that Flutter app is built: make build-ui",  # pylint: disable=line-too-long
                    "if_cors_errors": "Check browser console for details",
                },
            }

            logger.info(
                "Diagnostic endpoint called from: %s", request.remote_addr
            )
            return jsonify(diagnostic_info)

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

    def add_image_directory(self, directory: str):
        """
        Add a directory to scan for images.

        Args:
            directory: Path to the directory containing captured images
        """
        if directory not in self.image_directories:
            self.image_directories.append(directory)
            logger.info("Added image directory: %s", directory)

    def _get_local_ip(self) -> str:
        """
        Get the local IP address of this machine.

        Returns:
            Local IP address as string, or '127.0.0.1' if unable to determine
        """
        try:
            # Create a socket to determine local IP
            # This doesn't actually connect, just determines routing
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except OSError as e:
            logger.warning("Could not determine local IP: %s", e)
            return "127.0.0.1"

    def _start_mdns(self):
        """Start mDNS/Zeroconf service advertisement."""
        if not self.mdns_enabled:
            return

        try:
            # Get local IP address
            local_ip = self._get_local_ip()

            # Create Zeroconf instance
            self.zeroconf = Zeroconf()

            # Create service info
            # Service type: _http._tcp.local.
            service_type = "_http._tcp.local."
            service_name = f"{self.mdns_name}.{service_type}"

            # Get IP as bytes
            ip_bytes = socket.inet_aton(local_ip)

            # Create service info
            self.service_info = ServiceInfo(
                service_type,
                service_name,
                addresses=[ip_bytes],
                port=self.port,
                properties={
                    "version": "1.0.0",
                    "path": "/",
                    "app": "pumaguard",
                },
                server=f"{self.mdns_name}.local.",
            )

            # Register service
            self.zeroconf.register_service(self.service_info)

            logger.info(
                "mDNS service registered: %s at %s:%d",
                service_name,
                local_ip,
                self.port,
            )
            logger.info(
                "Server accessible at: http://%s.local:%d",
                self.mdns_name,
                self.port,
            )
        except OSError as e:
            logger.error("Failed to start mDNS service: %s", e)
            self.zeroconf = None
            self.service_info = None

    def _stop_mdns(self):
        """Stop mDNS/Zeroconf service advertisement."""
        if self.zeroconf and self.service_info:
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
                logger.info("mDNS service unregistered")
            except OSError as e:
                logger.error("Error stopping mDNS service: %s", e)
            finally:
                self.zeroconf = None
                self.service_info = None

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

        # Start mDNS service
        self._start_mdns()

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

        # Stop mDNS service
        self._stop_mdns()

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
        "--no-mdns",
        action="store_true",
        help="Disable mDNS/Zeroconf service advertisement",
    )
    parser.add_argument(
        "--mdns-name",
        type=str,
        default="pumaguard",
        help="mDNS service name (default: pumaguard)",
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
        presets=presets,
        host=args.host,
        port=args.port,
        debug=args.debug,
        mdns_enabled=not args.no_mdns,
        mdns_name=args.mdns_name,
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
