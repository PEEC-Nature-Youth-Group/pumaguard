"""
System routes for server administration and time synchronization
"""

# pylint: disable=too-many-lines

from __future__ import (
    annotations,
)

import glob
import io
import logging
import os
import platform
import shutil
import subprocess
import zipfile
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
    send_file,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)

# Managed services that can be queried and restarted through the API.
# Only these two names are accepted by the restart endpoint.
_MANAGED_SERVICES = frozenset({"hostapd", "dnsmasq"})


def _get_service_status(service: str) -> dict:
    """
    Return a status dict for a single systemd service.

    Uses ``systemctl is-active`` (exit 0 = active) and
    ``systemctl is-enabled`` (exit 0 = enabled) so that we never need
    ``sudo`` and the calls are fast.

    Returns a dict with keys:
        name      – service name
        active    – bool: True when systemctl is-active reports "active"
        enabled   – bool: True when systemctl is-enabled reports "enabled"
        state     – str: raw output of ``systemctl is-active`` (e.g.
                    "active", "inactive", "failed", "activating", …)
        available – bool: False when systemctl itself is not on PATH
    """
    if not _command_exists("systemctl"):
        return {
            "name": service,
            "active": False,
            "enabled": False,
            "state": "unavailable",
            "available": False,
        }

    try:
        active_result = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        state = active_result.stdout.strip() or "unknown"
        active = active_result.returncode == 0

        enabled_result = subprocess.run(
            ["systemctl", "is-enabled", service],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        enabled = enabled_result.returncode == 0

    except subprocess.TimeoutExpired:
        logger.warning("systemctl timed out querying service %s", service)
        return {
            "name": service,
            "active": False,
            "enabled": False,
            "state": "timeout",
            "available": True,
        }
    except Exception:  # pylint: disable=broad-except
        logger.exception("Unexpected error querying service %s", service)
        return {
            "name": service,
            "active": False,
            "enabled": False,
            "state": "error",
            "available": True,
        }

    return {
        "name": service,
        "active": active,
        "enabled": enabled,
        "state": state,
        "available": True,
    }


def register_system_routes(
    app: "Flask",
    webui: "WebUI",  # pylint: disable=unused-argument
) -> None:
    """Register system administration endpoints for time sync and status."""

    @app.route("/api/system/services", methods=["GET"])
    def get_services():
        """
        Return the current status of the managed infrastructure services
        (``hostapd`` and ``dnsmasq``).

        Response body::

            {
              "services": [
                {
                  "name": "hostapd",
                  "active": true,
                  "enabled": true,
                  "state": "active",
                  "available": true
                },
                {
                  "name": "dnsmasq",
                  "active": false,
                  "enabled": true,
                  "state": "failed",
                  "available": true
                }
              ]
            }
        """
        services = [
            _get_service_status(svc) for svc in sorted(_MANAGED_SERVICES)
        ]
        return jsonify({"services": services})

    @app.route(
        "/api/system/services/<string:service_name>/restart", methods=["POST"]
    )
    def restart_service(service_name: str):
        """
        Restart a managed infrastructure service.

        Only ``hostapd`` and ``dnsmasq`` are accepted; any other name returns
        ``400``.  The restart is performed with
        ``sudo systemctl restart <service>``, which requires a matching
        ``sudoers`` entry for the user running PumaGuard – for example::

            pumaguard ALL=(ALL) NOPASSWD: /bin/systemctl restart hostapd
            pumaguard ALL=(ALL) NOPASSWD: /bin/systemctl restart dnsmasq

        Response on success (HTTP 200)::

            {"success": true, "message": "hostapd restarted successfully",
             "service": { ... current status ... }}

        Response on failure (HTTP 500)::

            {"error": "Failed to restart hostapd: ..."}
        """
        if service_name not in _MANAGED_SERVICES:
            return (
                jsonify(
                    {
                        "error": (
                            f"Unknown service '{service_name}'. "
                            f"Allowed services: {sorted(_MANAGED_SERVICES)}"
                        )
                    }
                ),
                400,
            )

        if not _command_exists("systemctl"):
            return (
                jsonify(
                    {"error": "systemctl is not available on this system"}
                ),
                503,
            )

        logger.info("Restarting service: %s", service_name)
        try:
            # Use sudo with the full systemctl path and the ".service" suffix
            # to exactly match the sudoers drop-in grants, e.g.:
            #   pumaguard ALL=(ALL) NOPASSWD: /usr/bin/systemctl \
            #     restart hostapd.service
            # Note: NoNewPrivileges must NOT be set in pumaguard.service or
            # sudo will be blocked regardless of what sudoers permits.
            result = subprocess.run(
                [
                    "sudo",
                    "/usr/bin/systemctl",
                    "restart",
                    f"{service_name}.service",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            logger.error("Timed out while restarting %s", service_name)
            return (
                jsonify({"error": f"Timed out restarting {service_name}"}),
                504,
            )
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unexpected error restarting %s", service_name)
            return jsonify({"error": f"Failed to restart {service_name}"}), 500

        if result.returncode != 0:
            error_detail = result.stderr.strip() or result.stdout.strip()
            logger.error(
                "systemctl restart %s failed (rc=%d): %s",
                service_name,
                result.returncode,
                error_detail,
            )
            return (
                jsonify(
                    {
                        "error": (
                            f"Failed to restart {service_name}: {error_detail}"
                        )
                    }
                ),
                500,
            )

        logger.info("Service %s restarted successfully", service_name)
        # Return the fresh status so the UI can update immediately without a
        # separate round-trip.
        current_status = _get_service_status(service_name)
        return jsonify(
            {
                "success": True,
                "message": f"{service_name} restarted successfully",
                "service": current_status,
            }
        )

    @app.route("/api/system/logs", methods=["GET"])
    def get_system_logs():
        """
        Retrieve system journal logs via journalctl.

        Query parameters:
            scope: 'unit' to get logs for pumaguard unit only,
                   'all' to get all system logs (default: 'unit')
            since: journalctl --since value, e.g. '1 hour ago', '2024-01-01',
                   or 'boot'. When provided, --lines is omitted so the full
                   time window is returned. (default: '1 hour ago')
            lines: number of lines to return, or 'all'. Only used when
                   'since' is explicitly set to the empty string to request
                   all lines with no time bound. (default: ignored when
                   since is set)

        Returns:
            JSON with log lines and metadata
        """
        scope = request.args.get("scope", "unit")
        # A missing 'since' defaults to the last hour.  Passing since='' (or
        # since=all) explicitly opts out of the time window and falls back to
        # the 'lines' parameter instead.
        since_raw = request.args.get("since", "1 hour ago")
        use_since = since_raw not in ("", "all")

        lines = request.args.get("lines", "all")

        if not use_since and lines != "all":
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
            cmd = ["journalctl", "--no-pager"]

            if use_since:
                cmd += ["--since", since_raw]
            else:
                cmd += ["--lines", lines]

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
                    "since": since_raw if use_since else None,
                    "lines_requested": None if use_since else lines,
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

    @app.route("/api/system/poweroff", methods=["POST"])
    def poweroff():
        """
        Power off the device by running ``sudo systemctl poweroff``.

        The user running PumaGuard must have a matching ``sudoers`` entry,
        for example::

            pumaguard ALL=(ALL) NOPASSWD: /usr/bin/systemctl poweroff

        Response on success (HTTP 200)::

            {"success": true, "message": "System is powering off"}

        Response when ``systemctl`` is unavailable (HTTP 503)::

            {"error": "systemctl is not available on this system"}

        Response on failure (HTTP 500)::

            {"error": "Failed to initiate poweroff: ..."}
        """
        if not _command_exists("systemctl"):
            return (
                jsonify(
                    {"error": "systemctl is not available on this system"}
                ),
                503,
            )

        logger.info("Initiating system poweroff")
        try:
            result = subprocess.run(
                ["sudo", "/usr/bin/systemctl", "poweroff"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            logger.error("Timed out while initiating poweroff")
            return jsonify({"error": "Timed out initiating poweroff"}), 504
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unexpected error initiating poweroff")
            return jsonify({"error": "Failed to initiate poweroff"}), 500

        if result.returncode != 0:
            error_detail = result.stderr.strip() or result.stdout.strip()
            logger.error(
                "systemctl poweroff failed (rc=%d): %s",
                result.returncode,
                error_detail,
            )
            return (
                jsonify(
                    {"error": f"Failed to initiate poweroff: {error_detail}"}
                ),
                500,
            )

        logger.info("System poweroff initiated successfully")
        return jsonify({"success": True, "message": "System is powering off"})

    @app.route("/api/system/sos-report", methods=["POST"])
    def generate_sos_report():  # pylint: disable=too-many-return-statements
        """
        Generate an SOS report by running::

            sos report --alloptions --all-logs --batch

        This can take a minute or more to complete.  On success the response
        contains the path to the generated tarball so the client can
        immediately trigger a download via

        ``GET /api/system/sos-report/download``.

        Requires ``sos`` to be installed and the ``pumaguard`` user to have a
        matching ``sudoers`` entry, for example::

            pumaguard ALL=(ALL) NOPASSWD: /usr/bin/sos

        Response on success (HTTP 200)::

            {
              "success": true,
              "message": "SOS report generated",
              "filename": "sosreport-hostname-2024…tar.xz",
              "path": "/tmp/sosreport-hostname-2024….tar.xz"
            }

        Response when ``sos`` is unavailable (HTTP 503)::

            {"error": "sos is not available on this system"}

        Response on failure (HTTP 500)::

            {"error": "Failed to generate SOS report: …"}
        """
        if not _command_exists("sos"):
            return (
                jsonify({"error": "sos is not available on this system"}),
                503,
            )

        logger.info("Generating SOS report (this may take a while)")
        try:
            result = subprocess.run(
                [
                    "sudo",
                    "/usr/bin/sos",
                    "report",
                    "--alloptions",
                    "--all-logs",
                    "--batch",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            logger.error("SOS report generation timed out")
            return jsonify({"error": "SOS report generation timed out"}), 504
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unexpected error generating SOS report")
            return jsonify({"error": "Failed to generate SOS report"}), 500

        if result.returncode != 0:
            error_detail = result.stderr.strip() or result.stdout.strip()
            logger.error(
                "sos report failed (rc=%d): %s",
                result.returncode,
                error_detail,
            )
            return (
                jsonify(
                    {
                        "error": (
                            f"Failed to generate SOS report: {error_detail}"
                        )
                    }
                ),
                500,
            )

        # Locate the generated tarball in /tmp.  sos writes files named like:
        #   sosreport-<hostname>-<date>-<hash>.tar.xz        (tarball)
        #   sosreport-<hostname>-<date>-<hash>.tar.xz.sha256 (checksum)
        # or (newer sos versions):
        #   sos-<hostname>-<date>-<hash>.tar.xz
        #   sos-<hostname>-<date>-<hash>.tar.xz.sha256
        # We deliberately exclude the .sha256 files here so that mtime
        # sorting always yields the tarball first.
        matches = sorted(
            [
                p
                for p in (
                    glob.glob("/tmp/sos*.tar.xz")
                    + glob.glob("/tmp/sos*.tar.gz")
                    + glob.glob("/tmp/sosreport*.tar.xz")
                    + glob.glob("/tmp/sosreport*.tar.gz")
                )
                if not p.endswith(".sha256")
            ],
            key=os.path.getmtime,
            reverse=True,
        )

        if not matches:
            logger.error(
                "sos report succeeded but no tarball found in /tmp. "
                "stdout: %s",
                result.stdout.strip(),
            )
            return (
                jsonify(
                    {
                        "error": (
                            "SOS report finished but the output file could "
                            "not be located in /tmp"
                        )
                    }
                ),
                500,
            )

        tarball_path = matches[0]
        tarball_name = os.path.basename(tarball_path)

        # The checksum file is the tarball path with ".sha256" appended.
        checksum_path = tarball_path + ".sha256"
        checksum_name = tarball_name + ".sha256"

        # sos runs as root via sudo, so the generated files are owned by root
        # and not readable by the pumaguard service user.  chmod them
        # world-readable so Flask can open and stream them.
        files_to_chmod = [tarball_path]
        if os.path.isfile(checksum_path):
            files_to_chmod.append(checksum_path)

        try:
            subprocess.run(
                ["sudo", "chmod", "o+r"] + files_to_chmod,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
        except subprocess.CalledProcessError as exc:
            error_detail = exc.stderr.strip() or exc.stdout.strip()
            logger.error("Failed to chmod SOS report files: %s", error_detail)
            return (
                jsonify(
                    {
                        "error": (
                            "SOS report generated but could not be made "
                            f"readable: {error_detail}"
                        )
                    }
                ),
                500,
            )
        except subprocess.TimeoutExpired:
            logger.error("Timed out while chmodding SOS report files")
            return (
                jsonify(
                    {
                        "error": (
                            "SOS report generated but timed out making "
                            "it readable"
                        )
                    }
                ),
                500,
            )

        logger.info("SOS report generated: %s", tarball_path)
        return jsonify(
            {
                "success": True,
                "message": "SOS report generated",
                "filename": tarball_name,
                "path": tarball_path,
                "checksum_filename": (
                    checksum_name if os.path.isfile(checksum_path) else None
                ),
                "checksum_path": (
                    checksum_path if os.path.isfile(checksum_path) else None
                ),
            }
        )

    @app.route("/api/system/sos-report/download", methods=["GET"])
    def download_sos_report():
        """
        Package the SOS report tarball and its ``.sha256`` checksum file into
        a ZIP archive and return it as a single download.

        Using ZIP_STORED (no recompression) keeps CPU overhead minimal — the
        ``.tar.xz`` is already compressed.

        An optional ``path`` query parameter pins a specific tarball::

            GET /api/system/sos-report/download?path=/tmp/sosreport-….tar.xz

        If omitted the most recently modified ``sos*.tar.xz`` / ``sos*.tar.gz``
        file in ``/tmp`` is used.

        Response on success (HTTP 200):
            ``application/zip`` stream named ``<tarball-stem>.zip``.

        Response when no report exists (HTTP 404)::

            {"error": "No SOS report found in /tmp"}

        Response when the requested file is outside /tmp (HTTP 400)::

            {"error": "Invalid file path"}
        """
        requested_path = request.args.get("path", "").strip()

        if requested_path:
            # Basic safety check: only allow files that live under /tmp.
            real = os.path.realpath(requested_path)
            if not real.startswith("/tmp/"):
                return jsonify({"error": "Invalid file path"}), 400
            tarball_path = real
            if not os.path.isfile(tarball_path):
                return (
                    jsonify(
                        {
                            "error": (
                                f"File not found: "
                                f"{os.path.basename(tarball_path)}"
                            )
                        }
                    ),
                    404,
                )
        else:
            matches = sorted(
                [
                    p
                    for p in (
                        glob.glob("/tmp/sos*.tar.xz")
                        + glob.glob("/tmp/sos*.tar.gz")
                        + glob.glob("/tmp/sosreport*.tar.xz")
                        + glob.glob("/tmp/sosreport*.tar.gz")
                    )
                    if not p.endswith(".sha256")
                ],
                key=os.path.getmtime,
                reverse=True,
            )
            if not matches:
                return jsonify({"error": "No SOS report found in /tmp"}), 404
            tarball_path = matches[0]

        tarball_name = os.path.basename(tarball_path)
        checksum_path = tarball_path + ".sha256"

        # Build the zip in memory.  ZIP_STORED avoids wasting CPU trying to
        # recompress an already-compressed .tar.xz.
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_STORED) as zf:
            logger.info("Adding to zip: %s", tarball_path)
            zf.write(tarball_path, tarball_name)
            if os.path.isfile(checksum_path):
                logger.info("Adding to zip: %s", checksum_path)
                zf.write(checksum_path, tarball_name + ".sha256")
        zip_buffer.seek(0)

        # Name the zip after the tarball stem, e.g.
        # sosreport-raspberrypi-2026-03-05-moudxyc.zip
        zip_name = (
            tarball_name.replace(".tar.xz", "").replace(".tar.gz", "") + ".zip"
        )
        logger.info("Sending SOS report zip: %s", zip_name)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=zip_name,
        )


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
                        ["sudo", "timedatectl", "set-time", time_str],
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
