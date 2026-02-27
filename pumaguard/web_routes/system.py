"""System routes for server administration and time synchronization."""

from __future__ import (
    annotations,
)

import logging
import os
import platform
import shutil
import subprocess
from datetime import (
    datetime,
    timezone,
)
from typing import (
    TYPE_CHECKING,
)

from flask import (
    jsonify,
    request,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


def register_system_routes(
    app: "Flask",
    webui: "WebUI",  # pylint: disable=unused-argument
) -> None:
    """Register system administration endpoints for time sync and status."""

    @app.route("/api/system/logs", methods=["GET"])
    def get_system_logs():
        """
        Retrieve system journal logs via journalctl.

        Query parameters:
            scope: 'unit' to get logs for pumaguard unit only,
                   'all' to get all system logs (default: 'unit')
            lines: number of lines to return, or 'all' (default: 'all')

        Returns:
            JSON with log lines and metadata
        """
        scope = request.args.get("scope", "unit")
        lines = request.args.get("lines", "all")

        if lines != "all":
            try:
                lines_int = int(lines)
            except ValueError:
                return (
                    jsonify(
                        {
                            "error": (
                                "invalid value for lines; "
                                + "either 'all' or a number"
                            ),
                            "logs": [],
                        }
                    ),
                    503,
                )
            if lines_int < 1:
                return (
                    jsonify(
                        {
                            "error": ("lines needs to be a positive integer"),
                            "logs": [],
                        }
                    ),
                    503,
                )

        if not shutil.which("journalctl"):
            return (
                jsonify(
                    {
                        "error": (
                            "journalctl is not available on this system"
                        ),
                        "logs": [],
                    }
                ),
                503,
            )

        try:
            cmd = ["journalctl", "--no-pager", "--lines", lines]

            if scope == "unit":
                cmd += ["--unit", "pumaguard"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )

            if result.returncode != 0 and result.stderr:
                logger.warning(
                    "journalctl returned non-zero exit code %d: %s",
                    result.returncode,
                    result.stderr.strip(),
                )

            log_lines = result.stdout.splitlines()

            return jsonify(
                {
                    "scope": scope,
                    "lines_requested": lines,
                    "line_count": len(log_lines),
                    "logs": log_lines,
                }
            )

        except subprocess.TimeoutExpired:
            logger.error("journalctl command timed out")
            return jsonify({"error": "Log retrieval timed out"}), 504
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error retrieving system logs")
            return jsonify({"error": "Failed to retrieve logs"}), 500

    @app.route("/api/system/time", methods=["GET"])
    def get_system_time():
        """
        Get the current server time.

        Returns:
            JSON with server timestamp, timezone, and formatted time
        """
        now = datetime.now(timezone.utc)
        local_now = datetime.now()

        return jsonify(
            {
                "timestamp": now.timestamp(),
                "iso": now.isoformat(),
                "local_iso": local_now.isoformat(),
                "timezone": "UTC",
            }
        )

    @app.route("/api/system/time", methods=["PUT"])
    def set_system_time():  # pylint: disable=too-many-return-statements
        """
        Set the server's system time.

        Expects JSON payload:
        {
            "timestamp": 1234567890.123  # Unix timestamp in seconds
        }
        or
        {
            "iso": "2024-01-15T10:30:00Z"  # ISO 8601 datetime string
        }

        Returns:
            JSON with success status and any error messages
        """
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400

            # Parse the time from either timestamp or ISO format
            target_time = None
            if "timestamp" in data:
                try:
                    target_time = datetime.fromtimestamp(
                        float(data["timestamp"]), tz=timezone.utc
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "Invalid timestamp format received: %s", str(e)
                    )
                    return (
                        jsonify({"error": "Invalid timestamp format"}),
                        400,
                    )
            elif "iso" in data:
                try:
                    # Parse ISO format (handles both UTC 'Z'
                    # and timezone aware)
                    iso_str = data["iso"]
                    if iso_str.endswith("Z"):
                        target_time = datetime.fromisoformat(
                            iso_str.replace("Z", "+00:00")
                        )
                    else:
                        target_time = datetime.fromisoformat(iso_str)

                    # Convert to UTC if not already
                    if target_time.tzinfo is None:
                        target_time = target_time.replace(tzinfo=timezone.utc)
                    else:
                        target_time = target_time.astimezone(timezone.utc)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "Invalid ISO datetime format received: %s", str(e)
                    )
                    return (
                        jsonify({"error": "Invalid ISO datetime format"}),
                        400,
                    )
            else:
                return (
                    jsonify(
                        {
                            "error": (
                                "Must provide either 'timestamp' "
                                "or 'iso' field"
                            )
                        }
                    ),
                    400,
                )

            # Attempt to set system time
            system = platform.system().lower()
            success, message = _set_system_time(target_time, system)

            if success:
                logger.info("System time set to %s", target_time.isoformat())
                return jsonify(
                    {
                        "success": True,
                        "message": message,
                        "new_time": target_time.isoformat(),
                    }
                )

            logger.error("Failed to set system time: %s", message)
            return jsonify({"error": message}), 500

        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error setting system time")
            return jsonify({"error": "Internal error"}), 500


def _set_system_time(  # pylint: disable=too-many-return-statements
    target_time: datetime, system: str
) -> tuple[bool, str]:
    """
    Set system time using platform-specific commands.

    Args:
        target_time: Target datetime in UTC
        system: Platform system name ('linux', 'darwin', 'windows')

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if system == "linux":
            # Try timedatectl first (systemd-based systems)
            if _command_exists("timedatectl"):
                try:
                    # Format: YYYY-MM-DD HH:MM:SS
                    time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
                    result = subprocess.run(
                        ["timedatectl", "set-time", time_str],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=5,
                    )

                    if result.returncode == 0:
                        return True, "Time set successfully using timedatectl"
                    if (
                        "authentication" in result.stderr.lower()
                        or "permission" in result.stderr.lower()
                    ):
                        return False, (
                            "Permission denied. Server needs appropriate "
                            + "permissions (sudo/CAP_SYS_TIME) to set system "
                            + "time. Error: "
                            + result.stderr.strip()
                        )
                    # Fall through to try date command
                    logger.debug(
                        "timedatectl failed (%s), trying date command",
                        result.stderr.strip(),
                    )
                except subprocess.TimeoutExpired:
                    logger.warning("timedatectl command timed out")

            # Try date command as fallback
            if _command_exists("date"):
                # Use Unix timestamp format for better compatibility
                result = subprocess.run(
                    ["date", "-u", "-s", f"@{int(target_time.timestamp())}"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )

                if result.returncode == 0:
                    return True, "Time set successfully using date command"
                if (
                    "permission" in result.stderr.lower()
                    or "operation not permitted" in result.stderr.lower()
                ):
                    return False, (
                        "Permission denied. Server needs appropriate "
                        + "permissions (sudo/CAP_SYS_TIME) to set system "
                        + "time. Error: "
                        + result.stderr.strip()
                    )
                return (
                    False,
                    f"Failed to set time: {result.stderr.strip()}",
                )

            return (
                False,
                "No suitable time-setting command found on Linux",
            )

        if system == "darwin":  # macOS
            if not _command_exists("date"):
                return False, "date command not found"

            # macOS date format: MMDDhhmm[[CC]YY][.ss]
            time_str = target_time.strftime("%m%d%H%M%Y.%S")
            result = subprocess.run(
                ["date", "-u", time_str],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )

            if result.returncode == 0:
                return True, "Time set successfully on macOS"
            if "permission" in result.stderr.lower():
                return False, (
                    "Permission denied. Server needs to run with sudo "
                    + "to set system time on macOS. Error: "
                    + result.stderr.strip()
                )
            return False, f"Failed to set time: {result.stderr.strip()}"

        if system == "windows":
            # Windows time command format: HH:MM:SS
            time_str = target_time.strftime("%H:%M:%S")
            result = subprocess.run(
                ["time", time_str],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
                shell=True,
            )

            if result.returncode == 0:
                # Also set date
                date_str = target_time.strftime("%m-%d-%Y")
                result = subprocess.run(
                    ["date", date_str],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                    shell=True,
                )

                if result.returncode == 0:
                    return True, "Time set successfully on Windows"
                return (
                    False,
                    f"Failed to set date: {result.stderr.strip()}",
                )
            if (
                "permission" in result.stderr.lower()
                or "access" in result.stderr.lower()
            ):
                return False, (
                    "Permission denied. Server needs to run as Administrator "
                    + "to set system time on Windows. Error: "
                    + result.stderr.strip()
                )
            return False, f"Failed to set time: {result.stderr.strip()}"

        return False, f"Unsupported platform: {system}"

    except subprocess.TimeoutExpired:
        return False, "Time-setting command timed out"
    except FileNotFoundError as e:
        # Log the specific missing command but return a generic message
        logger.warning("Time-setting command not found: %s", str(e))
        return False, "Time-setting command not available on this system"
    except Exception:  # pylint: disable=broad-except
        return False, "Unexpected error while setting system time"


def _command_exists(command: str) -> bool:
    """
    Check if a command exists in the system PATH.

    Args:
        command: Command name to check

    Returns:
        True if command exists, False otherwise
    """
    try:
        result = subprocess.run(
            ["which", command] if os.name != "nt" else ["where", command],
            capture_output=True,
            check=False,
            timeout=2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
