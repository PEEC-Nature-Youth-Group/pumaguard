"""Diagnostics routes for server status and troubleshooting info."""

from __future__ import (
    annotations,
)

import json
import logging
import re
import subprocess
import time
from typing import (
    TYPE_CHECKING,
    Any,
)

from flask import (
    jsonify,
    request,
)

import pumaguard
from pumaguard.presets import (
    get_xdg_cache_home,
)

logger = logging.getLogger(__name__)

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

    @app.route("/api/sensors/current", methods=["GET"])
    def get_sensors_current():
        """
        Return the current sensor readings from lm-sensors.

        Runs ``sensors -j`` and returns its parsed JSON output directly.
        Each top-level key is a chip name; values are dicts of sensor
        readings.  Keys ending in ``_input`` hold the current value.

        Response JSON::

            {
              "available": true,
              "timestamp": "2024-01-15T10:30:00Z",
              "sensors": { <raw sensors -j output> }
            }
        """
        available = _command_exists("sensors")
        if not available:
            return jsonify(
                {
                    "available": False,
                    "timestamp": _utcnow(),
                    "sensors": {},
                }
            )

        result = subprocess.run(
            ["sensors", "-j"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        if result.returncode != 0:
            logger.warning(
                "sensors -j failed (rc=%d): %s",
                result.returncode,
                result.stderr.strip(),
            )
            return jsonify(
                {
                    "available": True,
                    "timestamp": _utcnow(),
                    "sensors": {},
                    "error": "sensors command failed",
                }
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            logger.warning("Could not parse sensors -j output: %s", exc)
            return jsonify(
                {
                    "available": True,
                    "timestamp": _utcnow(),
                    "sensors": {},
                    "error": "Could not parse sensor output",
                }
            )

        return jsonify(
            {
                "available": True,
                "timestamp": _utcnow(),
                "sensors": data,
            }
        )

    @app.route("/api/sensors/history", methods=["GET"])
    def get_sensors_history():
        """
        Return historical sensor readings collected by the lm-sensors.timer.

        The timer runs ``sensors`` (via lm-sensors.service) every 5 minutes
        and its output is captured in the systemd journal.  This endpoint
        replays those journal entries over the requested time window.

        Query parameters:

        - ``hours`` – how many hours of history to return (default: 1,
          max: 168 = 7 days)

        Response JSON::

            {
              "available": true,
              "hours": 1,
              "readings": [
                {
                  "timestamp": "2024-01-15T10:30:00Z",
                  "sensors": { <raw sensors -j output for that run> }
                },
                ...
              ]
            }

        Readings are sorted oldest-first so a chart can plot them directly
        on a time axis.
        """
        try:
            hours = max(1, min(168, int(request.args.get("hours", 1))))
        except (ValueError, TypeError):
            hours = 1

        available = _command_exists("journalctl") and _command_exists(
            "sensors"
        )
        if not available:
            return jsonify(
                {
                    "available": False,
                    "hours": hours,
                    "readings": [],
                }
            )

        since = f"{hours} hours ago"
        cmd = [
            "journalctl",
            "--unit=lm-sensors.service",
            f"--since={since}",
            "--output=json",
            "--no-pager",
        ]
        logger.info("sensors/history: running %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        logger.info(
            "sensors/history: journalctl rc=%d, stdout=%d bytes, stderr=%r",
            result.returncode,
            len(result.stdout),
            result.stderr.strip(),
        )

        if result.returncode != 0:
            logger.warning(
                "journalctl failed (rc=%d): %s",
                result.returncode,
                result.stderr.strip(),
            )
            return jsonify(
                {
                    "available": True,
                    "hours": hours,
                    "readings": [],
                    "error": "Could not read journal",
                }
            )

        # Each line of `sensors` output is a separate journal entry sharing
        # the same INVOCATION_ID.  Group them first, then reassemble the
        # full multi-line text before parsing.
        #
        # invocation_id → {"lines": [...], "timestamp_us": int}
        runs: dict[str, dict[str, Any]] = {}

        raw_lines = result.stdout.splitlines()
        logger.info(
            "sensors/history: journal returned %d raw lines", len(raw_lines)
        )

        skipped_parse_error = 0
        skipped_transport = 0
        skipped_no_inv_id = 0

        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                skipped_parse_error += 1
                logger.debug(
                    "sensors/history: JSON parse error (%s) on line: %r",
                    exc,
                    line[:120],
                )
                continue

            transport = entry.get("_TRANSPORT")

            # Only care about stdout lines from the sensors process itself,
            # not systemd bookkeeping messages (which have no useful content).
            if transport != "stdout":
                skipped_transport += 1
                logger.debug(
                    "sensors/history: skipping entry with _TRANSPORT=%r, MESSAGE=%r",
                    transport,
                    entry.get("MESSAGE", "")[:80],
                )
                continue

            inv_id = entry.get("_SYSTEMD_INVOCATION_ID", "")
            if not inv_id:
                skipped_no_inv_id += 1
                logger.debug(
                    "sensors/history: stdout entry has no _SYSTEMD_INVOCATION_ID, MESSAGE=%r",
                    entry.get("MESSAGE", "")[:80],
                )
                continue

            message = entry.get("MESSAGE", "")
            ts_us = entry.get("__REALTIME_TIMESTAMP")

            if inv_id not in runs:
                logger.debug(
                    "sensors/history: new invocation %s... at ts=%s",
                    inv_id[:8],
                    ts_us,
                )
                runs[inv_id] = {"lines": [], "timestamp_us": ts_us}
            else:
                # Keep the timestamp of the last line in the run so that
                # the reading is stamped when the run completed.
                if ts_us is not None:
                    runs[inv_id]["timestamp_us"] = ts_us

            runs[inv_id]["lines"].append(message)

        logger.info(
            "sensors/history: skipped %d JSON-errors, %d non-stdout, %d no-inv-id; "
            "grouped into %d run(s)",
            skipped_parse_error,
            skipped_transport,
            skipped_no_inv_id,
            len(runs),
        )

        readings: list[dict[str, Any]] = []

        for inv_id, run in runs.items():
            ts_us = run["timestamp_us"]
            logger.info(
                "sensors/history: processing run %s... (%d lines, ts=%s)",
                inv_id[:8],
                len(run["lines"]),
                ts_us,
            )
            if ts_us is None:
                logger.debug(
                    "sensors/history: run %s... has no timestamp, skipping",
                    inv_id[:8],
                )
                continue
            try:
                ts_s = int(ts_us) / 1_000_000
            except (ValueError, TypeError) as exc:
                logger.debug(
                    "sensors/history: run %s... bad timestamp %r (%s), skipping",
                    inv_id[:8],
                    ts_us,
                    exc,
                )
                continue

            full_text = "\n".join(run["lines"])
            logger.debug(
                "sensors/history: run %s... full_text (%d chars):\n%s",
                inv_id[:8],
                len(full_text),
                full_text,
            )
            sensor_data = _parse_sensors_text(full_text)
            logger.info(
                "sensors/history: run %s... parsed %d chip(s) with temperature data: %s",
                inv_id[:8],
                len(sensor_data),
                list(sensor_data.keys()),
            )
            if not sensor_data:
                logger.warning(
                    "sensors/history: run %s... yielded no temperature readings, skipping",
                    inv_id[:8],
                )
                continue

            readings.append(
                {
                    "timestamp": _ts_to_iso(ts_s),
                    "sensors": sensor_data,
                }
            )

        logger.info(
            "sensors/history: returning %d reading(s) for %d-hour window",
            len(readings),
            hours,
        )

        # Sort oldest-first for charting
        readings.sort(key=lambda r: r["timestamp"])

        return jsonify(
            {
                "available": True,
                "hours": hours,
                "readings": readings,
            }
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _command_exists(cmd: str) -> bool:
    """Return True if *cmd* is found on PATH."""
    result = subprocess.run(
        ["which", cmd],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    import datetime  # pylint: disable=import-outside-toplevel

    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _ts_to_iso(ts_s: float) -> str:
    """Convert a POSIX timestamp (seconds) to an ISO-8601 UTC string."""
    import datetime  # pylint: disable=import-outside-toplevel

    return datetime.datetime.fromtimestamp(
        ts_s, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


# Regex that matches a chip header line produced by `sensors`.
# Chip names look like: "coretemp-isa-0000", "cpu_thermal-virtual-0",
# "pwmfan-isa-0000", "rp1_adc-isa-0000", etc.
# They consist only of word characters (letters, digits, underscores) and
# hyphens, with no spaces, and are never followed by a sensor value on the
# same line.  "Adapter: ..." lines are excluded separately.
_CHIP_HEADER_RE = re.compile(r"^[\w][\w\-]*$")

# Regex that matches a sensor value line, e.g.:
#   "temp1:        +45.8°C"          (no leading whitespace on Pi)
#   "  Core 0:  +71.0°C  (high=…)"  (leading whitespace on x86)
# Capture groups: (1) label, (2) numeric value, (3) unit
_SENSOR_VALUE_RE = re.compile(
    r"^\s*(.+?):\s*[+-]?(\d+(?:\.\d+)?)\s*(°C|RPM|V|mV|A|W|%)",
    re.UNICODE,
)


def _parse_sensors_text(text: str) -> dict[str, Any]:
    """
    Parse the plain-text output of ``sensors`` into a dict that mirrors
    the structure of ``sensors -j``.

    Only temperature readings (lines containing °C) are extracted since
    those are the primary interest for the graph.  The result is keyed by
    chip name, with each chip containing a dict of sensor-name → value.

    This parser does **not** rely on leading whitespace to distinguish chip
    headers from sensor value lines, because ``sensors`` on the Raspberry Pi
    outputs everything flush-left with no indentation.  Instead, chip headers
    are identified by their format: alphanumeric + hyphens only, no spaces,
    no colon-separated value on the same line.

    Example Pi output (no indentation)::

        cpu_thermal-virtual-0
        Adapter: Virtual device
        temp1:        +45.8°C

    Example x86 output (indented values)::

        coretemp-isa-0000
        Adapter: ISA adapter
          Core 0:  +71.0°C  (high = +100.0°C, crit = +100.0°C)

    Both produce::

        {"cpu_thermal-virtual-0": {"temp1": {"temp_input": 45.8}}}
    """
    chips: dict[str, Any] = {}
    current_chip: str | None = None

    for line in text.splitlines():
        stripped = line.strip()

        # Blank line — reset chip context
        if not stripped:
            current_chip = None
            continue

        # "Adapter: ..." lines carry no useful data
        if stripped.startswith("Adapter:"):
            continue

        # Chip header: matches word-chars and hyphens only, no spaces
        if _CHIP_HEADER_RE.match(stripped):
            current_chip = stripped
            chips.setdefault(current_chip, {})
            continue

        if current_chip is None:
            continue

        # Sensor value line — only record temperature readings (°C)
        m = _SENSOR_VALUE_RE.match(stripped)
        if m and m.group(3) == "°C":
            label = m.group(1).strip()
            value = float(m.group(2))
            chips[current_chip][label] = {"temp_input": value}

    # Remove chips with no temperature sensors
    return {k: v for k, v in chips.items() if v}
