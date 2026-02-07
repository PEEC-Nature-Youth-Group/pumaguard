#!/usr/bin/env python3
"""
Manual test script for Shelly plug switch control API.

This script can be used to manually test the plug switch control functionality.
Run this while the PumaGuard server is running.

Usage:
    python tests/manual_test_plug_switch.py --help
"""

import argparse
import json
import sys
import time

import requests


def test_get_plugs(base_url: str) -> dict:
    """Get list of all plugs."""
    print("\n=== Getting list of plugs ===")
    url = f"{base_url}/api/dhcp/plugs"
    response = requests.get(url, timeout=10)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data


def test_get_plug(base_url: str, mac_address: str) -> dict:
    """Get specific plug information."""
    print(f"\n=== Getting plug info for {mac_address} ===")
    url = f"{base_url}/api/dhcp/plugs/{mac_address}"
    response = requests.get(url, timeout=10)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data


def test_get_shelly_status(base_url: str, mac_address: str) -> dict:
    """Get Shelly status from plug."""
    print(f"\n=== Getting Shelly status for {mac_address} ===")
    url = f"{base_url}/api/dhcp/plugs/{mac_address}/shelly-status"
    response = requests.get(url, timeout=10)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data


def test_set_switch(base_url: str, mac_address: str, on: bool) -> dict:
    """Set plug switch on or off."""
    print(
        f"\n=== Setting switch to {'ON' if on else 'OFF'} "
        f"for {mac_address} ==="
    )
    url = f"{base_url}/api/dhcp/plugs/{mac_address}/switch"
    payload = {"on": on}
    response = requests.put(url, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data


def test_toggle_switch(base_url: str, mac_address: str, delay: int = 2):
    """Toggle switch on and off with a delay."""
    print(f"\n=== Toggling switch for {mac_address} ===")

    # Turn ON
    result = test_set_switch(base_url, mac_address, True)
    if result.get("status") == "success":
        print(
            f"✓ Switch turned ON (was: {'ON' if result['was_on'] else 'OFF'})"
        )
    else:
        print(f"✗ Failed to turn ON: {result.get('error')}")
        return

    print(f"Waiting {delay} seconds...")
    time.sleep(delay)

    # Turn OFF
    result = test_set_switch(base_url, mac_address, False)
    if result.get("status") == "success":
        print(
            f"✓ Switch turned OFF (was: {'ON' if result['was_on'] else 'OFF'})"
        )
    else:
        print(f"✗ Failed to turn OFF: {result.get('error')}")


def test_error_cases(base_url: str, mac_address: str):
    """Test error handling."""
    print("\n=== Testing error cases ===")

    # Test 1: Invalid MAC address
    print("\n--- Test: Invalid MAC address ---")
    url = f"{base_url}/api/dhcp/plugs/99:99:99:99:99:99/switch"
    response = requests.put(url, json={"on": True}, timeout=10)
    print(f"Status: {response.status_code} (expected: 404)")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    # Test 2: Missing 'on' parameter
    print("\n--- Test: Missing 'on' parameter ---")
    url = f"{base_url}/api/dhcp/plugs/{mac_address}/switch"
    response = requests.put(url, json={}, timeout=10)
    print(f"Status: {response.status_code} (expected: 400)")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    # Test 3: Invalid 'on' parameter type
    print("\n--- Test: Invalid 'on' parameter type ---")
    url = f"{base_url}/api/dhcp/plugs/{mac_address}/switch"
    response = requests.put(url, json={"on": "true"}, timeout=10)
    print(f"Status: {response.status_code} (expected: 400)")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Manual test script for Shelly plug switch API"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:5000",
        help="Base URL of PumaGuard server (default: http://localhost:5000)",
    )
    parser.add_argument(
        "--mac",
        help="MAC address of plug to test (e.g., aa:bb:cc:dd:ee:ff)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all plugs and exit",
    )
    parser.add_argument(
        "--on",
        action="store_true",
        help="Turn switch ON",
    )
    parser.add_argument(
        "--off",
        action="store_true",
        help="Turn switch OFF",
    )
    parser.add_argument(
        "--toggle",
        action="store_true",
        help="Toggle switch ON then OFF",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Get Shelly status",
    )
    parser.add_argument(
        "--test-errors",
        action="store_true",
        help="Test error handling",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=2,
        help="Delay in seconds for toggle (default: 2)",
    )

    args = parser.parse_args()

    print(f"PumaGuard Server: {args.base_url}")

    try:
        # Test server connectivity
        response = requests.get(f"{args.base_url}/api/dhcp/plugs", timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(
            f"\n✗ Error: Cannot connect to PumaGuard server at {args.base_url}"
        )
        print(f"  {e}")
        print("\nMake sure the PumaGuard server is running.")
        sys.exit(1)

    # List plugs
    if args.list:
        test_get_plugs(args.base_url)
        return

    # Get MAC address
    if not args.mac:
        # Try to get first available plug
        plugs_data = test_get_plugs(args.base_url)
        if plugs_data.get("count", 0) == 0:
            print(
                "\n✗ No plugs found. Please specify --mac or add a plug first."
            )
            sys.exit(1)
        args.mac = plugs_data["plugs"][0]["mac_address"]
        print(f"\nUsing first available plug: {args.mac}")

    # Get plug info
    test_get_plug(args.base_url, args.mac)

    # Execute requested action
    if args.status:
        test_get_shelly_status(args.base_url, args.mac)
    elif args.on:
        test_set_switch(args.base_url, args.mac, True)
    elif args.off:
        test_set_switch(args.base_url, args.mac, False)
    elif args.toggle:
        test_toggle_switch(args.base_url, args.mac, args.delay)
    elif args.test_errors:
        test_error_cases(args.base_url, args.mac)
    else:
        # Run full test suite
        print("\n" + "=" * 60)
        print("Running full test suite")
        print("=" * 60)

        test_get_shelly_status(args.base_url, args.mac)
        test_toggle_switch(args.base_url, args.mac, args.delay)
        test_error_cases(args.base_url, args.mac)

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)


if __name__ == "__main__":
    main()
