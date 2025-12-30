"""Camera heartbeat monitoring for PumaGuard.

This module provides background monitoring of camera availability using
ICMP ping and TCP connection checks.
"""

from __future__ import annotations

import logging
import socket
import subprocess
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pumaguard.web_ui import WebUI

logger = logging.getLogger(__name__)


class CameraHeartbeat:
    """
    Background service to monitor camera availability via ICMP ping
    and TCP checks.

    The heartbeat monitor runs in a separate thread and periodically
    checks if cameras are reachable. It updates the camera status and
    last_seen timestamp based on the results.
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        webui: "WebUI",
        interval: int = 60,
        enabled: bool = True,
        check_method: str = "tcp",
        tcp_port: int = 80,
        tcp_timeout: int = 3,
        icmp_timeout: int = 2,
    ):
        """
        Initialize the camera heartbeat monitor.

        Args:
            webui: WebUI instance containing camera information
            interval: Check interval in seconds (default: 60)
            enabled: Enable heartbeat monitoring (default: True)
            check_method: Health check method - "icmp", "tcp", or
                "both" (default: "tcp")
            tcp_port: TCP port to check (default: 80 for HTTP)
            tcp_timeout: TCP connection timeout in seconds (default: 3)
            icmp_timeout: ICMP ping timeout in seconds (default: 2)
        """
        self.webui = webui
        self.interval = interval
        self.enabled = enabled
        self.check_method = check_method.lower()
        self.tcp_port = tcp_port
        self.tcp_timeout = tcp_timeout
        self.icmp_timeout = icmp_timeout

        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Validate check method
        if self.check_method not in ["icmp", "tcp", "both"]:
            logger.warning(
                "Invalid check_method '%s', defaulting to 'tcp'",
                self.check_method,
            )
            self.check_method = "tcp"

    def _check_icmp(self, ip_address: str) -> bool:
        """
        Check camera availability using ICMP ping.

        Args:
            ip_address: IP address to ping

        Returns:
            True if ping successful, False otherwise
        """
        try:
            # Use ping command with 1 packet and timeout
            # -c 1: send 1 packet
            # -W timeout: wait timeout seconds for response
            # -q: quiet output (only summary)
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(self.icmp_timeout), ip_address],
                capture_output=True,
                timeout=self.icmp_timeout + 1,
                check=False,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("ICMP ping failed for %s: %s", ip_address, str(e))
            return False

    def _check_tcp(self, ip_address: str, port: int) -> bool:
        """
        Check camera availability using TCP connection test.

        Args:
            ip_address: IP address to connect to
            port: TCP port to connect to

        Returns:
            True if connection successful, False otherwise
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.tcp_timeout)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            return result == 0
        except (socket.error, OSError) as e:
            logger.debug(
                "TCP connection failed for %s:%d: %s",
                ip_address,
                port,
                str(e),
            )
            return False

    def check_camera(self, ip_address: str) -> bool:
        """
        Check if a camera is reachable using the configured method.

        Args:
            ip_address: IP address of the camera

        Returns:
            True if camera is reachable, False otherwise
        """
        if self.check_method == "icmp":
            return self._check_icmp(ip_address)
        if self.check_method == "tcp":
            return self._check_tcp(ip_address, self.tcp_port)
        if self.check_method == "both":
            # Try ICMP first (faster), fall back to TCP
            if self._check_icmp(ip_address):
                return True
            return self._check_tcp(ip_address, self.tcp_port)
        return False

    def _update_camera_status(
        self, mac_address: str, is_reachable: bool
    ) -> None:
        """
        Update camera status and last_seen timestamp.

        Args:
            mac_address: MAC address of the camera
            is_reachable: Whether the camera is currently reachable
        """
        if mac_address not in self.webui.cameras:
            return

        camera = self.webui.cameras[mac_address]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if is_reachable:
            # Camera is reachable - update status to connected
            if camera["status"] != "connected":
                logger.info(
                    "Camera '%s' is now reachable at %s",
                    camera["hostname"],
                    camera["ip_address"],
                )
            camera["status"] = "connected"
            camera["last_seen"] = timestamp
        else:
            # Camera is not reachable - update status to disconnected
            if camera["status"] == "connected":
                logger.warning(
                    "Camera '%s' is no longer reachable at %s",
                    camera["hostname"],
                    camera["ip_address"],
                )
            camera["status"] = "disconnected"
            # Don't update last_seen on failure - keep the last successful time

        # Persist changes to settings
        self._save_camera_list()

    def _save_camera_list(self) -> None:
        """Save the camera list to settings file."""
        try:
            camera_list = []
            for _, cam_info in self.webui.cameras.items():
                camera_list.append(
                    {
                        "hostname": cam_info["hostname"],
                        "ip_address": cam_info["ip_address"],
                        "mac_address": cam_info["mac_address"],
                        "last_seen": cam_info["last_seen"],
                        "status": cam_info["status"],
                    }
                )
            self.webui.presets.cameras = camera_list
            self.webui.presets.save()
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to save camera list: %s", str(e))

    def _monitor_loop(self) -> None:
        """Main monitoring loop that runs in a background thread."""
        logger.info(
            "Camera heartbeat monitor started "
            "(method=%s, interval=%ds, port=%d)",
            self.check_method,
            self.interval,
            self.tcp_port,
        )

        while not self._stop_event.is_set():
            try:
                # Check each camera
                for mac_address, camera in list(self.webui.cameras.items()):
                    if self._stop_event.is_set():
                        break

                    ip_address = camera["ip_address"]
                    if not ip_address:
                        continue

                    logger.debug(
                        "Checking camera '%s' at %s",
                        camera["hostname"],
                        ip_address,
                    )

                    is_reachable = self.check_camera(ip_address)
                    self._update_camera_status(mac_address, is_reachable)

            except Exception as e:  # pylint: disable=broad-except
                logger.error("Error in heartbeat monitor loop: %s", str(e))

            # Wait for the next check interval or stop event
            self._stop_event.wait(self.interval)

        logger.info("Camera heartbeat monitor stopped")

    def start(self) -> None:
        """Start the heartbeat monitoring thread."""
        if not self.enabled:
            logger.info("Camera heartbeat monitoring is disabled")
            return

        if self._running:
            logger.warning("Heartbeat monitor is already running")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="CameraHeartbeat"
        )
        self._thread.start()
        logger.info("Camera heartbeat monitoring started")

    def stop(self) -> None:
        """Stop the heartbeat monitoring thread."""
        if not self._running:
            logger.warning("Heartbeat monitor is not running")
            return

        self._running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("Heartbeat monitor thread did not stop cleanly")
            else:
                logger.info("Camera heartbeat monitoring stopped")

    def check_now(self) -> dict[str, bool]:
        """
        Immediately check all cameras and return results.

        This can be called manually to force a check outside the
        regular interval.

        Returns:
            Dictionary mapping MAC addresses to reachability status
        """
        results = {}
        for mac_address, camera in self.webui.cameras.items():
            ip_address = camera["ip_address"]
            if not ip_address:
                results[mac_address] = False
                continue

            is_reachable = self.check_camera(ip_address)
            self._update_camera_status(mac_address, is_reachable)
            results[mac_address] = is_reachable

        return results
