"""DHCP event routes for camera detection notifications."""

from __future__ import (
    annotations,
)

import logging
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


def register_dhcp_routes(app: "Flask", webui: "WebUI") -> None:
    """Register DHCP event endpoints for camera detection."""

    @app.route("/api/dhcp/event", methods=["POST"])
    def dhcp_event():
        """
        Receive DHCP event notifications from dnsmasq script.

        Expected JSON payload:
        {
            "action": "add|old|del",
            "mac_address": "xx:xx:xx:xx:xx:xx",
            "ip_address": "192.168.52.xxx",
            "hostname": "device-hostname",
            "timestamp": "ISO8601 timestamp"
        }
        """
        try:
            data = request.get_json()

            if not data:
                return jsonify({"error": "No JSON data provided"}), 400

            action = data.get("action")
            mac_address = data.get("mac_address")
            ip_address = data.get("ip_address")
            hostname = data.get("hostname")
            timestamp = data.get("timestamp")

            # Log the DHCP event (MAC address redacted)
            logger.info(
                "DHCP event received: action=%s, hostname=%s, "
                "mac=%s, ip=%s, timestamp=%s",
                action,
                hostname,
                "***",
                ip_address,
                timestamp,
            )

            # Store camera information in webui.cameras dictionary
            if action in ["add", "old"]:
                # Camera connected or renewed lease
                logger.info(
                    "Camera '%s' connected at IP %s", hostname, ip_address
                )
                # Store camera info indexed by MAC address
                webui.cameras[mac_address] = {
                    "hostname": hostname,
                    "ip_address": ip_address,
                    "mac_address": mac_address,
                    "last_seen": timestamp,
                    "status": "connected",
                }

                # Update settings with camera list
                # Convert cameras dict to list for settings persistence
                camera_list = []
                for _, cam_info in webui.cameras.items():
                    camera_list.append(
                        {
                            "hostname": cam_info["hostname"],
                            "ip_address": cam_info["ip_address"],
                            "mac_address": cam_info["mac_address"],
                            "last_seen": cam_info["last_seen"],
                            "status": cam_info["status"],
                        }
                    )

                webui.presets.cameras = camera_list

                # Persist to settings file
                try:
                    webui.presets.save()
                    logger.info("Camera list saved to settings")
                except Exception as e:  # pylint: disable=broad-except
                    logger.error(
                        "Failed to save camera list to settings: %s", str(e)
                    )

            elif action == "del":
                # Camera disconnected
                logger.info("Camera '%s' disconnected", hostname)
                # Update camera status to disconnected (keep history)
                if mac_address in webui.cameras:
                    webui.cameras[mac_address]["status"] = "disconnected"
                    webui.cameras[mac_address]["last_seen"] = timestamp

                    # Update settings with updated camera list
                    camera_list = []
                    for _, cam_info in webui.cameras.items():
                        camera_list.append(
                            {
                                "hostname": cam_info["hostname"],
                                "ip_address": cam_info["ip_address"],
                                "mac_address": cam_info["mac_address"],
                                "last_seen": cam_info["last_seen"],
                                "status": cam_info["status"],
                            }
                        )

                    webui.presets.cameras = camera_list

                    # Persist to settings file
                    try:
                        webui.presets.save()
                        logger.info("Camera list updated in settings")
                    except Exception as e:  # pylint: disable=broad-except
                        logger.error(
                            "Failed to save camera list to settings: %s",
                            str(e),
                        )

            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "DHCP event processed",
                        "data": {
                            "action": action,
                            "hostname": hostname,
                            "ip_address": ip_address,
                        },
                    }
                ),
                200,
            )

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error processing DHCP event: %s", str(e))
            return (
                jsonify(
                    {
                        "error": "Failed to process DHCP event",
                    }
                ),
                500,
            )

    @app.route("/api/dhcp/cameras", methods=["GET"])
    def get_cameras():
        """
        Get list of known cameras.

        Returns all detected cameras with their connection status.
        """
        cameras_list = list(webui.cameras.values())

        return (
            jsonify(
                {
                    "cameras": cameras_list,
                    "count": len(cameras_list),
                }
            ),
            200,
        )

    @app.route("/api/dhcp/cameras/<mac_address>", methods=["GET"])
    def get_camera(mac_address: str):
        """
        Get specific camera by MAC address.

        Args:
            mac_address: MAC address of the camera (e.g., aa:bb:cc:dd:ee:ff)
        """
        # Normalize MAC address format (lowercase, colons)
        mac_address = mac_address.lower()

        if mac_address in webui.cameras:
            return jsonify(webui.cameras[mac_address]), 200
        return (
            jsonify(
                {
                    "error": "Camera not found",
                    "mac_address": mac_address,
                }
            ),
            404,
        )

    @app.route("/api/dhcp/cameras", methods=["POST"])
    def add_camera():
        """
        Manually add a camera (for testing purposes).

        Expected JSON payload:
        {
            "hostname": "camera-name",
            "ip_address": "192.168.52.100",
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "status": "connected"  // optional, defaults to "connected"
        }
        """
        try:
            data = request.get_json()

            if not data:
                return jsonify({"error": "No JSON data provided"}), 400

            hostname = data.get("hostname")
            ip_address = data.get("ip_address")
            mac_address = data.get("mac_address")
            status = data.get("status", "connected")

            # Validate required fields
            if not hostname or not ip_address or not mac_address:
                return (
                    jsonify(
                        {
                            "error": "Missing required fields: hostname, "
                            "ip_address, mac_address"
                        }
                    ),
                    400,
                )

            # Generate timestamp
            timestamp = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            # Add camera to webui.cameras
            webui.cameras[mac_address] = {
                "hostname": hostname,
                "ip_address": ip_address,
                "mac_address": mac_address,
                "last_seen": timestamp,
                "status": status,
            }

            # Update settings with camera list
            camera_list = []
            for _, cam_info in webui.cameras.items():
                camera_list.append(
                    {
                        "hostname": cam_info["hostname"],
                        "ip_address": cam_info["ip_address"],
                        "mac_address": cam_info["mac_address"],
                        "last_seen": cam_info["last_seen"],
                        "status": cam_info["status"],
                    }
                )

            webui.presets.cameras = camera_list

            # Persist to settings file
            try:
                webui.presets.save()
                logger.info(
                    "Manually added camera '%s' at %s", hostname, ip_address
                )
            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    "Failed to save camera list to settings: %s", str(e)
                )

            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Camera added successfully",
                        "camera": webui.cameras[mac_address],
                    }
                ),
                201,
            )

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error adding camera: %s", str(e))
            return (
                jsonify(
                    {
                        "error": "Failed to add camera",
                    }
                ),
                500,
            )

    @app.route("/api/dhcp/cameras", methods=["DELETE"])
    def clear_cameras():
        """
        Clear all camera records.

        This removes all stored camera information from memory.
        """
        count = len(webui.cameras)
        webui.cameras.clear()
        logger.info("Cleared %d camera records", count)

        # Update settings
        webui.presets.cameras = []
        try:
            webui.presets.save()
            logger.info("Camera list cleared from settings")
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to save camera list to settings: %s", str(e))

        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Cleared {count} camera record(s)",
                }
            ),
            200,
        )

    @app.route("/api/dhcp/cameras/heartbeat", methods=["POST"])
    def check_heartbeat():
        """
        Manually trigger a heartbeat check for all cameras.

        This immediately checks all cameras and returns their
        reachability status.

        Returns:
            JSON with camera reachability results
        """
        try:
            results = webui.heartbeat.check_now()

            # Convert results to human-readable format
            camera_status = {}
            for mac_address, is_reachable in results.items():
                camera = webui.cameras.get(mac_address)
                if camera:
                    camera_status[mac_address] = {
                        "hostname": camera["hostname"],
                        "ip_address": camera["ip_address"],
                        "reachable": is_reachable,
                        "status": camera["status"],
                        "last_seen": camera["last_seen"],
                    }

            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Heartbeat check completed",
                        "cameras": camera_status,
                    }
                ),
                200,
            )

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error performing heartbeat check: %s", str(e))
            return (
                jsonify(
                    {
                        "error": "Failed to perform heartbeat check",
                    }
                ),
                500,
            )
