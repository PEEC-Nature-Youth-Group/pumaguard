"""
Web-UI for Pumaguard.
"""

import argparse
import hashlib
import logging
import socket
import threading
import time
from pathlib import (
    Path,
)
from typing import (
    TYPE_CHECKING,
    TypedDict,
)

from flask import (
    Flask,
    jsonify,
    send_file,
    send_from_directory,
)
from flask_cors import (
    CORS,
)

# Note: YAMLError and yaml operations are handled in route modules
from zeroconf import (
    NonUniqueNameException,
    ServiceInfo,
    Zeroconf,
)

from pumaguard.camera_heartbeat import (
    CameraHeartbeat,
)
from pumaguard.plug_heartbeat import (
    PlugHeartbeat,
)
from pumaguard.presets import (
    Preset,
)
from pumaguard.web_routes.artifacts import (
    register_artifacts_routes,
)
from pumaguard.web_routes.dhcp import (
    register_dhcp_routes,
)
from pumaguard.web_routes.diagnostics import (
    register_diagnostics_routes,
)
from pumaguard.web_routes.directories import (
    register_directories_routes,
)
from pumaguard.web_routes.folders import (
    register_folders_routes,
)
from pumaguard.web_routes.photos import (
    register_photos_routes,
)
from pumaguard.web_routes.settings import (
    register_settings_routes,
)
from pumaguard.web_routes.sync import (
    register_sync_routes,
)

if TYPE_CHECKING:
    from pumaguard.server import (
        FolderManager,
    )

logger = logging.getLogger(__name__)


class CameraInfo(TypedDict):
    """Type definition for camera information stored in webui.cameras."""

    hostname: str
    ip_address: str
    mac_address: str
    last_seen: str
    status: str


class PlugInfo(TypedDict):
    """Type definition for plug information stored in webui.plugs."""

    hostname: str
    ip_address: str
    mac_address: str
    last_seen: str
    status: str
    mode: str


class PhotoDict(TypedDict):
    """Type definition for photo metadata dictionary."""

    filename: str
    path: str
    directory: str
    size: int
    modified: float
    created: float


class ArtifactDict(TypedDict):
    """Type definition for artifact metadata dictionary."""

    filename: str
    path: str
    ext: str
    kind: str
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
        self.classification_directories: list[str] = []

        # Track server start time for uptime calculation
        self.start_time: float = time.time()

        # Camera tracking - stores detected cameras by MAC address
        # Format: {mac_address: CameraInfo}
        self.cameras: dict[str, CameraInfo] = {}

        # Plug tracking - stores detected plugs by MAC address
        # Format: {mac_address: PlugInfo}
        self.plugs: dict[str, PlugInfo] = {}

        # Camera heartbeat monitoring (callback set after routes registered)
        self.heartbeat: CameraHeartbeat = CameraHeartbeat(
            webui=self,
            interval=presets.camera_heartbeat_interval,
            enabled=presets.camera_heartbeat_enabled,
            check_method=presets.camera_heartbeat_method,
            tcp_port=presets.camera_heartbeat_tcp_port,
            tcp_timeout=presets.camera_heartbeat_tcp_timeout,
            icmp_timeout=presets.camera_heartbeat_icmp_timeout,
            # Will be set after routes are registered
            status_change_callback=None,
        )

        # Plug heartbeat monitoring (callback set after routes registered)
        self.plug_heartbeat: PlugHeartbeat = PlugHeartbeat(
            webui=self,
            interval=presets.plug_heartbeat_interval,
            enabled=presets.plug_heartbeat_enabled,
            timeout=presets.plug_heartbeat_timeout,
            # Will be set after routes are registered
            status_change_callback=None,
        )

        # Load cameras from persisted settings
        for camera in presets.cameras:
            mac = camera.get("mac_address")
            if mac:
                self.cameras[mac] = CameraInfo(
                    hostname=camera.get("hostname", ""),
                    ip_address=camera.get("ip_address", ""),
                    mac_address=mac,
                    last_seen=camera.get("last_seen", ""),
                    status=camera.get("status", "disconnected"),
                )

        # Load plugs from persisted settings
        for plug in presets.plugs:
            mac = plug.get("mac_address")
            if mac:
                self.plugs[mac] = PlugInfo(
                    hostname=plug.get("hostname", ""),
                    ip_address=plug.get("ip_address", ""),
                    mac_address=mac,
                    last_seen=plug.get("last_seen", ""),
                    status=plug.get("status", "disconnected"),
                    mode=plug.get("mode", "off"),
                )

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
        """Set up Flask routes for the Flutter web app and API."""

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

        # Register modular route groups
        register_settings_routes(self.app, self)

        register_photos_routes(self.app, self)

        register_folders_routes(self.app, self)

        register_sync_routes(self.app, self)

        # Routes delegated to web_routes.artifacts

        register_directories_routes(self.app, self)

        register_diagnostics_routes(self.app, self)

        # Register DHCP routes and get the SSE notification callback
        camera_notification_callback = register_dhcp_routes(self.app, self)

        # Wire the callback to the heartbeat monitors
        self.heartbeat.status_change_callback = camera_notification_callback
        self.plug_heartbeat.status_change_callback = (
            camera_notification_callback
        )

        @self.app.route("/<path:path>")
        def serve_static(path: str):
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

        # Register artifacts after core routes
        register_artifacts_routes(self.app, self)

    def add_image_directory(self, directory: str):
        """
        Add a directory to scan for images (watched folder).

        Args:
            directory: Path to the directory containing captured images
        """
        if directory not in self.image_directories:
            self.image_directories.append(directory)
            logger.info("Added image directory: %s", directory)

    def add_classification_directory(self, directory: str):
        """
        Add a classification output directory (not watched, browse-only).

        Args:
            directory: Path to classification output directory
        """
        if directory not in self.classification_directories:
            self.classification_directories.append(directory)
            logger.info("Added classification directory: %s", directory)

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
            try:
                self.zeroconf.register_service(self.service_info)
            except NonUniqueNameException:
                logger.warning(
                    "mDNS service name '%s' already in use, "
                    + "attempting to unregister and re-register",
                    service_name,
                )
                # Try to unregister the existing service
                try:
                    self.zeroconf.unregister_service(self.service_info)
                    # Wait briefly for unregistration to complete
                    time.sleep(0.5)
                    # Try registering again
                    self.zeroconf.register_service(self.service_info)
                except Exception as e:
                    logger.error(
                        "Failed to re-register mDNS service after "
                        + "conflict: %s",
                        e,
                    )
                    raise

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
        except (OSError, NonUniqueNameException) as e:
            logger.error("Failed to start mDNS service: %s", e)
            if self.zeroconf:
                try:
                    self.zeroconf.close()
                except OSError:
                    pass
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

        # Start camera heartbeat monitoring
        self.heartbeat.start()

        # Start plug heartbeat monitoring
        self.plug_heartbeat.start()

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

        # Stop camera heartbeat monitoring
        self.heartbeat.stop()

        # Stop plug heartbeat monitoring
        self.plug_heartbeat.stop()

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

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

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
