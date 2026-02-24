"""Camera heartbeat monitoring for PumaGuard.

This module provides background monitoring of camera availability using
ICMP ping and TCP connection checks.
"""

from __future__ import (
    annotations,
)

import logging
import socket
import subprocess
from collections.abc import (
    Callable,
)
from typing import (
    TYPE_CHECKING,
)

from pumaguard.device_heartbeat import (
    DeviceHeartbeat,
)

if TYPE_CHECKING:
    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


class CameraHeartbeat(DeviceHeartbeat):
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
        status_change_callback: Callable[[str, dict], None] | None = None,
        auto_remove_enabled: bool = False,
        auto_remove_hours: int = 24,
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
            status_change_callback: Optional callback function to be called
                when camera status changes. Signature:
                callback(event_type: str, camera_data: dict)
            auto_remove_enabled: Enable automatic removal of stale cameras
                (default: False)
            auto_remove_hours: Hours of inactivity before auto-removal
                (default: 24)
        """
        super().__init__(
            webui=webui,
            device_type="camera",
            interval=interval,
            enabled=enabled,
            status_change_callback=status_change_callback,
            auto_remove_enabled=auto_remove_enabled,
            auto_remove_hours=auto_remove_hours,
        )
        self.check_method = check_method.lower()
        self.tcp_port = tcp_port
        self.tcp_timeout = tcp_timeout
        self.icmp_timeout = icmp_timeout

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

    def check_device(self, ip_address: str) -> bool:
        """
        Check if a camera is reachable.

        This is the abstract method implementation that delegates to
        check_camera.

        Args:
            ip_address: IP address of the camera

        Returns:
            True if camera is reachable, False otherwise
        """
        return self.check_camera(ip_address)

    def _get_devices_dict(self) -> dict:
        """
        Get the cameras dictionary from webui.

        Returns:
            Dictionary mapping MAC addresses to camera info
        """
        return self.webui.cameras

    def _save_device_list(self) -> None:
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

    def _get_log_context(self) -> str:
        """
        Get logging context string for camera monitoring.

        Returns:
            String describing monitoring configuration
        """
        return (
            f"method={self.check_method}, interval={self.interval}s, "
            f"port={self.tcp_port}"
        )

    # Alias for backwards compatibility with tests
    _save_camera_list = _save_device_list

    # Backwards compatibility methods for tests

    def _update_camera_status(
        self, mac_address: str, is_reachable: bool
    ) -> None:
        """
        Update camera status and last_seen timestamp.

        This method is provided for backwards compatibility.
        New code should use _update_device_status() instead.

        Args:
            mac_address: MAC address of the camera
            is_reachable: Whether the camera is currently reachable
        """
        return self._update_device_status(mac_address, is_reachable)

    def _check_and_remove_stale_cameras(self) -> None:
        """
        Check for cameras not seen within configured timeout.

        This method is provided for backwards compatibility.
        New code should use _check_and_remove_stale_devices() instead.
        """
        return self._check_and_remove_stale_devices()
