"""
WiFi management routes for scanning networks and configuring WiFi mode.

Uses wpa_cli/wpa_supplicant for WiFi management instead of NetworkManager.
Requires wpa_supplicant to be available on the system.
"""

from __future__ import (
    annotations,
)

import logging
import os
import subprocess
import time
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


def detect_wireless_interface() -> str | None:
    """
    Detect the first available wireless network interface.

    Checks /sys/class/net for interfaces with wireless extensions.

    Returns:
        str: The name of the first wireless interface found (e.g., 'wlan0'),
             or None if no wireless interface is detected.
    """
    try:
        # Check /sys/class/net for network interfaces
        net_dir = "/sys/class/net"
        logger.debug("Checking for wireless interfaces in %s", net_dir)
        if not os.path.exists(net_dir):
            logger.warning(
                "Network interface directory not found: %s", net_dir
            )
            return None

        interfaces = os.listdir(net_dir)
        logger.debug("Found network interfaces: %s", ", ".join(interfaces))
        wireless_interfaces = []

        for interface in interfaces:
            # Skip loopback and virtual interfaces
            if interface.startswith(("lo", "docker", "veth", "br-")):
                logger.debug("Skipping virtual interface: %s", interface)
                continue

            # Check if wireless directory exists (indicates wireless
            # capability)
            wireless_dir = os.path.join(net_dir, interface, "wireless")
            logger.debug(
                "Checking if %s is wireless: %s", interface, wireless_dir
            )
            if os.path.exists(wireless_dir):
                wireless_interfaces.append(interface)
                logger.info("Found wireless interface: %s", interface)
            else:
                logger.debug("%s is not a wireless interface", interface)

        if not wireless_interfaces:
            logger.warning("No wireless interfaces detected")
            return None

        if len(wireless_interfaces) > 1:
            logger.info(
                "Multiple wireless interfaces found: %s. Using first: %s",
                ", ".join(wireless_interfaces),
                wireless_interfaces[0],
            )

        return wireless_interfaces[0]

    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Error detecting wireless interface")
        return None


class NetworkInfo(TypedDict):
    """Type definition for WiFi network information."""

    ssid: str
    signal: int
    security: str
    secured: bool
    connected: bool


def detect_wifi_management_tool() -> str:
    """
    Detect which WiFi management tool is available.

    Returns:
        str: 'nmcli' if NetworkManager is available,
             'wpa_cli' if wpa_supplicant is available,
             or 'none' if neither is available.
    """
    logger.debug("Detecting WiFi management tool...")

    # Check for nmcli (NetworkManager)
    logger.debug("Checking for nmcli (NetworkManager)...")
    try:
        result = subprocess.run(
            ["nmcli", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info("Detected NetworkManager (nmcli) for WiFi management")
            logger.debug("nmcli version: %s", result.stdout.strip())
            return "nmcli"
        else:
            logger.debug(
                "nmcli not available (exit code %d)", result.returncode
            )
    except FileNotFoundError:
        logger.debug("nmcli not found in PATH")
    except subprocess.TimeoutExpired:
        logger.debug("nmcli version check timed out")

    # Check for wpa_cli (wpa_supplicant)
    logger.debug("Checking for wpa_cli (wpa_supplicant)...")
    try:
        result = subprocess.run(
            ["wpa_cli", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info(
                "Detected wpa_supplicant (wpa_cli) for WiFi management"
            )
            logger.debug("wpa_cli version: %s", result.stdout.strip())
            return "wpa_cli"
        else:
            logger.debug(
                "wpa_cli not available (exit code %d)", result.returncode
            )
    except FileNotFoundError:
        logger.debug("wpa_cli not found in PATH")
    except subprocess.TimeoutExpired:
        logger.debug("wpa_cli version check timed out")

    logger.warning("No WiFi management tool detected (nmcli or wpa_cli)")
    return "none"


def register_wifi_routes(app: "Flask", webui: "WebUI") -> None:
    """
    Register WiFi management endpoints.

    Args:
        app: Flask application instance
        webui: WebUI instance (unused but required for consistency)
    """
    # Detect wireless interface at startup
    wireless_interface = detect_wireless_interface()
    if wireless_interface:
        logger.info("Using wireless interface: %s", wireless_interface)
    else:
        logger.warning(
            "No wireless interface detected. WiFi functionality will not be "
            + "available. Falling back to 'wlan0' for compatibility."
        )
        wireless_interface = (
            "wlan0"  # Fallback for systems where detection fails
        )

    # Detect WiFi management tool
    wifi_tool = detect_wifi_management_tool()

    @app.route("/api/wifi/scan", methods=["GET"])
    def scan_wifi_networks():
        """
        Scan for available WiFi networks.

        Uses NetworkManager (nmcli) if available, otherwise falls back
        to wpa_supplicant (wpa_cli).

        Returns:
            JSON with list of networks containing SSID, signal strength,
            security type, etc.
        """
        try:
            networks: list[NetworkInfo] = []
            seen_ssids: set[str] = set()
            current_ssid = None

            if wifi_tool == "nmcli":
                # Use NetworkManager to scan
                logger.debug(
                    "Using NetworkManager (nmcli) to scan for WiFi networks"
                )

                # First, trigger a rescan
                logger.debug("Triggering WiFi rescan with nmcli...")
                rescan_result = subprocess.run(
                    ["nmcli", "device", "wifi", "rescan"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                logger.debug(
                    "Rescan result: exit code %d", rescan_result.returncode
                )
                if rescan_result.stderr:
                    logger.debug(
                        "Rescan stderr: %s", rescan_result.stderr.strip()
                    )

                # Wait a bit for scan to complete
                logger.debug("Waiting 2 seconds for scan to complete...")
                time.sleep(2)

                # Get scan results
                logger.debug("Retrieving WiFi scan results from nmcli...")
                result = subprocess.run(
                    [
                        "nmcli",
                        "-t",
                        "-f",
                        "SSID,SIGNAL,SECURITY,ACTIVE",
                        "device",
                        "wifi",
                        "list",
                        "--rescan",
                        "no",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                logger.debug(
                    "Got %d bytes of scan results", len(result.stdout)
                )

                # Parse nmcli output
                # Format: SSID:SIGNAL:SECURITY:ACTIVE
                line_count = 0
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue

                    line_count += 1
                    parts = line.split(":")
                    if len(parts) < 4:
                        logger.debug("Skipping malformed line: %s", line)
                        continue

                    ssid = parts[0].strip()
                    signal_str = parts[1].strip()
                    security_flags = parts[2].strip()
                    active = parts[3].strip() == "yes"

                    logger.debug(
                        "Parsing network: SSID='%s', Signal=%s, "
                        "Security='%s', Active=%s",
                        ssid,
                        signal_str,
                        security_flags,
                        active,
                    )

                    # Skip empty SSIDs and duplicates
                    if not ssid:
                        logger.debug("Skipping empty SSID")
                        continue
                    if ssid in seen_ssids:
                        logger.debug("Skipping duplicate SSID: %s", ssid)
                        continue

                    seen_ssids.add(ssid)

                    # Parse signal strength
                    try:
                        signal_int = int(signal_str)
                    except ValueError:
                        signal_int = 0

                    # Determine security type
                    security = "Open"
                    secured = False
                    if security_flags:
                        if "WPA2" in security_flags:
                            security = "WPA2"
                            secured = True
                        elif "WPA" in security_flags:
                            security = "WPA"
                            secured = True
                        elif "WEP" in security_flags:
                            security = "WEP"
                            secured = True

                    if active:
                        current_ssid = ssid

                    networks.append(
                        {
                            "ssid": ssid,
                            "signal": signal_int,
                            "security": security,
                            "secured": secured,
                            "connected": active,
                        }
                    )

                logger.debug(
                    "Parsed %d networks from nmcli output", line_count
                )

            elif wifi_tool == "wpa_cli":
                # Use wpa_cli to scan for networks
                logger.debug(
                    "Using wpa_cli to scan for WiFi networks on interface %s",
                    wireless_interface,
                )

                # First, trigger a scan
                logger.debug("Triggering WiFi scan with wpa_cli...")
                scan_trigger = subprocess.run(
                    ["wpa_cli", "-i", wireless_interface, "scan"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                logger.debug(
                    "Scan trigger result: %s (exit code %d)",
                    scan_trigger.stdout.strip(),
                    scan_trigger.returncode,
                )

                # Check if scan was accepted
                if scan_trigger.stdout.strip() != "OK":
                    logger.warning(
                        "Scan trigger returned: %s",
                        scan_trigger.stdout.strip(),
                    )

                # Wait for scan to complete
                logger.debug(
                    "Waiting for scan to complete (max 20 attempts)..."
                )
                max_attempts = 20  # 20 attempts * 0.3s = 6s max wait
                scan_complete = False
                previous_count = 0

                for attempt in range(max_attempts):
                    time.sleep(0.3)
                    check_result = subprocess.run(
                        [
                            "wpa_cli",
                            "-i",
                            wireless_interface,
                            "scan_results",
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    lines = check_result.stdout.strip().split("\n")
                    current_count = len(lines) - 1

                    logger.debug(
                        "Attempt %d: Found %d networks",
                        attempt + 1,
                        current_count,
                    )

                    if current_count > 0 and attempt > 2:
                        if current_count == previous_count:
                            scan_complete = True
                            logger.debug(
                                "Scan completed with %d networks after "
                                "%d attempts",
                                current_count,
                                attempt + 1,
                            )
                            break
                    previous_count = current_count

                if not scan_complete:
                    logger.warning(
                        "Scan may not have completed within timeout, "
                        "proceeding anyway"
                    )

                # Get the scan results
                logger.debug("Retrieving final scan results from wpa_cli...")
                result = subprocess.run(
                    ["wpa_cli", "-i", wireless_interface, "scan_results"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                logger.debug(
                    "Got %d bytes of scan results", len(result.stdout)
                )

                # Get current connected network
                try:
                    status_result = subprocess.run(
                        ["wpa_cli", "-i", wireless_interface, "status"],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    for line in status_result.stdout.split("\n"):
                        if line.startswith("ssid="):
                            current_ssid = line.split("=", 1)[1].strip()
                            break
                except Exception:  # pylint: disable=broad-except
                    pass

                # Parse wpa_cli scan results
                # Format: bssid / frequency / signal level / flags / ssid
                lines = result.stdout.strip().split("\n")
                logger.debug(
                    "Parsing %d lines of wpa_cli scan results", len(lines)
                )
                for i, line in enumerate(lines):
                    if i == 0:
                        logger.debug("Skipping header line")
                        continue
                    if not line:
                        continue

                    parts = line.split("\t")
                    if len(parts) < 5:
                        logger.debug("Skipping malformed line: %s", line)
                        continue

                    signal_str = parts[2].strip()
                    flags = parts[3].strip()
                    ssid = parts[4].strip()

                    logger.debug(
                        "Parsing network: SSID='%s', Signal=%s dBm, "
                        "Flags='%s'",
                        ssid,
                        signal_str,
                        flags,
                    )

                    if not ssid:
                        logger.debug("Skipping empty SSID")
                        continue
                    if ssid in seen_ssids:
                        logger.debug("Skipping duplicate SSID: %s", ssid)
                        continue

                    seen_ssids.add(ssid)

                    # Convert signal from dBm to percentage
                    try:
                        signal_dbm = int(signal_str)
                        signal_int = max(0, min(100, 2 * (signal_dbm + 100)))
                    except ValueError:
                        signal_int = 0

                    # Determine security type
                    security = "Open"
                    secured = False
                    if "WPA2" in flags or "WPA-PSK" in flags:
                        security = "WPA2"
                        secured = True
                    elif "WPA" in flags:
                        security = "WPA"
                        secured = True
                    elif "WEP" in flags:
                        security = "WEP"
                        secured = True

                    networks.append(
                        {
                            "ssid": ssid,
                            "signal": signal_int,
                            "security": security,
                            "secured": secured,
                            "connected": ssid == current_ssid,
                        }
                    )

            else:
                return (
                    jsonify(
                        {
                            "error": (
                                "No WiFi management tool available "
                                "(nmcli or wpa_cli required)"
                            )
                        }
                    ),
                    500,
                )

            # Sort by signal strength (strongest first)
            networks.sort(key=lambda x: x["signal"], reverse=True)

            logger.info(
                "WiFi scan completed successfully: found %d networks",
                len(networks),
            )
            for i, net in enumerate(networks[:5]):  # Log top 5 networks
                logger.debug(
                    "Network %d: %s (signal: %d%%, security: %s, "
                    "connected: %s)",
                    i + 1,
                    net["ssid"],
                    net["signal"],
                    net["security"],
                    net["connected"],
                )
            if len(networks) > 5:
                logger.debug("... and %d more networks", len(networks) - 5)

            return jsonify({"networks": networks})

        except subprocess.TimeoutExpired:
            logger.exception("WiFi scan timed out")
            return jsonify({"error": "WiFi scan timed out"}), 500
        except subprocess.CalledProcessError as e:
            logger.exception("Error scanning WiFi networks")
            error_msg = f"Failed to scan WiFi networks: {e.stderr}"
            return jsonify({"error": error_msg}), 500
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unexpected error scanning WiFi")
            return (
                jsonify({"error": "Failed to scan WiFi networks"}),
                500,
            )

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
            logger.debug(
                "Checking WiFi client mode status using %s", wifi_tool
            )

            connected_ssid = None
            connected = False

            if wifi_tool == "nmcli":
                # Use NetworkManager to check connection status
                logger.debug("Using nmcli to check connection status...")
                result = subprocess.run(
                    [
                        "nmcli",
                        "-t",
                        "-f",
                        "ACTIVE,SSID",
                        "connection",
                        "show",
                        "--active",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                # Parse nmcli output for active wireless connection
                # Format: yes:SSID_NAME or no:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    parts = line.split(":")
                    if len(parts) >= 2:
                        is_active = parts[0].strip() == "yes"
                        ssid = parts[1].strip() if len(parts) > 1 else ""
                        if is_active and ssid:
                            connected = True
                            connected_ssid = ssid
                            logger.debug(
                                "Found active connection: %s", connected_ssid
                            )
                            break

            elif wifi_tool == "wpa_cli":
                # Use wpa_cli to check connection status
                logger.debug("Using wpa_cli to check connection status...")
                result = subprocess.run(
                    ["wpa_cli", "-i", wireless_interface, "status"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                for line in result.stdout.strip().split("\n"):
                    if line.startswith("wpa_state="):
                        state = line.split("=", 1)[1].strip()
                        connected = state == "COMPLETED"
                        logger.debug("wpa_state: %s", state)
                    elif line.startswith("ssid="):
                        connected_ssid = line.split("=", 1)[1].strip()
                        logger.debug("Connected SSID: %s", connected_ssid)

            logger.info(
                "WiFi mode: client, connected: %s, SSID: %s",
                connected,
                connected_ssid or "(none)",
            )

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
    def set_wifi_mode():
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

        Note:
            This function currently requires wpa_supplicant for client mode.
            Systems using NetworkManager should use nmcli commands directly.
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

            # Warn if using NetworkManager (client mode won't work properly)
            if mode == "client" and wifi_tool == "nmcli":
                logger.warning(
                    "set_wifi_mode called with NetworkManager detected. "
                    "Client mode switching requires wpa_supplicant. "
                    "This may not work as expected."
                )

            logger.debug(
                "Setting WiFi mode to %s with SSID: %s, wifi_tool: %s",
                mode,
                ssid,
                wifi_tool,
            )

            # Switch to AP mode
            if mode == "ap":
                logger.info("Switching to AP mode with SSID: %s", ssid)

                # Stop wpa_supplicant
                _ = subprocess.run(
                    [
                        "systemctl",
                        "stop",
                        f"wpa_supplicant@{wireless_interface}",
                    ],
                    check=False,
                    timeout=10,
                )

                # Disconnect from any current network
                logger.debug("Disconnecting from current network...")
                disconnect_result = subprocess.run(
                    ["wpa_cli", "-i", wireless_interface, "disconnect"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if disconnect_result.returncode != 0:
                    logger.debug(
                        "wpa_cli disconnect failed (may not be running): %s",
                        disconnect_result.stderr,
                    )

                # Update hostapd configuration
                hostapd_config = f"""interface={wireless_interface}
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
                    # Derive a PSK from the SSID and password using
                    # wpa_passphrase
                    try:
                        psk_proc = subprocess.run(
                            ["wpa_passphrase", ssid, password],
                            check=True,
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                    except (
                        subprocess.CalledProcessError,
                        subprocess.TimeoutExpired,
                    ) as e:
                        logger.error("Failed to derive PSK for hostapd: %s", e)
                        return (
                            jsonify(
                                {
                                    "error": (
                                        "Failed to derive secure PSK for "
                                        "access point"
                                    ),
                                }
                            ),
                            500,
                        )

                    psk_value: str | None = None
                    for line in psk_proc.stdout.splitlines():
                        line = line.strip()
                        if line.startswith("psk=") and not line.startswith(
                            "#"
                        ):
                            # line format: psk=<hex>
                            psk_value = line.split("=", 1)[1].strip()
                            break

                    if not psk_value:
                        logger.error(
                            "wpa_passphrase did not produce a usable PSK "
                            "for SSID %s",
                            ssid,
                        )
                        return (
                            jsonify(
                                {
                                    "error": (
                                        "Failed to compute secure PSK for "
                                        "access point"
                                    ),
                                }
                            ),
                            500,
                        )

                    hostapd_config += f"""wpa=2
wpa_psk={psk_value}
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

            # Start wpa_supplicant if not running
            subprocess.run(
                ["systemctl", "start", f"wpa_supplicant@{wireless_interface}"],
                check=False,
                timeout=10,
            )

            # Wait for wpa_supplicant to initialize
            logger.debug("Waiting for wpa_supplicant to initialize...")
            time.sleep(2)

            # Remove any existing network configurations
            logger.debug("Removing existing network configurations...")
            list_result = subprocess.run(
                ["wpa_cli", "-i", wireless_interface, "list_networks"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in list_result.stdout.split("\n")[1:]:  # Skip header
                if line.strip():
                    parts = line.split("\t")
                    if parts:
                        network_id = parts[0].strip()
                        subprocess.run(
                            [
                                "wpa_cli",
                                "-i",
                                wireless_interface,
                                "remove_network",
                                network_id,
                            ],
                            check=False,
                            timeout=5,
                        )

            # Add new network
            add_result = subprocess.run(
                ["wpa_cli", "-i", wireless_interface, "add_network"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )

            network_id = add_result.stdout.strip().split("\n")[-1]

            # Set SSID
            subprocess.run(
                [
                    "wpa_cli",
                    "-i",
                    wireless_interface,
                    "set_network",
                    network_id,
                    "ssid",
                    f'"{ssid}"',
                ],
                check=True,
                timeout=5,
            )

            # Set security
            if password:
                subprocess.run(
                    [
                        "wpa_cli",
                        "-i",
                        wireless_interface,
                        "set_network",
                        network_id,
                        "psk",
                        f'"{password}"',
                    ],
                    check=True,
                    timeout=5,
                )
            else:
                subprocess.run(
                    [
                        "wpa_cli",
                        "-i",
                        wireless_interface,
                        "set_network",
                        network_id,
                        "key_mgmt",
                        "NONE",
                    ],
                    check=True,
                    timeout=5,
                )

            # Enable the network
            subprocess.run(
                [
                    "wpa_cli",
                    "-i",
                    wireless_interface,
                    "enable_network",
                    network_id,
                ],
                check=True,
                timeout=5,
            )

            # Select the network
            subprocess.run(
                [
                    "wpa_cli",
                    "-i",
                    wireless_interface,
                    "select_network",
                    network_id,
                ],
                check=True,
                timeout=5,
            )

            # Save configuration
            subprocess.run(
                ["wpa_cli", "-i", wireless_interface, "save_config"],
                check=False,
                timeout=5,
            )

            # Wait for connection
            time.sleep(5)

            # Verify connection
            status_result = subprocess.run(
                ["wpa_cli", "-i", wireless_interface, "status"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )

            connected = False
            for line in status_result.stdout.split("\n"):
                if line.startswith("wpa_state="):
                    state = line.split("=", 1)[1].strip()
                    connected = state == "COMPLETED"
                    break

            if not connected:
                raise ConnectionError("Failed to connect to network")

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
        """Forget a saved WiFi network.

        Request body:
            {
                "ssid": "network-name"
            }

        Returns:
            JSON with success status

        Note:
            This function currently requires wpa_supplicant.
            Systems using NetworkManager should use nmcli commands directly.
        """
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "No data provided"}), 400

            ssid = data.get("ssid")
            if not ssid:
                return jsonify({"error": "SSID is required"}), 400

            # Warn if using NetworkManager
            if wifi_tool == "nmcli":
                logger.warning(
                    "forget_wifi_network called with NetworkManager detected. "
                    "This operation requires wpa_supplicant. "
                    "This may not work as expected."
                )

            logger.info("Forgetting WiFi network: %s", ssid)
            logger.debug("Using wifi_tool: %s", wifi_tool)
            # Get list of networks and find matching SSID
            list_result = subprocess.run(
                ["wpa_cli", "-i", wireless_interface, "list_networks"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )

            network_id = None
            for line in list_result.stdout.split("\n")[1:]:  # Skip header
                if line.strip():
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        net_id = parts[0].strip()
                        net_ssid = parts[1].strip()
                        if net_ssid == ssid:
                            network_id = net_id
                            break

            if network_id is None:
                return jsonify({"error": f"Network '{ssid}' not found"}), 404

            # Remove the network
            subprocess.run(
                [
                    "wpa_cli",
                    "-i",
                    wireless_interface,
                    "remove_network",
                    network_id,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Save configuration
            subprocess.run(
                ["wpa_cli", "-i", wireless_interface, "save_config"],
                check=False,
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
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unexpected error forgetting WiFi network")
            return (
                jsonify(
                    {
                        "error": (
                            "An internal error occurred while "
                            "forgetting the WiFi network"
                        )
                    }
                ),
                500,
            )
