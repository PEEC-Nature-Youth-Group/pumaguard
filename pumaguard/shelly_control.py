"""
Shared utilities for controlling Shelly smart plugs.

This module provides common functions for interacting with Shelly Gen2 devices
via their RPC API, used by both the server and web routes.
"""

import logging
from typing import (
    Dict,
    Optional,
    Tuple,
)

import requests

logger = logging.getLogger(__name__)


def set_shelly_switch(
    ip_address: str,
    on_state: bool,
    hostname: str = "unknown",
    timeout: int = 5,
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Control a Shelly plug switch using the Gen2 Switch.Set API.

    Args:
        ip_address: IP address of the Shelly plug
        on_state: True to turn on, False to turn off
        hostname: Hostname of the plug for logging (optional)
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Tuple of (success, response_data, error_message):
            - success: True if operation succeeded, False otherwise
            - response_data: Dict with Shelly response data if
                successful, None otherwise
            - error_message: Error description if failed, None if
                successful

    Example:
        >>> success, data, error = set_shelly_switch(
        ...     "192.168.1.100", True, "porch-plug"
        ... )
        >>> if success:
        ...     print(f"Was previously: {data['was_on']}")
        ... else:
        ...     print(f"Error: {error}")
    """
    if not ip_address:
        error = f"Cannot control plug '{hostname}': no IP address"
        logger.warning(error)
        return False, None, error

    try:
        # Call Shelly Gen2 Switch.Set API
        on_param = "true" if on_state else "false"
        shelly_url = f"http://{ip_address}/rpc/Switch.Set?id=0&on={on_param}"

        logger.info(
            "Setting plug '%s' switch to %s at %s",
            hostname,
            "ON" if on_state else "OFF",
            ip_address,
        )

        response = requests.get(shelly_url, timeout=timeout)
        response.raise_for_status()

        # Parse response data
        try:
            response_data = response.json()
        except ValueError as e:
            error = f"Invalid JSON response from Shelly: {e}"
            logger.error(
                "Error parsing Shelly response from %s: %s", ip_address, e
            )
            return False, None, error

        logger.info(
            "Successfully set plug '%s' switch to %s",
            hostname,
            "ON" if on_state else "OFF",
        )

        return True, response_data, None

    except requests.exceptions.Timeout:
        error = f"Timeout connecting to plug '{hostname}' at {ip_address}"
        logger.warning(error)
        return False, None, error

    except requests.exceptions.RequestException as e:
        error = f"Error setting plug '{hostname}' switch at {ip_address}: {e}"
        logger.error(error)
        return False, None, error

    except Exception as e:  # pylint: disable=broad-except
        error = f"Unexpected error controlling plug '{hostname}': {e}"
        logger.error(error)
        return False, None, error


def get_shelly_status(
    ip_address: str, hostname: str = "unknown", timeout: int = 5
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Get the current status of a Shelly plug using the Gen2
    Switch.GetStatus API.

    Args:
        ip_address: IP address of the Shelly plug
        hostname: Hostname of the plug for logging (optional)
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Tuple of (success, status_data, error_message):
            - success: True if operation succeeded, False
                otherwise
            - status_data: Dict with Shelly status data if
                successful, None otherwise
            - error_message: Error description if failed, None if
                successful

    Example:
        >>> success, data, error = get_shelly_status(
        ...     "192.168.1.100", "porch-plug"
        ... )
        >>> if success:
        ...     is_on = data['output']
        ...     print(f"Switch is: {'ON' if is_on else 'OFF'}")
        ... else:
        ...     print(f"Error: {error}")
    """
    if not ip_address:
        error = f"Cannot get status for plug '{hostname}': no IP address"
        logger.warning(error)
        return False, None, error

    try:
        shelly_url = f"http://{ip_address}/rpc/Switch.GetStatus?id=0"

        logger.debug(
            "Getting status for plug '%s' at %s", hostname, ip_address
        )

        response = requests.get(shelly_url, timeout=timeout)
        response.raise_for_status()

        # Parse response data
        try:
            status_data = response.json()
        except ValueError as e:
            error = f"Invalid JSON response from Shelly: {e}"
            logger.error(
                "Error parsing Shelly status from %s: %s", ip_address, e
            )
            return False, None, error

        logger.debug("Successfully retrieved status for plug '%s'", hostname)

        return True, status_data, None

    except requests.exceptions.Timeout:
        error = f"Timeout connecting to plug '{hostname}' at {ip_address}"
        logger.warning(error)
        return False, None, error

    except requests.exceptions.RequestException as e:
        error = (
            f"Error getting status for plug '{hostname}' at {ip_address}: {e}"
        )
        logger.error(error)
        return False, None, error

    except Exception as e:  # pylint: disable=broad-except
        error = f"Unexpected error getting status for plug '{hostname}': {e}"
        logger.error(error)
        return False, None, error
