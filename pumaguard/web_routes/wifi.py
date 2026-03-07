"""WiFi client configuration routes for the USB wireless adapter (wifi1).

Manages WPA supplicant credentials and network scanning for the USB Wi-Fi
adapter (matched to wlx* and renamed wifi1 by netplan).

Architecture
------------

- Ansible deploys /etc/netplan/91-pumaguard-wireless.yaml once, which
  matches any wlx* adapter, renames it wifi1, and enables dhcp4. It
  contains no credentials.
- At runtime, this module writes credentials to
  /etc/wpa_supplicant/wpa_supplicant-wifi1.conf and restarts
  wpa_supplicant@wifi1.service via passwordless sudo (granted by the
  pumaguard-wpa-supplicant sudoers drop-in).
- The list of configured networks is persisted in the pumaguard settings
  YAML under the key "wifi-networks" so it survives a pumaguard restart.
  On startup the settings are loaded and, if any networks are present,
  the wpa_supplicant config is re-written so wifi1 reconnects without
  manual intervention.

Endpoints
---------

::

    GET  /api/wifi/mode      – current wifi1 state (connected/disconnected,
                               SSID, IP address)
    GET  /api/wifi/scan      – list of visible networks seen by wifi1
    POST /api/wifi/mode      – add/replace a network and reconnect
    POST /api/wifi/forget    – remove a saved network by SSID

"""

# pyright: reportImportCycles=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false
# pyright: reportAny=false
# pyright: reportUnusedFunction=false
# pyright: reportExplicitAny=false

from __future__ import (
    annotations,
)

import logging
import re
import subprocess
from typing import (
    TYPE_CHECKING,
    Any,
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

# The interface name assigned by the netplan match rule.
_IFACE = "wifi1"

# Absolute path that pumaguard is allowed to write via ``sudo tee``.
_WPA_CONF = f"/etc/wpa_supplicant/wpa_supplicant-{_IFACE}.conf"

# systemd service instance for the interface.
_WPA_SERVICE = f"wpa_supplicant@{_IFACE}.service"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a subprocess, returning CompletedProcess regardless of exit code."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        **kwargs,
    )


def _iface_exists() -> bool:
    """Return True if the wifi1 interface is present in the system."""
    result = _run(["ip", "link", "show", _IFACE])
    return result.returncode == 0


def _get_current_ssid() -> str | None:
    """Return the SSID wifi1 is currently associated with, or None."""
    result = _run(["iw", "dev", _IFACE, "link"])
    if result.returncode != 0 or "Not connected" in result.stdout:
        return None
    match = re.search(r"SSID:\s*(.+)", result.stdout)
    return match.group(1).strip() if match else None


def _get_ip_address() -> str | None:
    """Return the IPv4 address assigned to wifi1, or None."""
    result = _run(["ip", "-4", "addr", "show", _IFACE])
    if result.returncode != 0:
        return None
    match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", result.stdout)
    return match.group(1) if match else None


def _get_signal_percent() -> int | None:
    """
    Return the signal strength as a percentage (0-100) for the current
    association, or None if not connected or the value cannot be parsed.

    ``iw dev wifi1 link`` reports signal in dBm, e.g. ``signal: -55 dBm``.
    We convert using the common -100 dBm (0 %) … -50 dBm (100 %) scale.
    """
    result = _run(["iw", "dev", _IFACE, "link"])
    if result.returncode != 0:
        return None
    match = re.search(r"signal:\s*(-?\d+)\s*dBm", result.stdout)
    if not match:
        return None
    dbm = int(match.group(1))
    pct = max(0, min(100, 2 * (dbm + 100)))
    return pct


def _build_wpa_conf(networks: list[dict[str, Any]]) -> str:
    """
    Render a wpa_supplicant.conf string from a list of network dicts.

    Each dict must have at minimum a key ``ssid``. Optional keys:
      ``psk``      – pre-shared key; omit or set to "" for open networks
      ``priority`` – integer; higher value = higher preference (default 0)
    """
    lines = [
        "# Managed by PumaGuard - do not edit manually.",
        "# Changes will be overwritten by the PumaGuard wifi API.",
        "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev",
        "update_config=1",
        "country=US",
        "",
    ]
    for net in networks:
        ssid = net.get("ssid", "")
        psk = net.get("psk", "")
        priority = int(net.get("priority", 0))
        lines.append("network={")
        lines.append(f'\tssid="{ssid}"')
        if psk:
            lines.append(f'\tpsk="{psk}"')
        else:
            # Open network
            lines.append("\tkey_mgmt=NONE")
        lines.append(f"\tpriority={priority}")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def _write_wpa_conf(networks: list[dict[str, Any]]) -> tuple[bool, str]:
    """
    Write the wpa_supplicant config file via ``sudo tee`` (permitted by the
    pumaguard-wpa-supplicant sudoers drop-in without a password).

    Returns (success, error_message).  The error_message is safe to surface
    in the UI — system-level detail is logged server-side only.
    """
    conf = _build_wpa_conf(networks)
    try:
        result = subprocess.run(
            ["sudo", "tee", _WPA_CONF],
            input=conf,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error(
                "Failed to write %s: %s",
                _WPA_CONF,
                result.stderr.strip() or result.stdout.strip(),
            )
            return False, "Failed to write WiFi configuration."
        return True, ""
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Exception writing %s: %s", _WPA_CONF, exc)
        return False, "Failed to write WiFi configuration."


def _restart_wpa_supplicant() -> tuple[bool, str]:
    """
    Restart wpa_supplicant@wifi1.service via sudo.

    Returns (success, error_message).  The error_message is safe to surface
    in the UI — system-level detail is logged server-side only.
    """
    try:
        result = _run(["sudo", "systemctl", "restart", _WPA_SERVICE])
        if result.returncode != 0:
            logger.error(
                "Failed to restart %s: %s",
                _WPA_SERVICE,
                result.stderr.strip() or result.stdout.strip(),
            )
            return False, "Failed to restart WiFi service."
        logger.info("Restarted %s", _WPA_SERVICE)
        return True, ""
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Exception restarting %s: %s", _WPA_SERVICE, exc)
        return False, "Failed to restart WiFi service."


def _scan_networks() -> list[dict[str, Any]]:
    """
    Trigger a scan on wifi1 and return a list of visible networks.

    Each entry is a dict with keys:
      ssid     – network name (str)
      signal   – signal strength as percentage 0-100 (int)
      security – human-readable security type string (str)
      secured  – True if the network requires a password (bool)

    Duplicate SSIDs are collapsed, keeping the entry with the highest signal.
    """
    # Trigger an active scan (best-effort; may fail if interface is busy)
    _run(["sudo", "ip", "link", "set", _IFACE, "up"])
    _run(["iw", "dev", _IFACE, "scan", "flush"])

    result = _run(["iw", "dev", _IFACE, "scan"])
    if result.returncode != 0:
        logger.warning("iw scan failed: %s", result.stderr.strip())
        return []

    networks: dict[str, dict[str, Any]] = {}

    current_ssid: str | None = None
    current_signal: int = 0
    current_security: str = "Open"
    current_secured: bool = False

    def _flush() -> None:
        if current_ssid is not None:
            existing = networks.get(current_ssid)
            if existing is None or existing["signal"] < current_signal:
                networks[current_ssid] = {
                    "ssid": current_ssid,
                    "signal": current_signal,
                    "security": current_security,
                    "secured": current_secured,
                }

    for line in result.stdout.splitlines():
        line = line.strip()

        # Start of a new BSS block
        if line.startswith("BSS "):
            _flush()
            current_ssid = None
            current_signal = 0
            current_security = "Open"
            current_secured = False
            continue

        ssid_match = re.match(r"SSID:\s*(.+)", line)
        if ssid_match:
            current_ssid = ssid_match.group(1).strip()
            continue

        signal_match = re.match(r"signal:\s*(-?\d+\.\d+|\-?\d+)\s*dBm", line)
        if signal_match:
            dbm = float(signal_match.group(1))
            current_signal = max(0, min(100, int(2 * (dbm + 100))))
            continue

        # Detect WPA2/RSN
        if re.match(r"RSN:", line):
            current_security = "WPA2"
            current_secured = True
            continue

        # Detect WPA
        if re.match(r"WPA:", line) and current_security == "Open":
            current_security = "WPA"
            current_secured = True
            continue

    _flush()

    return sorted(
        networks.values(),
        key=lambda n: n["signal"],
        reverse=True,
    )


def apply_wifi_networks_from_settings(webui: "WebUI") -> None:
    """
    Called at startup to re-apply any persisted wifi networks.

    If wifi-networks is non-empty in presets, write the wpa_supplicant
    config and (re)start the service so wifi1 connects without the
    operator having to go through the UI again.
    """
    if not webui.presets.wifi_networks:
        logger.debug("No persisted wifi networks to apply at startup.")
        return

    logger.info(
        "Applying %d persisted wifi network(s) to %s",
        len(webui.presets.wifi_networks),
        _WPA_CONF,
    )
    ok, err = _write_wpa_conf(webui.presets.wifi_networks)
    if not ok:
        logger.error(
            "Could not write wpa_supplicant config at startup: %s", err
        )
        return

    ok, err = _restart_wpa_supplicant()
    if not ok:
        logger.error(
            "Could not start wpa_supplicant@wifi1 at startup: %s", err
        )


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def register_wifi_routes(app: "Flask", webui: "WebUI") -> None:
    """Register /api/wifi/* endpoints."""

    @app.route("/api/wifi/mode", methods=["GET"])
    def get_wifi_mode():
        """
        Return the current state of wifi1.

        Response JSON:
          connected  – bool
          ssid       – str | null
          ip_address – str | null
          signal     – int (0-100) | null
          interface  – str  (always "wifi1")
          present    – bool  (False if no USB adapter is plugged in)
        """
        present = _iface_exists()
        if not present:
            return jsonify(
                {
                    "present": False,
                    "connected": False,
                    "ssid": None,
                    "ip_address": None,
                    "signal": None,
                    "interface": _IFACE,
                }
            )

        ssid = _get_current_ssid()
        return jsonify(
            {
                "present": True,
                "connected": ssid is not None,
                "ssid": ssid,
                "ip_address": _get_ip_address(),
                "signal": _get_signal_percent() if ssid else None,
                "interface": _IFACE,
            }
        )

    @app.route("/api/wifi/scan", methods=["GET"])
    def scan_wifi():
        """
        Scan for visible WiFi networks on wifi1.

        Response JSON:
          networks – list of:
            ssid     – str
            signal   – int (0-100)
            security – str ("Open", "WPA", "WPA2")
            secured  – bool
            connected – bool  (True if currently associated to this SSID)
        """
        if not _iface_exists():
            return (
                jsonify(
                    {
                        "error": (
                            f"Interface {_IFACE} not present. "
                            "Is the USB Wi-Fi adapter plugged in?"
                        )
                    }
                ),
                503,
            )

        current_ssid = _get_current_ssid()
        networks = _scan_networks()

        # Annotate which network is currently connected
        for net in networks:
            net["connected"] = net["ssid"] == current_ssid

        return jsonify({"networks": networks})

    @app.route("/api/wifi/mode", methods=["POST"])
    def set_wifi_mode():
        """
        Add or replace a WiFi network and reconnect.

        If a network with the same SSID already exists in the saved list it
        is updated in place (e.g. password changed). Otherwise the new
        network is appended with the next available priority value.

        Request JSON:
          ssid     – str (required)
          password – str (optional; omit or "" for open networks)

        Response JSON:
          success  – bool
          message  – str
        """
        data: Any = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        ssid = (data.get("ssid") or "").strip()
        if not ssid:
            return jsonify({"error": "ssid is required"}), 400

        password = (data.get("password") or "").strip()

        # Build updated network list: update existing entry or append new one.
        networks: list[dict[str, Any]] = list(webui.presets.wifi_networks)
        existing = next((n for n in networks if n.get("ssid") == ssid), None)

        if existing is not None:
            existing["psk"] = password
            logger.info("Updated credentials for WiFi network '%s'", ssid)
        else:
            # Assign a priority one above the current maximum so newer
            # entries are preferred.
            max_priority = max(
                (int(n.get("priority", 0)) for n in networks), default=-1
            )
            networks.append(
                {
                    "ssid": ssid,
                    "psk": password,
                    "priority": max_priority + 1,
                }
            )
            logger.info("Added WiFi network '%s'", ssid)

        # Write config and restart service.
        ok, err = _write_wpa_conf(networks)
        if not ok:
            return jsonify({"success": False, "message": err}), 500

        ok, err = _restart_wpa_supplicant()
        if not ok:
            return jsonify({"success": False, "message": err}), 500

        # Persist to settings only after the system call succeeded.
        webui.presets.wifi_networks = networks
        try:
            webui.presets.save()
            logger.info("WiFi network list saved to settings")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to save wifi networks to settings: %s", exc)
            # Not fatal – the network is active even if persistence failed.

        return jsonify(
            {"success": True, "message": f"Connecting to '{ssid}'..."}
        )

    @app.route("/api/wifi/forget", methods=["POST"])
    def forget_wifi_network():
        """
        Remove a saved WiFi network by SSID.

        If wifi1 is currently connected to that network, wpa_supplicant is
        restarted (which will disconnect; if other saved networks exist it
        will try them in priority order).

        Request JSON:
          ssid – str (required)

        Response JSON:
          success – bool
          message – str
        """
        data: Any = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        ssid = (data.get("ssid") or "").strip()
        if not ssid:
            return jsonify({"error": "ssid is required"}), 400

        networks: list[dict[str, Any]] = list(webui.presets.wifi_networks)
        before = len(networks)
        networks = [n for n in networks if n.get("ssid") != ssid]

        if len(networks) == before:
            # Do not reveal whether a particular SSID exists in the saved
            # list — return a generic 404 without echoing the ssid.
            return (
                jsonify({"success": False, "message": "Network not found."}),
                404,
            )

        logger.info("Forgot WiFi network '%s'", ssid)

        # Re-write config (and restart) only if the interface exists.
        # If the adapter is unplugged we still want to remove it from the
        # persisted list so it won't be tried next time.
        if _iface_exists():
            ok, err = _write_wpa_conf(networks)
            if not ok:
                return jsonify({"success": False, "message": err}), 500

            ok, err = _restart_wpa_supplicant()
            if not ok:
                return jsonify({"success": False, "message": err}), 500

        webui.presets.wifi_networks = networks
        try:
            webui.presets.save()
            logger.info("WiFi network list saved to settings after forget")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to save wifi networks to settings: %s", exc)

        return jsonify({"success": True, "message": "Network removed."})
