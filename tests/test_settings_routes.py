"""Tests for settings routes."""

# pylint: disable=redefined-outer-name,unused-variable
# Pytest fixtures intentionally redefine names, and some variables
# are unpacked from fixtures but not used in all tests

import json
from unittest.mock import (
    MagicMock,
    mock_open,
    patch,
)

import pytest
from flask import (
    Flask,
)
from yaml.representer import (
    YAMLError,
)

from pumaguard.presets import (
    Settings,
)
from pumaguard.web_routes.settings import (
    register_settings_routes,
)
from pumaguard.web_ui import (
    WebUI,
)


@pytest.fixture
def mock_presets():
    """Create a mock Settings instance."""
    preset = MagicMock(spec=Settings)
    preset.yolo_min_size = 0.02
    preset.yolo_conf_thresh = 0.15
    preset.yolo_max_dets = 300
    preset.yolo_model_filename = "yolov8s.pt"
    preset.classifier_model_filename = "model.h5"
    preset.deterrent_sound_file = "sound.mp3"
    preset.deterrent_sound_files = ["sound.mp3", "sound2.mp3"]
    preset.file_stabilization_extra_wait = 2
    preset.play_sound = True
    preset.volume = 75
    preset.camera_url = "http://192.168.1.100"
    preset.camera_heartbeat_enabled = True
    preset.camera_heartbeat_interval = 60
    preset.camera_heartbeat_method = "tcp"
    preset.camera_heartbeat_tcp_port = 80
    preset.camera_heartbeat_tcp_timeout = 3
    preset.camera_heartbeat_icmp_timeout = 2
    preset.device_auto_remove_enabled = False
    preset.device_auto_remove_hours = 24
    preset.sound_path = "/path/to/sounds"
    preset.settings_file = "/path/to/settings.yaml"
    preset.__iter__ = MagicMock(
        return_value=iter(
            [
                ("yolo-min-size", 0.02),
                ("volume", 75),
            ]
        )
    )
    return preset


@pytest.fixture
def test_app(mock_presets):
    """Create a test Flask app with settings routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    webui = MagicMock(spec=WebUI)
    webui.presets = mock_presets
    webui.cameras = {
        "aa:bb:cc:dd:ee:01": {
            "hostname": "Camera1",
            "ip_address": "192.168.1.101",
            "mac_address": "aa:bb:cc:dd:ee:01",
            "last_seen": "2024-01-15T10:00:00Z",
            "status": "connected",
        }
    }
    webui.plugs = {
        "aa:bb:cc:dd:ee:02": {
            "hostname": "Plug1",
            "ip_address": "192.168.1.102",
            "mac_address": "aa:bb:cc:dd:ee:02",
            "last_seen": "2024-01-15T10:00:00Z",
            "status": "connected",
            "mode": "automatic",
        }
    }

    register_settings_routes(app, webui)

    return app, webui


def test_get_settings(test_app):
    """Test GET /api/settings returns current settings."""
    app, webui = test_app
    client = app.test_client()

    response = client.get("/api/settings")

    assert response.status_code == 200
    data = json.loads(response.data)
    # Verify cameras and plugs are included
    assert "cameras" in data
    assert len(data["cameras"]) == 1
    assert data["cameras"][0]["hostname"] == "Camera1"
    assert "plugs" in data
    assert len(data["plugs"]) == 1
    assert data["plugs"][0]["hostname"] == "Plug1"


def test_get_settings_empty_cameras_and_plugs():
    """Test GET /api/settings with no cameras or plugs."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    mock_presets = MagicMock(spec=Settings)
    mock_presets.__iter__ = MagicMock(return_value=iter([]))

    webui = MagicMock(spec=WebUI)
    webui.presets = mock_presets
    webui.cameras = {}
    webui.plugs = {}

    register_settings_routes(app, webui)
    client = app.test_client()

    response = client.get("/api/settings")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["cameras"] == []
    assert data["plugs"] == []


def test_update_settings_valid(test_app):
    """Test PUT /api/settings with valid data."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "YOLO-min-size": 0.03,
        "volume": 80,
        "play-sound": False,
    }

    with patch("builtins.open", mock_open()):
        with patch("pumaguard.web_routes.settings.yaml.dump"):
            response = client.put(
                "/api/settings",
                data=json.dumps(payload),
                content_type="application/json",
            )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["message"] == "Settings updated and saved"

    # Verify settings were updated
    assert webui.presets.yolo_min_size == 0.03
    assert webui.presets.volume == 80
    assert webui.presets.play_sound is False


def test_update_settings_no_data(test_app):
    """Test PUT /api/settings with no data."""
    app, webui = test_app
    client = app.test_client()

    response = client.put("/api/settings")

    # Flask returns 415 when no content-type is set
    assert response.status_code == 415


def test_update_settings_empty_dict(test_app):
    """Test PUT /api/settings with empty dict."""
    app, webui = test_app
    client = app.test_client()

    payload = {}

    response = client.put(
        "/api/settings",
        data=json.dumps(payload),
        content_type="application/json",
    )

    # Empty dict is technically valid JSON, but has no settings
    # The handler checks len(data) == 0 and raises ValueError which returns 500
    # However, looking at the actual implementation, it might return 400
    # Let's check what the actual response is
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_update_settings_unknown_key(test_app):
    """Test PUT /api/settings with unknown setting key."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "volume": 80,
        "unknown-setting": "value",
    }

    with patch("builtins.open", mock_open()):
        with patch("pumaguard.web_routes.settings.yaml.dump"):
            response = client.put(
                "/api/settings",
                data=json.dumps(payload),
                content_type="application/json",
            )

    # Should succeed but ignore unknown key
    assert response.status_code == 200
    assert webui.presets.volume == 80


def test_update_settings_camera_auto_remove_backward_compat(test_app):
    """Test PUT /api/settings with old camera-auto-remove settings."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "camera-auto-remove-enabled": True,
        "camera-auto-remove-hours": 48,
    }

    with patch("builtins.open", mock_open()):
        with patch("pumaguard.web_routes.settings.yaml.dump"):
            response = client.put(
                "/api/settings",
                data=json.dumps(payload),
                content_type="application/json",
            )

    assert response.status_code == 200
    # Should map to new generic names
    assert webui.presets.device_auto_remove_enabled is True
    assert webui.presets.device_auto_remove_hours == 48


def test_update_settings_yaml_error(test_app):
    """Test PUT /api/settings when YAML save fails."""
    app, webui = test_app
    client = app.test_client()

    payload = {"volume": 80}

    with patch("builtins.open", mock_open()):
        with patch(
            "pumaguard.web_routes.settings.yaml.dump",
            side_effect=YAMLError("YAML error"),
        ):
            response = client.put(
                "/api/settings",
                data=json.dumps(payload),
                content_type="application/json",
            )

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data


def test_save_settings_default_filepath(test_app):
    """Test POST /api/settings/save with default filepath."""
    app, webui = test_app
    client = app.test_client()

    with patch("builtins.open", mock_open()):
        with patch("pumaguard.web_routes.settings.yaml.dump"):
            response = client.post(
                "/api/settings/save",
                data=json.dumps({}),
                content_type="application/json",
            )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["filepath"] == webui.presets.settings_file


def test_save_settings_custom_filepath(test_app):
    """Test POST /api/settings/save with custom filepath."""
    app, webui = test_app
    client = app.test_client()

    custom_path = "/custom/path/settings.yaml"
    payload = {"filepath": custom_path}

    with patch("builtins.open", mock_open()):
        with patch("pumaguard.web_routes.settings.yaml.dump"):
            response = client.post(
                "/api/settings/save",
                data=json.dumps(payload),
                content_type="application/json",
            )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["filepath"] == custom_path


def test_load_settings_success(test_app):
    """Test POST /api/settings/load with valid filepath."""
    app, webui = test_app
    client = app.test_client()

    payload = {"filepath": "/path/to/settings.yaml"}

    response = client.post(
        "/api/settings/load",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["message"] == "Settings loaded"
    webui.presets.load.assert_called_once_with("/path/to/settings.yaml")


def test_load_settings_no_filepath(test_app):
    """Test POST /api/settings/load without filepath."""
    app, webui = test_app
    client = app.test_client()

    response = client.post(
        "/api/settings/load",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No filepath provided"


def test_test_sound_success(test_app):
    """Test POST /api/settings/test-sound with valid sound file."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=True
    ):
        with patch("pumaguard.web_routes.settings.playsound") as mock_play:
            response = client.post("/api/settings/test-sound")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "Sound started:" in data["message"]
    mock_play.assert_called_once()


def test_test_sound_no_files_configured(test_app):
    """Test POST /api/settings/test-sound with no sound files."""
    app, webui = test_app
    webui.presets.deterrent_sound_files = []
    client = app.test_client()

    response = client.post("/api/settings/test-sound")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No sound file configured"


def test_test_sound_file_not_found(test_app):
    """Test POST /api/settings/test-sound when file doesn't exist."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=False
    ):
        response = client.post("/api/settings/test-sound")

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert "Sound file not found:" in data["error"]


def test_test_sound_playback_disabled(test_app):
    """Test POST /api/settings/test-sound when play_sound is disabled."""
    app, webui = test_app
    webui.presets.play_sound = False
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=True
    ):
        response = client.post("/api/settings/test-sound")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "disabled" in data["message"]


def test_stop_test_sound_success(test_app):
    """Test POST /api/settings/stop-sound when sound is playing."""
    app, webui = test_app
    client = app.test_client()

    with patch("pumaguard.web_routes.settings.stop_sound", return_value=True):
        response = client.post("/api/settings/stop-sound")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["message"] == "Sound stopped"


def test_stop_test_sound_not_playing(test_app):
    """Test POST /api/settings/stop-sound when no sound is playing."""
    app, webui = test_app
    client = app.test_client()

    with patch("pumaguard.web_routes.settings.stop_sound", return_value=False):
        response = client.post("/api/settings/stop-sound")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["message"] == "No sound was playing"


def test_stop_test_sound_exception(test_app):
    """Test POST /api/settings/stop-sound with exception."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.stop_sound",
        side_effect=Exception("Stop failed"),
    ):
        response = client.post("/api/settings/stop-sound")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data


def test_get_sound_status_playing(test_app):
    """Test GET /api/settings/sound-status when sound is playing."""
    app, webui = test_app
    client = app.test_client()

    with patch("pumaguard.web_routes.settings.is_playing", return_value=True):
        response = client.get("/api/settings/sound-status")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["playing"] is True


def test_get_sound_status_not_playing(test_app):
    """Test GET /api/settings/sound-status when no sound is playing."""
    app, webui = test_app
    client = app.test_client()

    with patch("pumaguard.web_routes.settings.is_playing", return_value=False):
        response = client.get("/api/settings/sound-status")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["playing"] is False


def test_get_sound_status_exception(test_app):
    """Test GET /api/settings/sound-status with exception."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.is_playing",
        side_effect=Exception("Status check failed"),
    ):
        response = client.get("/api/settings/sound-status")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data


def test_test_detection_success(test_app):
    """Test POST /api/settings/test-detection with automatic plugs."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=True
    ):
        with patch("pumaguard.web_routes.settings.playsound"):
            with patch(
                "pumaguard.web_routes.settings.set_shelly_switch"
            ) as mock_shelly:
                response = client.post("/api/settings/test-detection")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "Detection test completed:" in data["message"]
    # Should turn on and off the automatic plug
    assert mock_shelly.call_count == 2


def test_test_detection_no_sound_files(test_app):
    """Test POST /api/settings/test-detection with no sound files."""
    app, webui = test_app
    webui.presets.deterrent_sound_files = []
    client = app.test_client()

    response = client.post("/api/settings/test-detection")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No sound file configured"


def test_test_detection_file_not_found(test_app):
    """Test POST /api/settings/test-detection when sound file doesn't exist."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=False
    ):
        response = client.post("/api/settings/test-detection")

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert "Sound file not found:" in data["error"]


def test_test_detection_playback_disabled(test_app):
    """Test POST /api/settings/test-detection when play_sound is disabled."""
    app, webui = test_app
    webui.presets.play_sound = False
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=True
    ):
        response = client.post("/api/settings/test-detection")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "disabled" in data["message"]


def test_test_detection_no_automatic_plugs(test_app):
    """Test POST /api/settings/test-detection with no automatic plugs."""
    app, webui = test_app
    webui.plugs = {}
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=True
    ):
        with patch("pumaguard.web_routes.settings.playsound"):
            with patch(
                "pumaguard.web_routes.settings.set_shelly_switch"
            ) as mock_shelly:
                response = client.post("/api/settings/test-detection")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    # Should not call shelly switch
    mock_shelly.assert_not_called()


def test_test_detection_manual_plug_not_triggered(test_app):
    """Test POST /api/settings/test-detection doesn't trigger manual plugs."""
    app, webui = test_app
    # Change plug to manual mode
    webui.plugs["aa:bb:cc:dd:ee:02"]["mode"] = "manual"
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=True
    ):
        with patch("pumaguard.web_routes.settings.playsound"):
            with patch(
                "pumaguard.web_routes.settings.set_shelly_switch"
            ) as mock_shelly:
                response = client.post("/api/settings/test-detection")

    assert response.status_code == 200
    # Should not trigger manual plug
    mock_shelly.assert_not_called()


def test_test_detection_disconnected_plug_not_triggered(
    test_app,
):
    """Test test-detection doesn't trigger disconnected plugs."""
    app, webui = test_app
    # Change plug to disconnected
    webui.plugs["aa:bb:cc:dd:ee:02"]["status"] = "disconnected"
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=True
    ):
        with patch("pumaguard.web_routes.settings.playsound"):
            with patch(
                "pumaguard.web_routes.settings.set_shelly_switch"
            ) as mock_shelly:
                response = client.post("/api/settings/test-detection")

    assert response.status_code == 200
    # Should not trigger disconnected plug
    mock_shelly.assert_not_called()


def test_get_available_models_classifier(test_app):
    """Test GET /api/models/available for classifier models."""
    app, webui = test_app
    client = app.test_client()

    mock_models_dir = MagicMock()
    mock_model_path = MagicMock()
    mock_model_path.exists.return_value = True
    mock_model_path.stat.return_value.st_size = 10 * 1024 * 1024  # 10MB
    mock_models_dir.__truediv__.return_value = mock_model_path

    with patch(
        "pumaguard.web_routes.settings.get_models_directory",
        return_value=mock_models_dir,
    ):
        with patch(
            "pumaguard.web_routes.settings.list_available_models",
            return_value=["model1.h5", "model2.h5", "yolo.pt"],
        ):
            with patch(
                "pumaguard.web_routes.settings.MODEL_REGISTRY",
                {
                    "model1.h5": {"sha256": "abc123"},
                    "model2.h5": {"sha256": "def456"},
                },
            ):
                with patch(
                    "pumaguard.web_routes.settings.verify_file_checksum",
                    return_value=True,
                ):
                    response = client.get("/api/models/available")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "models" in data
    # Should only return .h5 files for classifier
    assert len(data["models"]) == 2
    assert all(m["name"].endswith(".h5") for m in data["models"])


def test_get_available_models_yolo(test_app):
    """Test GET /api/models/available for YOLO models."""
    app, webui = test_app
    client = app.test_client()

    mock_models_dir = MagicMock()
    mock_model_path = MagicMock()
    mock_model_path.exists.return_value = True
    mock_model_path.stat.return_value.st_size = 20 * 1024 * 1024  # 20MB
    mock_models_dir.__truediv__.return_value = mock_model_path

    with patch(
        "pumaguard.web_routes.settings.get_models_directory",
        return_value=mock_models_dir,
    ):
        with patch(
            "pumaguard.web_routes.settings.list_available_models",
            return_value=["model1.h5", "yolo1.pt", "yolo2.pt"],
        ):
            with patch(
                "pumaguard.web_routes.settings.MODEL_REGISTRY",
                {
                    "yolo1.pt": {"sha256": "abc123"},
                    "yolo2.pt": {"sha256": "def456"},
                },
            ):
                with patch(
                    "pumaguard.web_routes.settings.verify_file_checksum",
                    return_value=True,
                ):
                    response = client.get("/api/models/available?type=yolo")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "models" in data
    # Should only return .pt files for yolo
    assert len(data["models"]) == 2
    assert all(m["name"].endswith(".pt") for m in data["models"])


def test_get_available_models_not_cached(test_app):
    """Test GET /api/models/available when models are not cached."""
    app, webui = test_app
    client = app.test_client()

    mock_models_dir = MagicMock()
    mock_model_path = MagicMock()
    mock_model_path.exists.return_value = False
    mock_models_dir.__truediv__.return_value = mock_model_path

    with patch(
        "pumaguard.web_routes.settings.get_models_directory",
        return_value=mock_models_dir,
    ):
        with patch(
            "pumaguard.web_routes.settings.list_available_models",
            return_value=["model1.h5"],
        ):
            with patch(
                "pumaguard.web_routes.settings.MODEL_REGISTRY",
                {
                    "model1.h5": {"sha256": "abc123"},
                },
            ):
                response = client.get("/api/models/available")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["models"]) == 1
    assert data["models"][0]["cached"] is False
    assert data["models"][0]["size_mb"] is None


def test_get_available_models_exception(test_app):
    """Test GET /api/models/available handles exceptions."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.get_models_directory",
        side_effect=Exception("Directory error"),
    ):
        response = client.get("/api/models/available")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "error" in data


def test_get_available_sounds_success(test_app):
    """Test GET /api/sounds/available returns sound files."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=True
    ):
        with patch(
            "pumaguard.web_routes.settings.os.listdir",
            return_value=["sound1.mp3", "sound2.mp3", "other.txt"],
        ):
            with patch(
                "pumaguard.web_routes.settings.os.path.isfile",
                return_value=True,
            ):
                with patch(
                    "pumaguard.web_routes.settings.os.path.getsize",
                    return_value=5 * 1024 * 1024,
                ):
                    response = client.get("/api/sounds/available")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "sounds" in data
    # Should only return .mp3 files
    assert len(data["sounds"]) == 2
    assert all(s["name"].endswith(".mp3") for s in data["sounds"])


def test_get_available_sounds_path_not_found(test_app):
    """Test GET /api/sounds/available when sound path doesn't exist."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=False
    ):
        response = client.get("/api/sounds/available")

    assert response.status_code == 404
    data = json.loads(response.data)
    assert "error" in data
    assert "Sound path not found:" in data["error"]


def test_get_available_sounds_empty_directory(test_app):
    """Test GET /api/sounds/available with no sound files."""
    app, webui = test_app
    client = app.test_client()

    with patch(
        "pumaguard.web_routes.settings.os.path.exists", return_value=True
    ):
        with patch(
            "pumaguard.web_routes.settings.os.listdir", return_value=[]
        ):
            response = client.get("/api/sounds/available")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["sounds"] == []


def test_update_settings_all_allowed_fields(test_app):
    """Test PUT /api/settings with all allowed fields."""
    app, webui = test_app
    client = app.test_client()

    payload = {
        "YOLO-min-size": 0.03,
        "YOLO-conf-thresh": 0.2,
        "YOLO-max-dets": 500,
        "YOLO-model-filename": "new_yolo.pt",
        "classifier-model-filename": "new_classifier.h5",
        "deterrent-sound-file": "new_sound.mp3",
        "deterrent-sound-files": ["sound1.mp3", "sound2.mp3"],
        "file-stabilization-extra-wait": 3,
        "play-sound": True,
        "volume": 90,
        "camera-url": "http://192.168.1.200",
        "camera-heartbeat-enabled": False,
        "camera-heartbeat-interval": 120,
        "camera-heartbeat-method": "icmp",
        "camera-heartbeat-tcp-port": 8080,
        "camera-heartbeat-tcp-timeout": 5,
        "camera-heartbeat-icmp-timeout": 3,
        "device-auto-remove-enabled": True,
        "device-auto-remove-hours": 48,
    }

    with patch("builtins.open", mock_open()):
        with patch("pumaguard.web_routes.settings.yaml.dump"):
            response = client.put(
                "/api/settings",
                data=json.dumps(payload),
                content_type="application/json",
            )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True

    # Verify all settings were updated
    assert webui.presets.yolo_min_size == 0.03
    assert webui.presets.yolo_conf_thresh == 0.2
    assert webui.presets.yolo_max_dets == 500
    assert webui.presets.volume == 90
