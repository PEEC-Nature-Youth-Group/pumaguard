"""WiFi management routes for scanning networks and configuring WiFi mode."""

from __future__ import (
    annotations,
)

import logging
import subprocess
from typing import (
    TYPE_CHECKING,
    TypedDict,
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


class NetworkInfo(TypedDict):
    """Type definition for WiFi network information."""

    ssid: str
    signal: int
    security: str
    secured: bool
    connected: bool


def register_wifi_routes(app: "Flask", webui: "WebUI") -> None:
    """Register WiFi management endpoints.

    Args:
        app: Flask application instance
        webui: WebUI instance (unused but required for consistency)
    """
    # pylint: disable=unused-argument

    @app.route("/api/wifi/scan", methods=["GET"])
    def scan_wifi_networks():
        """Scan for available WiFi networks.

        Returns:
            JSON with list of networks containing SSID, signal strength,
            security type, etc.
        """
        try:
            # Use nmcli to scan for networks
            # First, rescan to get fresh results
            subprocess.run(
                ["nmcli", "device", "wifi", "rescan"],
                check=False,
                capture_output=True,
                timeout=30,
            )

            # Get the list of networks
            result = subprocess.run(
                [
                    "nmcli",
                    "-t",
                    "-f",
                    "SSID,SIGNAL,SECURITY,IN-USE",
                    "device",
                    "wifi",
                    "list",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )

            networks: list[NetworkInfo] = []
            seen_ssids: set[str] = set()

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split(":")
                if len(parts) < 4:
                    continue

                ssid = parts[0].strip()
                signal = parts[1].strip()
                security = parts[2].strip()
                in_use = parts[3].strip()

                # Skip empty SSIDs and duplicates (keep strongest signal)
                if not ssid or ssid == "--":
                    continue

                if ssid in seen_ssids:
                    continue

                seen_ssids.add(ssid)

                try:
                    signal_int = int(signal) if signal else 0
                except ValueError:
                    signal_int = 0

                networks.append(
                    {
                        "ssid": ssid,
                        "signal": signal_int,
                        "security": security if security else "Open",
                        "secured": bool(security and security != "--"),
                        "connected": in_use == "*",
                    }
                )

            # Sort by signal strength (strongest first)
            networks.sort(key=lambda x: x["signal"], reverse=True)

            return jsonify({"networks": networks})

        except subprocess.TimeoutExpired:
            logger.exception("WiFi scan timed out")
            return jsonify({"error": "WiFi scan timed out"}), 500
        except subprocess.CalledProcessError as e:
            logger.exception("Error scanning WiFi networks")
            error_msg = f"Failed to scan WiFi networks: {e.stderr}"
            return jsonify({"error": error_msg}), 500
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Unexpected error scanning WiFi")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/wifi/mode", methods=["GET"])
    def get_wifi_mode():
        """Get current WiFi mode (ap or client).

        Returns:
            JSON with mode, current SSID if in client mode,
            and connection status
        """
        try:
            # Check if hostapd is running (AP mode)
            hostapd_result = subprocess.run(
                ["systemctl", "is-active", "hostapd"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if hostapd_result.stdout.strip() == "active":
                # AP mode is active
                # Get the SSID from hostapd config
                try:
                    with open(
                        "/etc/hostapd/hostapd.conf", "r", encoding="utf-8"
                    ) as f:
                        config = f.read()
                        ssid = None
                        for line in config.split("\n"):
                            if line.startswith("ssid="):
                                ssid = line.split("=", 1)[1].strip()
                                break

                    return jsonify(
                        {
                            "mode": "ap",
                            "ssid": ssid or "pumaguard",
                            "connected": True,
                        }
                    )
                except Exception as e:  # pylint: disable=broad-except
                    logger.warning("Could not read hostapd config: %s", e)
                    return jsonify(
                        {
                            "mode": "ap",
                            "ssid": "pumaguard",
                            "connected": True,
                        }
                    )

            # Check if connected to a WiFi network (client mode)
            result = subprocess.run(
                [
                    "nmcli",
                    "-t",
                    "-f",
                    "TYPE,DEVICE,STATE,CONNECTION",
                    "connection",
                    "show",
                    "--active",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )

            connected_ssid = None
            connected = False

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split(":")
                if len(parts) >= 4:
                    conn_type = parts[0].strip()
                    device = parts[1].strip()
                    state = parts[2].strip()
                    connection = parts[3].strip()

                    if (
                        conn_type == "802-11-wireless"
                        and device == "wlan0"
                        and state == "activated"
                    ):
                        connected_ssid = connection
                        connected = True
                        break

            return jsonify(
                {
                    "mode": "client",
                    "ssid": connected_ssid,
                    "connected": connected,
                }
            )

        except subprocess.TimeoutExpired:
            logger.exception("WiFi mode check timed out")
            return jsonify({"error": "WiFi mode check timed out"}), 500
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error getting WiFi mode")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/wifi/mode", methods=["PUT"])
    def set_wifi_mode():  # pylint: disable=too-many-return-statements
        """Set WiFi mode to AP or client.

        Request body:
            {
                "mode": "ap" or "client",
                "ssid": "network-name" (required for both modes),
                "password": "network-password"
                (optional for client, required for AP)
            }

        Returns:
            JSON with success status and message
        """
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "No data provided"}), 400

            mode = data.get("mode")
            ssid = data.get("ssid")
            password = data.get("password", "")

            if mode not in ["ap", "client"]:
                return (
                    jsonify({"error": "Mode must be 'ap' or 'client'"}),
                    400,
                )

            if not ssid:
                return jsonify({"error": "SSID is required"}), 400

            # Switch to AP mode
            if mode == "ap":
                logger.info("Switching to AP mode with SSID: %s", ssid)

                # Stop NetworkManager from managing wlan0
                subprocess.run(
                    ["nmcli", "device", "set", "wlan0", "managed", "no"],
                    check=True,
                    timeout=10,
                )

                # Update hostapd configuration
                hostapd_config = f"""interface=wlan0
driver=nl80211
ssid={ssid}
hw_mode=g
channel=7
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""

                if password:
                    # WPA2 secured AP
                    hostapd_config += f"""wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""

                with open(
                    "/etc/hostapd/hostapd.conf", "w", encoding="utf-8"
                ) as f:
                    f.write(hostapd_config)

                # Restart hostapd
                subprocess.run(
                    ["systemctl", "restart", "hostapd"],
                    check=True,
                    timeout=15,
                )

                # Restart dnsmasq for DHCP
                subprocess.run(
                    ["systemctl", "restart", "dnsmasq"],
                    check=True,
                    timeout=15,
                )

                logger.info("Successfully switched to AP mode")
                return jsonify(
                    {
                        "success": True,
                        "message": f"AP mode enabled with SSID: {ssid}",
                    }
                )

            # Switch to client mode
            logger.info("Switching to client mode, connecting to: %s", ssid)

            # Stop hostapd and dnsmasq
            subprocess.run(
                ["systemctl", "stop", "hostapd"],
                check=False,
                timeout=10,
            )
            subprocess.run(
                ["systemctl", "stop", "dnsmasq"],
                check=False,
                timeout=10,
            )

            # Let NetworkManager manage wlan0
            subprocess.run(
                ["nmcli", "device", "set", "wlan0", "managed", "yes"],
                check=True,
                timeout=10,
            )

            # Delete existing connection if it exists
            subprocess.run(
                ["nmcli", "connection", "delete", ssid],
                check=False,
                capture_output=True,
                timeout=5,
            )

            # Create new WiFi connection
            if password:
                cmd = [
                    "nmcli",
                    "device",
                    "wifi",
                    "connect",
                    ssid,
                    "password",
                    password,
                ]
            else:
                cmd = ["nmcli", "device", "wifi", "connect", ssid]

            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            logger.info("Successfully connected to WiFi network: %s", ssid)
            return jsonify(
                {
                    "success": True,
                    "message": f"Connected to WiFi network: {ssid}",
                }
            )

        except subprocess.TimeoutExpired:
            logger.exception("WiFi mode change timed out")
            return jsonify({"error": "WiFi mode change timed out"}), 500
        except subprocess.CalledProcessError as e:
            logger.exception("Error changing WiFi mode")
            error_msg = e.stderr if e.stderr else str(e)
            return (
                jsonify({"error": f"Failed to change WiFi mode: {error_msg}"}),
                500,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Unexpected error changing WiFi mode")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/wifi/forget", methods=["POST"])
    def forget_wifi_network():
        """Forget/delete a saved WiFi connection.

        Request body:
            {
                "ssid": "network-name"
            }

        Returns:
            JSON with success status
        """
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "No data provided"}), 400

            ssid = data.get("ssid")
            if not ssid:
                return jsonify({"error": "SSID is required"}), 400

            # Delete the connection
            subprocess.run(
                ["nmcli", "connection", "delete", ssid],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )

            logger.info("Forgot WiFi network: %s", ssid)
            return jsonify(
                {
                    "success": True,
                    "message": f"Forgot network: {ssid}",
                }
            )

        except subprocess.CalledProcessError as e:
            logger.exception("Error forgetting WiFi network")
            return (
                jsonify({"error": (f"Failed to forget network: {e.stderr}")}),
                500,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Unexpected error forgetting WiFi network")
            return jsonify({"error": str(e)}), 500
