"""
Web-UI for Pumaguard.
"""

import logging
import os
import subprocess
import threading
from pathlib import Path

from flask import Flask, send_file, send_from_directory

logger = logging.getLogger(__name__)


class WebUI:
    def __init__(self, host="127.0.0.1", port=5000, debug=False):
        """
        Initialize the WebUI server.

        Args:
            host: The host to bind to (default: 127.0.0.1)
            port: The port to bind to (default: 5000)
            debug: Enable debug mode (default: False)
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.app = Flask(__name__)
        self.server_thread = None
        self._running = False

        # Determine the Flutter build directory
        # This assumes the Flutter app has been built for web
        self.flutter_dir = Path(__file__).parent.parent / "web-ui-flutter"
        self.build_dir = self.flutter_dir / "build" / "web"

        self._setup_routes()

    def _setup_routes(self):
        """Set up Flask routes to serve the Flutter web app."""

        @self.app.route("/")
        def index():
            """Serve the main index.html file."""
            if not self.build_dir.exists():
                return (
                    "Flutter web app not built. Please run 'flutter build web' "
                    f"in the {self.flutter_dir} directory first.",
                    500,
                )
            return send_file(self.build_dir / "index.html")

        @self.app.route("/<path:path>")
        def serve_static(path):
            """Serve static files (JS, CSS, assets, etc.)."""
            if not self.build_dir.exists():
                return (
                    "Flutter web app not built. Please run 'flutter build web' "
                    f"in the {self.flutter_dir} directory first.",
                    500,
                )

            file_path = self.build_dir / path
            if file_path.exists() and file_path.is_file():
                return send_from_directory(self.build_dir, path)
            else:
                # For client-side routing, return index.html for non-existent paths
                return send_file(self.build_dir / "index.html")

    def build_flutter_app(self):
        """
        Build the Flutter web app.

        Returns:
            bool: True if build was successful, False otherwise
        """
        if not self.flutter_dir.exists():
            logger.error(f"Flutter directory not found: {self.flutter_dir}")
            return False

        try:
            logger.info("Building Flutter web app...")
            result = subprocess.run(
                ["flutter", "build", "web"],
                cwd=self.flutter_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Flutter build completed successfully")
            logger.debug(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Flutter build failed: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error(
                "Flutter command not found. Please ensure Flutter is installed and in PATH."
            )
            return False

    def _run_server(self):
        """Internal method to run the Flask server."""
        self.app.run(
            host=self.host,
            port=self.port,
            debug=self.debug,
            use_reloader=False,
        )

    def start(self, auto_build=True):
        """
        Start the web-ui server.

        Args:
            auto_build: Automatically build the Flutter app if not already built (default: True)
        """
        if self._running:
            logger.warning("Server is already running")
            return

        # Check if Flutter app is built, build it if needed
        if not self.build_dir.exists():
            if auto_build:
                logger.info("Flutter build not found, building now...")
                if not self.build_flutter_app():
                    logger.error(
                        "Failed to build Flutter app. Cannot start server."
                    )
                    return
            else:
                logger.error(
                    f"Flutter build directory not found: {self.build_dir}\n"
                    f"Please run 'flutter build web' in {self.flutter_dir} first, "
                    "or call start(auto_build=True)"
                )
                return

        logger.info(f"Starting WebUI server on http://{self.host}:{self.port}")
        self._running = True

        if self.debug:
            # Run in the main thread for debug mode
            self._run_server()
        else:
            # Run in a separate thread for production
            self.server_thread = threading.Thread(
                target=self._run_server, daemon=True
            )
            self.server_thread.start()
            logger.info("WebUI server started successfully")

    def stop(self):
        """
        Stop the web-ui server.

        Note: Stopping a Flask server cleanly is complex.
        This implementation uses threading, so the server will stop when the main program exits.
        For production use, consider using a production WSGI server like Gunicorn or Waitress.
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
    """Start the WebUI server from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Pumaguard Web UI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to bind to"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode"
    )
    parser.add_argument(
        "--no-auto-build",
        action="store_true",
        help="Disable automatic Flutter build",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    web_ui = WebUI(host=args.host, port=args.port, debug=args.debug)
    web_ui.start(auto_build=not args.no_auto_build)

    if not args.debug:
        # Keep the main thread alive
        try:
            import time

            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            web_ui.stop()


if __name__ == "__main__":
    main()
