"""Plug heartbeat monitoring for PumaGuard.

This module provides background monitoring of Shelly plug availability using
HTTP REST API checks.
"""

from __future__ import (
    annotations,
)

import logging
from collections.abc import (
    Callable,
)
from typing import (
    TYPE_CHECKING,
)

import requests

from pumaguard.device_heartbeat import (
    DeviceHeartbeat,
)

if TYPE_CHECKING:
    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


class PlugHeartbeat(DeviceHeartbeat):
    """
    Background service to monitor Shelly plug availability via HTTP REST API.

    The heartbeat monitor runs in a separate thread and periodically
    checks if plugs are reachable by querying their Shelly Gen2 REST API.
    It updates the plug status and last_seen timestamp based on the results.
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        webui: "WebUI",
        interval: int = 60,
        enabled: bool = True,
        timeout: int = 5,
        status_change_callback: Callable[[str, dict], None] | None = None,
        auto_remove_enabled: bool = False,
        auto_remove_hours: int = 24,
    ):
        """
        Initialize the plug heartbeat monitor.

        Args:
            webui: WebUI instance containing plug information
            interval: Check interval in seconds (default: 60)
            enabled: Enable heartbeat monitoring (default: True)
            timeout: HTTP request timeout in seconds (default: 5)
            status_change_callback: Optional callback function to be called
                when plug status changes. Signature:
                callback(event_type: str, plug_data: dict)
            auto_remove_enabled: Enable automatic removal of stale plugs
                (default: False)
            auto_remove_hours: Hours of inactivity before auto-removal
                (default: 24)
        """
        super().__init__(
            webui=webui,
            device_type="plug",
            interval=interval,
            enabled=enabled,
            status_change_callback=status_change_callback,
            auto_remove_enabled=auto_remove_enabled,
            auto_remove_hours=auto_remove_hours,
        )
        self.timeout = timeout

    def _check_http(self, ip_address: str) -> bool:
        """
        Check plug availability using HTTP REST API request.

        Queries the Shelly Gen2 Switch.GetStatus endpoint to verify
        the plug is responsive.

        Args:
            ip_address: IP address of the plug

        Returns:
            True if HTTP request successful, False otherwise
        """
        try:
            url = f"http://{ip_address}/rpc/Switch.GetStatus?id=0"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            # Verify response contains expected data
            data = response.json()
            return "output" in data
        except (
            requests.exceptions.RequestException,
            ValueError,
            KeyError,
        ) as e:
            logger.debug("HTTP check failed for %s: %s", ip_address, str(e))
            return False

    def check_plug(self, ip_address: str) -> bool:
        """
        Check if a plug is reachable.

        Args:
            ip_address: IP address of the plug

        Returns:
            True if plug is reachable, False otherwise
        """
        return self._check_http(ip_address)

    def check_device(self, ip_address: str) -> bool:
        """
        Check if a plug is reachable.

        This is the abstract method implementation that delegates to
        check_plug.

        Args:
            ip_address: IP address of the plug

        Returns:
            True if plug is reachable, False otherwise
        """
        return self.check_plug(ip_address)

    def _get_devices_dict(self) -> dict:
        """
        Get the plugs dictionary from webui.

        Returns:
            Dictionary mapping MAC addresses to plug info
        """
        return self.webui.plugs

    def _save_device_list(self) -> None:
        """Save the plug list to settings file."""
        try:
            plug_list = []
            for _, plug_info in self.webui.plugs.items():
                plug_list.append(
                    {
                        "hostname": plug_info["hostname"],
                        "ip_address": plug_info["ip_address"],
                        "mac_address": plug_info["mac_address"],
                        "last_seen": plug_info["last_seen"],
                        "status": plug_info["status"],
                        "mode": plug_info.get("mode", "off"),
                    }
                )
            self.webui.presets.plugs = plug_list
            self.webui.presets.save()
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to save plug list: %s", str(e))

    def _get_log_context(self) -> str:
        """
        Get logging context string for plug monitoring.

        Returns:
            String describing monitoring configuration
        """
        return f"interval={self.interval}s, timeout={self.timeout}s"

    # Aliases for backwards compatibility with tests
    _save_plug_list = _save_device_list

    # Backwards compatibility methods for tests
    def _update_plug_status(
        self, mac_address: str, is_reachable: bool
    ) -> None:
        """
        Update plug status and last_seen timestamp.

        This method is provided for backwards compatibility.
        New code should use _update_device_status() instead.

        Args:
            mac_address: MAC address of the plug
            is_reachable: Whether the plug is currently reachable
        """
        return self._update_device_status(mac_address, is_reachable)

    def _check_and_remove_stale_plugs(self) -> None:
        """
        Check for plugs not seen within configured timeout.

        This method is provided for backwards compatibility.
        New code should use _check_and_remove_stale_devices() instead.
        """
        return self._check_and_remove_stale_devices()
