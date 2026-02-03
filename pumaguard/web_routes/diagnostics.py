"""Diagnostics routes for server status and troubleshooting info."""

from __future__ import (
    annotations,
)

import time
from typing import (
    TYPE_CHECKING,
)

from flask import (
    jsonify,
    request,
)

import pumaguard
from pumaguard.presets import (
    get_xdg_cache_home,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )


def register_diagnostics_routes(app: "Flask", webui: "WebUI") -> None:
    """Register diagnostics endpoints for status and debug info."""

    @app.route("/api/status", methods=["GET"])
    def get_status():
        origin = request.headers.get("Origin", "No Origin header")
        host = request.headers.get("Host", "No Host header")

        # Calculate uptime in seconds
        uptime_seconds = int(time.time() - webui.start_time)

        return jsonify(
            {
                "status": "running",
                "version": pumaguard.__version__,
                "directories_count": len(webui.image_directories),
                "host": webui._get_local_ip(),  # pylint: disable=protected-access
                "port": webui.port,
                "uptime_seconds": uptime_seconds,
                "request_origin": origin,
                "request_host": host,
            }
        )

    @app.route("/api/diagnostic", methods=["GET"])
    def get_diagnostic():
        # Get log file path
        log_dir = get_xdg_cache_home() / "pumaguard"
        log_file = log_dir / "pumaguard.log"

        diagnostic_info = {
            "server": {
                "host": webui.host,
                "port": webui.port,
                "flutter_dir": str(webui.flutter_dir),
                "build_dir": str(webui.build_dir),
                "build_exists": webui.build_dir.exists(),
                "mdns_enabled": webui.mdns_enabled,
                "mdns_name": webui.mdns_name if webui.mdns_enabled else None,
                "mdns_url": (
                    f"http://{webui.mdns_name}.local:{webui.port}"
                    if webui.mdns_enabled
                    else None
                ),
                "local_ip": webui._get_local_ip(),  # pylint: disable=protected-access
                "log_file": str(log_file),
                "log_file_exists": log_file.exists(),
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
                "flutter_app_should_detect": (
                    f"{request.scheme}://{request.host}"
                ),
                "api_calls_should_go_to": (
                    f"{request.scheme}://{request.host}/api/..."
                ),
            },
            "troubleshooting": {
                "if_api_calls_go_to_localhost": (
                    "Browser is using cached old JavaScript - clear cache"
                ),
                "if_page_doesnt_load": (
                    "Check that Flutter app is built: make build-ui"
                ),
                "if_cors_errors": "Check browser console for details",
            },
        }
        return jsonify(diagnostic_info)
