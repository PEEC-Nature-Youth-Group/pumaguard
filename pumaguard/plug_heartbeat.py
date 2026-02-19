"""Plug heartbeat monitoring for PumaGuard.

This module provides background monitoring of Shelly plug availability using
HTTP REST API checks.
"""

from __future__ import (
    annotations,
)

import logging
import threading
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

import requests

if TYPE_CHECKING:
    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


class PlugHeartbeat:
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
        self.webui = webui
        self.interval = interval
        self.enabled = enabled
        self.timeout = timeout
        self.status_change_callback = status_change_callback
        self.auto_remove_enabled = auto_remove_enabled
        self.auto_remove_hours = auto_remove_hours

        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

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

    def _update_plug_status(
        self, mac_address: str, is_reachable: bool
    ) -> None:
        """
        Update plug status and last_seen timestamp.

        Args:
            mac_address: MAC address of the plug
            is_reachable: Whether the plug is currently reachable
        """
        if mac_address not in self.webui.plugs:
            return

        plug = self.webui.plugs[mac_address]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        status_changed = False

        if is_reachable:
            # Plug is reachable - update status to connected
            if plug["status"] != "connected":
                logger.info(
                    "Plug '%s' is now reachable at %s",
                    plug["hostname"],
                    plug["ip_address"],
                )
                status_changed = True
            plug["status"] = "connected"
            plug["last_seen"] = timestamp
        else:
            # Plug is not reachable - update status to disconnected
            if plug["status"] == "connected":
                logger.warning(
                    "Plug '%s' is no longer reachable at %s",
                    plug["hostname"],
                    plug["ip_address"],
                )
                status_changed = True
            plug["status"] = "disconnected"
            # Don't update last_seen on failure - keep the last successful time

        # Persist changes to settings
        self._save_plug_list()

        # Notify callback if status changed
        if status_changed and self.status_change_callback:
            try:
                event_type = (
                    "plug_status_changed_online"
                    if is_reachable
                    else "plug_status_changed_offline"
                )
                self.status_change_callback(event_type, dict(plug))
            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    "Error calling status change callback: %s", str(e)
                )

    def _save_plug_list(self) -> None:
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

    def _check_and_remove_stale_plugs(self) -> None:
        """
        Check for plugs not seen within configured timeout.

        Remove plugs whose last_seen timestamp exceeds the
        configured hours threshold. Called during heartbeat
        monitoring loop if auto-removal is enabled.
        """
        now = datetime.now(timezone.utc)
        removal_threshold = timedelta(hours=self.auto_remove_hours)

        plugs_to_remove = []

        for mac_address, plug in list(self.webui.plugs.items()):
            last_seen_str = plug.get("last_seen")
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

                # Check if plug exceeds removal threshold
                if time_since_seen > removal_threshold:
                    plugs_to_remove.append((mac_address, plug))
                    logger.info(
                        "Plug '%s' (%s) not seen for %.1f hours, "
                        "scheduling for auto-removal",
                        plug["hostname"],
                        mac_address,
                        hours_offline,
                    )
                # Log status for offline plugs (debugging)
                elif plug["status"] == "disconnected":
                    if self.auto_remove_enabled:
                        # Calculate time until removal
                        time_until_removal = (
                            removal_threshold - time_since_seen
                        )
                        hours_until_removal = (
                            time_until_removal.total_seconds() / 3600
                        )

                        logger.debug(
                            "Plug '%s' (%s) at %s has been offline "
                            "for %.1f hours, will be auto-removed "
                            "in %.1f hours",
                            plug["hostname"],
                            mac_address,
                            plug["ip_address"],
                            hours_offline,
                            hours_until_removal,
                        )
                    else:
                        # Auto-removal disabled, log offline duration
                        logger.debug(
                            "Plug '%s' (%s) at %s has been offline "
                            "for %.1f hours (auto-removal disabled)",
                            plug["hostname"],
                            mac_address,
                            plug["ip_address"],
                            hours_offline,
                        )

            except (ValueError, AttributeError) as e:
                logger.warning(
                    "Could not parse last_seen timestamp for plug %s: %s",
                    mac_address,
                    str(e),
                )

        # Remove plugs outside iteration loop
        # (only if auto-removal is enabled)
        if self.auto_remove_enabled:
            for mac_address, plug in plugs_to_remove:
                try:
                    # Remove from in-memory dictionary
                    del self.webui.plugs[mac_address]

                    # Persist changes
                    self._save_plug_list()

                    logger.info(
                        "Auto-removed plug '%s' (%s) at %s",
                        plug["hostname"],
                        mac_address,
                        plug["ip_address"],
                    )

                    # Notify via SSE if callback is available
                    if self.status_change_callback:
                        try:
                            self.status_change_callback(
                                "plug_removed", dict(plug)
                            )
                        except Exception as e:  # pylint: disable=broad-except
                            logger.error(
                                "Error calling status change callback "
                                + "for removal: %s",
                                str(e),
                            )

                except Exception as e:  # pylint: disable=broad-except
                    logger.error(
                        "Failed to auto-remove plug %s: %s",
                        mac_address,
                        str(e),
                    )
        elif plugs_to_remove:
            # Auto-removal disabled but plugs would have been removed
            logger.debug(
                "%d plug(s) would be auto-removed but feature is disabled",
                len(plugs_to_remove),
            )

    def _monitor_loop(self) -> None:
        """Main monitoring loop that runs in a background thread."""
        auto_remove_msg = ""
        if self.auto_remove_enabled:
            auto_remove_msg = f", auto-remove after {self.auto_remove_hours}h"

        logger.info(
            "Plug heartbeat monitor started (interval=%ds, timeout=%ds%s)",
            self.interval,
            self.timeout,
            auto_remove_msg,
        )

        while not self._stop_event.is_set():
            try:
                # Check each plug
                for mac_address, plug in list(self.webui.plugs.items()):
                    if self._stop_event.is_set():
                        break

                    ip_address = plug["ip_address"]
                    if not ip_address:
                        continue

                    logger.debug(
                        "Checking plug '%s' at %s",
                        plug["hostname"],
                        ip_address,
                    )

                    is_reachable = self.check_plug(ip_address)
                    self._update_plug_status(mac_address, is_reachable)

                # Check for stale plugs after status checks
                self._check_and_remove_stale_plugs()

            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    "Error in plug heartbeat monitor loop: %s", str(e)
                )

            # Wait for the next check interval or stop event
            self._stop_event.wait(self.interval)

        logger.info("Plug heartbeat monitor stopped")

    def start(self) -> None:
        """Start the heartbeat monitoring thread."""
        if not self.enabled:
            logger.info("Plug heartbeat monitoring is disabled")
            return

        if self._running:
            logger.warning("Plug heartbeat monitor is already running")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="PlugHeartbeat"
        )
        self._thread.start()
        logger.info("Plug heartbeat monitoring started")

    def stop(self) -> None:
        """Stop the heartbeat monitoring thread."""
        if not self._running:
            logger.warning("Plug heartbeat monitor is not running")
            return

        self._running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning(
                    "Plug heartbeat monitor thread did not stop cleanly"
                )
            else:
                logger.info("Plug heartbeat monitoring stopped")

    def check_now(self) -> dict[str, bool]:
        """
        Immediately check all plugs and return results.

        This can be called manually to force a check outside the
        regular interval.

        Returns:
            Dictionary mapping MAC addresses to reachability status
        """
        results = {}
        for mac_address, plug in self.webui.plugs.items():
            ip_address = plug["ip_address"]
            if not ip_address:
                results[mac_address] = False
                continue

            is_reachable = self.check_plug(ip_address)
            self._update_plug_status(mac_address, is_reachable)
            results[mac_address] = is_reachable

        return results
