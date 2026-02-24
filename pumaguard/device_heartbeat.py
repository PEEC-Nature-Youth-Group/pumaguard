"""Base class for device heartbeat monitoring in PumaGuard.

This module provides a common abstract base class for monitoring device
availability in the background. It handles thread management, status updates,
persistence, and stale device removal.
"""

from __future__ import (
    annotations,
)

import logging
import threading
from abc import (
    ABC,
    abstractmethod,
)
from collections.abc import (
    Callable,
)
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


class DeviceHeartbeat(ABC):
    """
    Abstract base class for device heartbeat monitoring.

    Provides common functionality for monitoring device availability via
    background threads. Subclasses must implement device-specific check
    methods and persistence logic.
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        webui: "WebUI",
        device_type: str,
        interval: int = 60,
        enabled: bool = True,
        status_change_callback: Callable[[str, dict], None] | None = None,
        auto_remove_enabled: bool = False,
        auto_remove_hours: int = 24,
    ):
        """
        Initialize the device heartbeat monitor.

        Args:
            webui: WebUI instance containing device information
            device_type: Type of device being monitored
                (e.g., "plug", "camera")
            interval: Check interval in seconds (default: 60)
            enabled: Enable heartbeat monitoring (default: True)
            status_change_callback: Optional callback function to be
                called when device status changes. Signature:
                callback(event_type: str, device_data: dict)
            auto_remove_enabled: Enable automatic removal of stale devices
                (default: False)
            auto_remove_hours: Hours of inactivity before auto-removal
                (default: 24)
        """
        self.webui = webui
        self.device_type = device_type
        self.interval = interval
        self.enabled = enabled
        self.status_change_callback = status_change_callback
        self.auto_remove_enabled = auto_remove_enabled
        self.auto_remove_hours = auto_remove_hours

        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @abstractmethod
    def check_device(self, ip_address: str) -> bool:
        """
        Check if a device is reachable.

        Subclasses must implement this method with their specific
        connectivity check logic (HTTP, ICMP, TCP, etc.).

        Args:
            ip_address: IP address of the device

        Returns:
            True if device is reachable, False otherwise
        """

    @abstractmethod
    def _get_devices_dict(self) -> dict:
        """
        Get the devices dictionary from webui.

        Returns:
            Dictionary mapping MAC addresses to device info
            (e.g., webui.plugs or webui.cameras)
        """

    @abstractmethod
    def _save_device_list(self) -> None:
        """
        Save the device list to settings file.

        Subclasses must implement this to persist their specific
        device attributes to the settings file.
        """

    @abstractmethod
    def _get_log_context(self) -> str:
        """
        Get logging context string for this device type.

        Returns:
            String describing monitoring configuration for logging
            (e.g., "interval=60s, timeout=5s" or "method=tcp, port=80")
        """

    def _update_device_status(
        self, mac_address: str, is_reachable: bool
    ) -> None:
        """
        Update device status and last_seen timestamp.

        Args:
            mac_address: MAC address of the device
            is_reachable: Whether the device is currently reachable
        """
        devices = self._get_devices_dict()
        if mac_address not in devices:
            return

        device = devices[mac_address]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        status_changed = False

        if is_reachable:
            # Device is reachable - update status to connected
            if device["status"] != "connected":
                logger.info(
                    "%s '%s' is now reachable at %s",
                    self.device_type.capitalize(),
                    device["hostname"],
                    device["ip_address"],
                )
                status_changed = True
            device["status"] = "connected"
            device["last_seen"] = timestamp
        else:
            # Device is not reachable - update status to disconnected
            if device["status"] == "connected":
                logger.warning(
                    "%s '%s' is no longer reachable at %s",
                    self.device_type.capitalize(),
                    device["hostname"],
                    device["ip_address"],
                )
                status_changed = True
            device["status"] = "disconnected"
            # Don't update last_seen on failure - keep the last successful time

        # Persist changes to settings
        self._save_device_list()

        # Notify callback if status changed
        if status_changed and self.status_change_callback:
            try:
                event_type = (
                    f"{self.device_type}_status_changed_online"
                    if is_reachable
                    else f"{self.device_type}_status_changed_offline"
                )
                self.status_change_callback(event_type, dict(device))
            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    "Error calling status change callback: %s", str(e)
                )

    def _check_and_remove_stale_devices(self) -> None:
        """
        Check for devices not seen within configured timeout.

        Remove devices whose last_seen timestamp exceeds the
        configured hours threshold. Called during heartbeat
        monitoring loop if auto-removal is enabled.
        """
        now = datetime.now(timezone.utc)
        removal_threshold = timedelta(hours=self.auto_remove_hours)

        devices_to_remove = []
        devices = self._get_devices_dict()

        for mac_address, device in list(devices.items()):
            last_seen_str = device.get("last_seen")
            if not last_seen_str:
                continue

            try:
                # Parse ISO8601 timestamp
                last_seen = datetime.fromisoformat(
                    last_seen_str.replace("Z", "+00:00")
                )

                # Calculate time since last seen
                time_since_seen = now - last_seen
                hours_offline = time_since_seen.total_seconds() / 3600

                # Check if device exceeds removal threshold
                if time_since_seen > removal_threshold:
                    devices_to_remove.append((mac_address, device))
                    logger.info(
                        "%s '%s' (%s) not seen for %.1f hours, "
                        + "scheduling for auto-removal",
                        self.device_type.capitalize(),
                        device["hostname"],
                        mac_address,
                        hours_offline,
                    )
                # Log status for offline devices (debugging)
                elif device["status"] == "disconnected":
                    if self.auto_remove_enabled:
                        # Calculate time until removal
                        time_until_removal = (
                            removal_threshold - time_since_seen
                        )
                        hours_until_removal = (
                            time_until_removal.total_seconds() / 3600
                        )

                        logger.debug(
                            "%s '%s' (%s) at %s has been offline "
                            + "for %.1f hours, will be auto-removed "
                            + "in %.1f hours",
                            self.device_type.capitalize(),
                            device["hostname"],
                            mac_address,
                            device["ip_address"],
                            hours_offline,
                            hours_until_removal,
                        )
                    else:
                        # Auto-removal disabled, log offline duration
                        logger.debug(
                            "%s '%s' (%s) at %s has been offline "
                            + "for %.1f hours (auto-removal disabled)",
                            self.device_type.capitalize(),
                            device["hostname"],
                            mac_address,
                            device["ip_address"],
                            hours_offline,
                        )

            except (ValueError, AttributeError) as e:
                logger.warning(
                    "Could not parse last_seen timestamp for %s %s: %s",
                    self.device_type,
                    mac_address,
                    str(e),
                )

        # Remove devices outside iteration loop
        # (only if auto-removal is enabled)
        if self.auto_remove_enabled:
            for mac_address, device in devices_to_remove:
                try:
                    # Remove from in-memory dictionary
                    del devices[mac_address]

                    # Persist changes
                    self._save_device_list()

                    logger.info(
                        "Auto-removed %s '%s' (%s) at %s",
                        self.device_type,
                        device["hostname"],
                        mac_address,
                        device["ip_address"],
                    )

                    # Notify via SSE if callback is available
                    if self.status_change_callback:
                        try:
                            self.status_change_callback(
                                f"{self.device_type}_removed", dict(device)
                            )
                        except Exception as e:  # pylint: disable=broad-except
                            logger.error(
                                "Error calling status change callback "
                                + "for removal: %s",
                                str(e),
                            )

                except Exception as e:  # pylint: disable=broad-except
                    logger.error(
                        "Failed to auto-remove %s %s: %s",
                        self.device_type,
                        mac_address,
                        str(e),
                    )
        elif devices_to_remove:
            # Auto-removal disabled but devices would have been removed
            logger.debug(
                "%d %s(s) would be auto-removed but feature is disabled",
                len(devices_to_remove),
                self.device_type,
            )

    def _monitor_loop(self) -> None:
        """Main monitoring loop that runs in a background thread."""
        auto_remove_msg = ""
        if self.auto_remove_enabled:
            auto_remove_msg = f", auto-remove after {self.auto_remove_hours}h"

        logger.info(
            "%s heartbeat monitor started (%s%s)",
            self.device_type.capitalize(),
            self._get_log_context(),
            auto_remove_msg,
        )

        devices = self._get_devices_dict()

        while not self._stop_event.is_set():
            try:
                # Check each device
                for mac_address, device in list(devices.items()):
                    if self._stop_event.is_set():
                        break

                    ip_address = device["ip_address"]
                    if not ip_address:
                        continue

                    logger.debug(
                        "Checking %s '%s' at %s",
                        self.device_type,
                        device["hostname"],
                        ip_address,
                    )

                    is_reachable = self.check_device(ip_address)
                    self._update_device_status(mac_address, is_reachable)

                # Check for stale devices after status checks
                self._check_and_remove_stale_devices()

            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    "Error in %s heartbeat monitor loop: %s",
                    self.device_type,
                    str(e),
                )

            # Wait for the next check interval or stop event
            self._stop_event.wait(self.interval)

        logger.info(
            "%s heartbeat monitor stopped", self.device_type.capitalize()
        )

    def start(self) -> None:
        """Start the heartbeat monitoring thread."""
        if not self.enabled:
            logger.info(
                "%s heartbeat monitoring is disabled",
                self.device_type.capitalize(),
            )
            return

        if self._running:
            logger.warning(
                "%s heartbeat monitor is already running",
                self.device_type.capitalize(),
            )
            return

        self._running = True
        self._stop_event.clear()
        thread_name = f"{self.device_type.capitalize()}Heartbeat"
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name=thread_name
        )
        self._thread.start()
        logger.info(
            "%s heartbeat monitoring started", self.device_type.capitalize()
        )

    def stop(self) -> None:
        """Stop the heartbeat monitoring thread."""
        if not self._running:
            logger.warning(
                "%s heartbeat monitor is not running",
                self.device_type.capitalize(),
            )
            return

        self._running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning(
                    "%s heartbeat monitor thread did not stop cleanly",
                    self.device_type.capitalize(),
                )
            else:
                logger.info(
                    "%s heartbeat monitoring stopped",
                    self.device_type.capitalize(),
                )

    def check_now(self) -> dict[str, bool]:
        """
        Immediately check all devices and return results.

        This can be called manually to force a check outside the
        regular interval.

        Returns:
            Dictionary mapping MAC addresses to reachability status
        """
        results = {}
        devices = self._get_devices_dict()

        for mac_address, device in devices.items():
            ip_address = device["ip_address"]
            if not ip_address:
                results[mac_address] = False
                continue

            is_reachable = self.check_device(ip_address)
            self._update_device_status(mac_address, is_reachable)
            results[mac_address] = is_reachable

        return results
