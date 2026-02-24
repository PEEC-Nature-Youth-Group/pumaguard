"""Tests for Shelly smart plug control."""

from unittest.mock import (
    MagicMock,
    patch,
)

import requests

from pumaguard.shelly_control import (
    get_shelly_status,
    set_shelly_switch,
)


def test_get_shelly_status_success():
    """Test get_shelly_status returns device info successfully."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "output": True,
        "apower": 100.5,
        "voltage": 120.0,
        "current": 0.84,
    }
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, status, error = get_shelly_status("192.168.1.100", "TestPlug")

    assert success is True
    assert status is not None
    assert error is None
    assert status["output"] is True
    assert status["apower"] == 100.5


def test_get_shelly_status_timeout():
    """Test get_shelly_status handles timeout gracefully."""
    with patch(
        "pumaguard.shelly_control.requests.get",
        side_effect=requests.exceptions.Timeout(),
    ):
        success, status, error = get_shelly_status(
            "192.168.1.100", "TestPlug", timeout=2
        )

    assert success is False
    assert status is None
    assert error is not None
    assert "Timeout" in error


def test_get_shelly_status_connection_error():
    """Test get_shelly_status handles connection errors."""
    with patch(
        "pumaguard.shelly_control.requests.get",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        success, status, error = get_shelly_status("192.168.1.100", "TestPlug")

    assert success is False
    assert status is None
    assert error is not None


def test_get_shelly_status_http_error():
    """Test get_shelly_status handles HTTP errors."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found"
    )

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, status, error = get_shelly_status("192.168.1.100", "TestPlug")

    assert success is False
    assert status is None
    assert error is not None


def test_get_shelly_status_invalid_json():
    """Test get_shelly_status handles invalid JSON response."""
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, status, error = get_shelly_status("192.168.1.100", "TestPlug")

    assert success is False
    assert status is None
    assert error is not None
    assert "Invalid JSON" in error


def test_get_shelly_status_request_exception():
    """Test get_shelly_status handles general request exceptions."""
    with patch(
        "pumaguard.shelly_control.requests.get",
        side_effect=requests.exceptions.RequestException("Network error"),
    ):
        success, status, error = get_shelly_status("192.168.1.100", "TestPlug")

    assert success is False
    assert status is None
    assert error is not None


def test_get_shelly_status_custom_timeout():
    """Test get_shelly_status uses custom timeout."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": True}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ) as mock_get:
        get_shelly_status("192.168.1.100", "TestPlug", timeout=10)

    # Verify timeout parameter was passed
    mock_get.assert_called_once()
    assert mock_get.call_args[1]["timeout"] == 10


def test_get_shelly_status_empty_ip_address():
    """Test get_shelly_status with empty IP address."""
    success, status, error = get_shelly_status("", "TestPlug")

    assert success is False
    assert status is None
    assert error is not None
    assert "no IP address" in error


def test_set_shelly_switch_turn_on():
    """Test set_shelly_switch turns on the switch."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"was_on": False, "output": True}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, data, error = set_shelly_switch(
            "192.168.1.100", True, "TestPlug"
        )

    assert success is True
    assert data is not None
    assert error is None
    assert data["output"] is True


def test_set_shelly_switch_turn_off():
    """Test set_shelly_switch turns off the switch."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"was_on": True, "output": False}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, data, error = set_shelly_switch(
            "192.168.1.100", False, "TestPlug"
        )

    assert success is True
    assert data is not None
    assert error is None
    assert data["output"] is False


def test_set_shelly_switch_timeout():
    """Test set_shelly_switch handles timeout gracefully."""
    with patch(
        "pumaguard.shelly_control.requests.get",
        side_effect=requests.exceptions.Timeout(),
    ):
        success, data, error = set_shelly_switch(
            "192.168.1.100", True, "TestPlug", timeout=2
        )

    assert success is False
    assert data is None
    assert error is not None
    assert "Timeout" in error


def test_set_shelly_switch_connection_error():
    """Test set_shelly_switch handles connection errors."""
    with patch(
        "pumaguard.shelly_control.requests.get",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        success, data, error = set_shelly_switch(
            "192.168.1.100", True, "TestPlug"
        )

    assert success is False
    assert data is None
    assert error is not None


def test_set_shelly_switch_http_error():
    """Test set_shelly_switch handles HTTP errors."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "500 Server Error"
    )

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, data, error = set_shelly_switch(
            "192.168.1.100", True, "TestPlug"
        )

    assert success is False
    assert data is None
    assert error is not None


def test_set_shelly_switch_invalid_json():
    """Test set_shelly_switch handles invalid JSON response."""
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, data, error = set_shelly_switch(
            "192.168.1.100", True, "TestPlug"
        )

    assert success is False
    assert data is None
    assert error is not None
    assert "Invalid JSON" in error


def test_set_shelly_switch_request_exception():
    """Test set_shelly_switch handles general request exceptions."""
    with patch(
        "pumaguard.shelly_control.requests.get",
        side_effect=requests.exceptions.RequestException("Network error"),
    ):
        success, data, error = set_shelly_switch(
            "192.168.1.100", True, "TestPlug"
        )

    assert success is False
    assert data is None
    assert error is not None


def test_set_shelly_switch_custom_timeout():
    """Test set_shelly_switch uses custom timeout."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": True}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ) as mock_get:
        set_shelly_switch("192.168.1.100", True, "TestPlug", timeout=10)

    # Verify timeout parameter was passed
    mock_get.assert_called_once()
    assert mock_get.call_args[1]["timeout"] == 10


def test_set_shelly_switch_correct_url_on():
    """Test set_shelly_switch constructs correct URL for turning on."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": True}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ) as mock_get:
        set_shelly_switch("192.168.1.100", True, "TestPlug")

    # Verify URL contains correct parameters
    called_url = mock_get.call_args[0][0]
    assert "192.168.1.100" in called_url
    assert "Switch.Set" in called_url
    assert "id=0" in called_url
    assert "on=true" in called_url


def test_set_shelly_switch_correct_url_off():
    """Test set_shelly_switch constructs correct URL for turning off."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": False}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ) as mock_get:
        set_shelly_switch("192.168.1.100", False, "TestPlug")

    # Verify URL contains correct parameters
    called_url = mock_get.call_args[0][0]
    assert "192.168.1.100" in called_url
    assert "Switch.Set" in called_url
    assert "id=0" in called_url
    assert "on=false" in called_url


def test_set_shelly_switch_empty_ip_address():
    """Test set_shelly_switch with empty IP address."""
    success, data, error = set_shelly_switch("", True, "TestPlug")

    assert success is False
    assert data is None
    assert error is not None
    assert "no IP address" in error


def test_get_shelly_status_correct_url():
    """Test get_shelly_status constructs correct URL."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": True}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ) as mock_get:
        get_shelly_status("192.168.1.100", "TestPlug")

    # Verify URL
    called_url = mock_get.call_args[0][0]
    assert "192.168.1.100" in called_url
    assert "Switch.GetStatus" in called_url


def test_get_shelly_status_with_different_ip():
    """Test get_shelly_status with different IP address."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": False}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ) as mock_get:
        get_shelly_status("10.0.0.50", "AnotherPlug")

    called_url = mock_get.call_args[0][0]
    assert "10.0.0.50" in called_url


def test_set_shelly_switch_with_different_ip():
    """Test set_shelly_switch with different IP address."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": True}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ) as mock_get:
        set_shelly_switch("10.0.0.50", True, "AnotherPlug")

    called_url = mock_get.call_args[0][0]
    assert "10.0.0.50" in called_url


def test_get_shelly_status_complex_response():
    """Test get_shelly_status with complex device response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": 0,
        "source": "init",
        "output": True,
        "apower": 250.3,
        "voltage": 119.8,
        "current": 2.09,
        "aenergy": {
            "total": 12345.678,
            "by_minute": [1.2, 1.3, 1.1],
        },
        "temperature": {
            "tC": 42.5,
            "tF": 108.5,
        },
    }
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, status, error = get_shelly_status("192.168.1.100", "TestPlug")

    assert success is True
    assert status is not None
    assert error is None
    assert status["apower"] == 250.3
    assert status["aenergy"]["total"] == 12345.678


def test_set_shelly_switch_empty_hostname():
    """Test set_shelly_switch with empty hostname."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": True}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, data, error = set_shelly_switch("192.168.1.100", True, "")

    assert success is True
    assert data is not None
    assert error is None


def test_get_shelly_status_empty_hostname():
    """Test get_shelly_status with empty hostname."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": True}
    mock_response.raise_for_status = MagicMock()

    with patch(
        "pumaguard.shelly_control.requests.get", return_value=mock_response
    ):
        success, status, error = get_shelly_status("192.168.1.100", "")

    assert success is True
    assert status is not None
    assert error is None


def test_set_shelly_switch_general_exception():
    """Test set_shelly_switch handles unexpected exceptions."""
    with patch(
        "pumaguard.shelly_control.requests.get",
        side_effect=Exception("Unexpected error"),
    ):
        success, data, error = set_shelly_switch(
            "192.168.1.100", True, "TestPlug"
        )

    assert success is False
    assert data is None
    assert error is not None
    assert "Unexpected error" in error


def test_get_shelly_status_general_exception():
    """Test get_shelly_status handles unexpected exceptions."""
    with patch(
        "pumaguard.shelly_control.requests.get",
        side_effect=Exception("Unexpected error"),
    ):
        success, status, error = get_shelly_status("192.168.1.100", "TestPlug")

    assert success is False
    assert status is None
    assert error is not None
    assert "Unexpected error" in error
