"""DHCP event routes for camera detection notifications."""

from __future__ import (
    annotations,
)

import json
import logging
import queue
import threading
from collections.abc import (
    Callable,
)
from datetime import (
    datetime,
    timezone,
)
from typing import (
    TYPE_CHECKING,
)

from flask import (
    Response,
    jsonify,
    request,
    stream_with_context,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


def register_dhcp_routes(
    app: "Flask", webui: "WebUI"
) -> Callable[[str, dict], None]:
    """
    Register DHCP event endpoints for camera detection.

    Returns:
        Callback function to notify SSE clients of camera changes
    """

    # Queue for SSE notifications
    sse_clients: list[queue.Queue] = []
    sse_clients_lock = threading.Lock()

    def notify_camera_change(event_type: str, camera_data: dict) -> None:
        """Notify all SSE clients about a camera status change."""
        message = {
            "type": event_type,
            "data": camera_data,
            "timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }

        with sse_clients_lock:
            disconnected_clients = []
            for client_queue in sse_clients:
                try:
                    # Non-blocking put with timeout
                    client_queue.put(message, block=False)
                except queue.Full:
                    # Client queue is full, mark for removal
                    disconnected_clients.append(client_queue)

            # Remove disconnected clients
            for client_queue in disconnected_clients:
                sse_clients.remove(client_queue)
                logger.debug("Removed disconnected SSE client")

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

            # Determine device type based on hostname pattern
            is_camera = hostname and hostname.startswith("Microseven")
            is_plug = hostname and hostname.lower().startswith("shellyplug")

            if is_camera:
                # Handle camera events
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

                    # Notify SSE clients
                    notify_camera_change(
                        "camera_connected", dict(webui.cameras[mac_address])
                    )

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
                        logger.info("Camera list saved to settings")
                    except Exception as e:  # pylint: disable=broad-except
                        logger.error(
                            "Failed to save camera list to settings: %s",
                            str(e),
                        )

                elif action == "del":
                    # Camera disconnected
                    logger.info("Camera '%s' disconnected", hostname)
                    # Update camera status to disconnected (keep history)
                    if mac_address in webui.cameras:
                        webui.cameras[mac_address]["status"] = "disconnected"
                        webui.cameras[mac_address]["last_seen"] = timestamp

                        # Notify SSE clients
                        notify_camera_change(
                            "camera_disconnected",
                            dict(webui.cameras[mac_address]),
                        )

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

            elif is_plug:
                # Handle plug events
                if action in ["add", "old"]:
                    # Plug connected or renewed lease
                    logger.info(
                        "Plug '%s' connected at IP %s", hostname, ip_address
                    )
                    # Store plug info indexed by MAC address
                    webui.plugs[mac_address] = {
                        "hostname": hostname,
                        "ip_address": ip_address,
                        "mac_address": mac_address,
                        "last_seen": timestamp,
                        "status": "connected",
                    }

                    # Notify SSE clients
                    notify_camera_change(
                        "plug_connected", dict(webui.plugs[mac_address])
                    )

                    # Update settings with plug list
                    plug_list = []
                    for _, plug_info in webui.plugs.items():
                        plug_list.append(
                            {
                                "hostname": plug_info["hostname"],
                                "ip_address": plug_info["ip_address"],
                                "mac_address": plug_info["mac_address"],
                                "last_seen": plug_info["last_seen"],
                                "status": plug_info["status"],
                            }
                        )

                    webui.presets.plugs = plug_list

                    # Persist to settings file
                    try:
                        webui.presets.save()
                        logger.info("Plug list saved to settings")
                    except Exception as e:  # pylint: disable=broad-except
                        logger.error(
                            "Failed to save plug list to settings: %s", str(e)
                        )

                elif action == "del":
                    # Plug disconnected
                    logger.info("Plug '%s' disconnected", hostname)
                    # Update plug status to disconnected (keep history)
                    if mac_address in webui.plugs:
                        webui.plugs[mac_address]["status"] = "disconnected"
                        webui.plugs[mac_address]["last_seen"] = timestamp

                        # Notify SSE clients
                        notify_camera_change(
                            "plug_disconnected", dict(webui.plugs[mac_address])
                        )

                        # Update settings with updated plug list
                        plug_list = []
                        for _, plug_info in webui.plugs.items():
                            plug_list.append(
                                {
                                    "hostname": plug_info["hostname"],
                                    "ip_address": plug_info["ip_address"],
                                    "mac_address": plug_info["mac_address"],
                                    "last_seen": plug_info["last_seen"],
                                    "status": plug_info["status"],
                                }
                            )

                        webui.presets.plugs = plug_list

                        # Persist to settings file
                        try:
                            webui.presets.save()
                            logger.info("Plug list updated in settings")
                        except Exception as e:  # pylint: disable=broad-except
                            logger.error(
                                "Failed to save plug list to settings: %s",
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
                            "device_type": (
                                "camera"
                                if is_camera
                                else "plug" if is_plug else "unknown"
                            ),
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

            # Notify SSE clients
            notify_camera_change(
                "camera_added", dict(webui.cameras[mac_address])
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

    @app.route("/api/dhcp/plugs", methods=["GET"])
    def get_plugs():
        """
        Get list of known plugs.

        Returns all detected plugs with their connection status.
        """
        plugs_list = list(webui.plugs.values())

        return (
            jsonify(
                {
                    "plugs": plugs_list,
                    "count": len(plugs_list),
                }
            ),
            200,
        )

    @app.route("/api/dhcp/plugs/<mac_address>", methods=["GET"])
    def get_plug(mac_address: str):
        """
        Get information about a specific plug.

        Args:
            mac_address: MAC address of the plug
        """
        plug = webui.plugs.get(mac_address)
        if not plug:
            return jsonify({"error": "Plug not found"}), 404

        return jsonify({"plug": plug}), 200

    @app.route("/api/dhcp/plugs", methods=["POST"])
    def add_plug():
        """
        Manually add a plug (for testing purposes).

        Expected JSON payload:
        {
            "hostname": "plug-name",
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

            # Add plug to webui.plugs
            webui.plugs[mac_address] = {
                "hostname": hostname,
                "ip_address": ip_address,
                "mac_address": mac_address,
                "last_seen": timestamp,
                "status": status,
            }

            # Update settings with plug list
            plug_list = []
            for _, plug_info in webui.plugs.items():
                plug_list.append(
                    {
                        "hostname": plug_info["hostname"],
                        "ip_address": plug_info["ip_address"],
                        "mac_address": plug_info["mac_address"],
                        "last_seen": plug_info["last_seen"],
                        "status": plug_info["status"],
                    }
                )

            webui.presets.plugs = plug_list

            # Persist to settings file
            try:
                webui.presets.save()
                logger.info(
                    "Manually added plug '%s' at %s", hostname, ip_address
                )
            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    "Failed to save plug list to settings: %s", str(e)
                )

            # Notify SSE clients
            notify_camera_change("plug_added", dict(webui.plugs[mac_address]))

            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Plug added successfully",
                        "plug": webui.plugs[mac_address],
                    }
                ),
                201,
            )

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error adding plug: %s", str(e))
            return (
                jsonify(
                    {
                        "error": "Failed to add plug",
                    }
                ),
                500,
            )

    @app.route("/api/dhcp/plugs", methods=["DELETE"])
    def clear_plugs():
        """
        Clear all plug records.

        This removes all stored plug information from memory.
        """
        count = len(webui.plugs)
        webui.plugs.clear()
        logger.info("Cleared %d plug records", count)

        # Update settings
        webui.presets.plugs = []
        try:
            webui.presets.save()
            logger.info("Plug list cleared from settings")
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to save plug list to settings: %s", str(e))

        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Cleared {count} plug record(s)",
                }
            ),
            200,
        )

    @app.route("/api/dhcp/cameras/events", methods=["GET"])
    def camera_events():
        """
        Server-Sent Events (SSE) endpoint for real-time camera status updates.

        This endpoint provides a stream of camera status changes including:
        - camera_connected: A camera has connected
        - camera_disconnected: A camera has disconnected
        - camera_added: A camera was manually added
        - camera_status_changed: Camera status changed (from heartbeat)

        The stream sends JSON-formatted events with the following structure:
        {
            "type": "event_type",
            "data": {...camera data...},
            "timestamp": "ISO8601 timestamp"
        }
        """

        def event_stream():
            # Create a queue for this client
            client_queue: queue.Queue = queue.Queue(maxsize=10)

            with sse_clients_lock:
                sse_clients.append(client_queue)

            logger.info(
                "SSE client connected, total clients: %d", len(sse_clients)
            )

            try:
                # Send initial connection message
                # Send initial connection message
                initial_msg = {
                    "type": "connected",
                    "timestamp": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
                yield f"data: {json.dumps(initial_msg)}\n\n"

                # Stream events to client
                while True:
                    try:
                        # Wait for messages with timeout for periodic keepalive
                        message = client_queue.get(timeout=30)
                        yield f"data: {json.dumps(message)}\n\n"
                    except queue.Empty:
                        # Send keepalive comment to prevent connection timeout
                        yield ": keepalive\n\n"
            except GeneratorExit:
                # Client disconnected
                logger.info("SSE client disconnected")
            finally:
                # Remove this client from the list
                with sse_clients_lock:
                    if client_queue in sse_clients:
                        sse_clients.remove(client_queue)
                logger.info(
                    "SSE client removed, remaining clients: %d",
                    len(sse_clients),
                )

        return Response(
            stream_with_context(event_stream()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # Return the notification callback so it can be wired to heartbeat
    return notify_camera_change
