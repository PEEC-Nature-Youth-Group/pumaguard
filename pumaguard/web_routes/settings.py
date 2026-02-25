"""Settings routes for loading, saving, and updating presets."""

from __future__ import (
    annotations,
)

import logging
import os
import random
import subprocess
from typing import (
    TYPE_CHECKING,
)

import yaml
from flask import (
    jsonify,
    request,
)
from werkzeug.utils import (
    secure_filename,
)
from yaml.representer import (
    YAMLError,
)

from pumaguard.model_downloader import (
    MODEL_REGISTRY,
    get_models_directory,
    list_available_models,
    verify_file_checksum,
)
from pumaguard.shelly_control import (
    set_shelly_switch,
)
from pumaguard.sound import (
    get_volume,
    is_playing,
    playsound,
    stop_sound,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


def register_settings_routes(app: "Flask", webui: "WebUI") -> None:
    """Register settings endpoints for GET, PUT, save, and load."""

    @app.route("/api/settings", methods=["GET"])
    def get_settings():
        settings_dict = dict(webui.presets)
        # Add cameras from webui.cameras (runtime state)
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
        settings_dict["cameras"] = camera_list
        # Add plugs from webui.plugs (runtime state)
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
        settings_dict["plugs"] = plug_list
        # Override the stored volume with the live ALSA value so the UI
        # always reflects any manual amixer adjustments made outside of
        # PumaGuard.
        current_volume = get_volume()
        if current_volume is not None:
            settings_dict["volume"] = current_volume
            webui.presets.volume = current_volume
        return jsonify(settings_dict)

    @app.route("/api/settings", methods=["PUT"])
    def update_settings():
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400

            allowed_settings = [
                "YOLO-min-size",
                "YOLO-conf-thresh",
                "YOLO-max-dets",
                "YOLO-model-filename",
                "classifier-model-filename",
                "puma-threshold",
                "deterrent-sound-file",
                "deterrent-sound-files",
                "file-stabilization-extra-wait",
                "play-sound",
                "volume",
                "camera-url",
                "camera-heartbeat-enabled",
                "camera-heartbeat-interval",
                "camera-heartbeat-method",
                "camera-heartbeat-tcp-port",
                "camera-heartbeat-tcp-timeout",
                "camera-heartbeat-icmp-timeout",
                "camera-auto-remove-enabled",  # Backward compatibility
                "camera-auto-remove-hours",  # Backward compatibility
                "device-auto-remove-enabled",  # New generic name
                "device-auto-remove-hours",  # New generic name
            ]

            if len(data) == 0:
                raise ValueError("Did not receive any settings")

            for key, value in data.items():
                if key in allowed_settings:
                    logger.info(
                        "Updating setting %s with value %s", key, value
                    )
                    # Map old camera-specific names to new generic names
                    if key == "camera-auto-remove-enabled":
                        attr_name = "device_auto_remove_enabled"
                    elif key == "camera-auto-remove-hours":
                        attr_name = "device_auto_remove_hours"
                    else:
                        attr_name = key.replace("-", "_").replace(
                            "YOLO_", "yolo_"
                        )
                    setattr(webui.presets, attr_name, value)
                    # Log verification of volume setting
                    if key == "volume":
                        logger.info(
                            "Volume setting updated to %d, verified: %d",
                            value,
                            webui.presets.volume,
                        )
                else:
                    logger.debug("Skipping unknown/read-only setting: %s", key)

            try:
                filepath = webui.presets.settings_file
                settings_dict = dict(webui.presets)
                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.dump(settings_dict, f, default_flow_style=False)
                logger.info(
                    "Settings updated and saved to %s (volume: %d)",
                    filepath,
                    webui.presets.volume,
                )
            except YAMLError:
                logger.exception("Error saving settings")
                return (
                    jsonify(
                        {
                            "error": (
                                "Settings updated but failed to save due "
                                "to an internal error"
                            )
                        }
                    ),
                    500,
                )

            return jsonify(
                {"success": True, "message": "Settings updated and saved"}
            )
        except ValueError as e:  # pragma: no cover (unexpected)
            logger.error("Error updating settings: %s", e)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/save", methods=["POST"])
    def save_settings():
        data = request.json
        filepath = data.get("filepath") if data else None
        if not filepath:
            filepath = webui.presets.settings_file
        settings_dict = dict(webui.presets)
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(settings_dict, f, default_flow_style=False)
        logger.info("Settings saved to %s", filepath)
        return jsonify({"success": True, "filepath": filepath})

    @app.route("/api/settings/load", methods=["POST"])
    def load_settings():
        data = request.json
        filepath = data.get("filepath") if data else None
        if not filepath:
            return jsonify({"error": "No filepath provided"}), 400
        webui.presets.load(filepath)
        logger.info("Settings loaded from %s", filepath)
        return jsonify({"success": True, "message": "Settings loaded"})

    @app.route("/api/settings/test-sound", methods=["POST"])
    def test_sound():
        """Test the configured deterrent sound."""
        logger.info("=== Test sound endpoint called ===")
        try:
            sound_files = webui.presets.deterrent_sound_files
            logger.info("Configured sound files: %s", sound_files)

            if not sound_files:
                logger.warning("No sound files configured")
                return (
                    jsonify({"error": "No sound file configured"}),
                    400,
                )

            # Randomly select one sound from the list
            sound_file = random.choice(sound_files)
            logger.info("Selected sound file: %s", sound_file)

            # Combine sound_path with deterrent_sound_file
            sound_file_path = os.path.join(
                webui.presets.sound_path, sound_file
            )
            logger.info("Full sound file path: %s", sound_file_path)

            # Check if file exists
            if not os.path.exists(sound_file_path):
                logger.error("Sound file not found: %s", sound_file_path)
                return (
                    jsonify(
                        {"error": (f"Sound file not found: {sound_file_path}")}
                    ),
                    404,
                )

            # Play the sound with configured volume (non-blocking)
            volume = webui.presets.volume
            logger.info(
                "Starting sound playback: file=%s, volume=%d, play_sound=%s",
                sound_file_path,
                volume,
                webui.presets.play_sound,
            )

            if not webui.presets.play_sound:
                logger.warning(
                    "Sound playback is disabled in settings (play_sound=False)"
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Sound playback is disabled "
                            + "in settings",
                        }
                    ),
                    400,
                )

            playsound(sound_file_path, volume, blocking=False)
            logger.info("Sound playback command sent successfully")

            return jsonify(
                {
                    "success": True,
                    "message": f"Sound started: {sound_file}",
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error testing sound: %s", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/stop-sound", methods=["POST"])
    def stop_test_sound():
        """Stop the currently playing test sound."""
        try:
            stopped = stop_sound()
            if stopped:
                logger.info("Sound playback stopped")
                return jsonify(
                    {
                        "success": True,
                        "message": "Sound stopped",
                    }
                )
            return jsonify(
                {
                    "success": True,
                    "message": "No sound was playing",
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error stopping sound")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/sound-status", methods=["GET"])
    def get_sound_status():
        """Check if a sound is currently playing."""
        try:
            playing = is_playing()
            return jsonify(
                {
                    "playing": playing,
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error checking sound status")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/settings/test-detection", methods=["POST"])
    def test_detection():
        """Simulate a puma detection with sound and plug control."""
        logger.info("=== Test detection endpoint called ===")
        try:
            sound_files = webui.presets.deterrent_sound_files
            logger.info("Configured sound files: %s", sound_files)

            if not sound_files:
                logger.warning("No sound files configured")
                return (
                    jsonify({"error": "No sound file configured"}),
                    400,
                )

            # Randomly select one sound from the list
            sound_file = random.choice(sound_files)
            logger.info("Selected sound file: %s", sound_file)

            # Combine sound_path with deterrent_sound_file
            sound_file_path = os.path.join(
                webui.presets.sound_path, sound_file
            )
            logger.info("Full sound file path: %s", sound_file_path)

            # Check if file exists
            if not os.path.exists(sound_file_path):
                logger.error("Sound file not found: %s", sound_file_path)
                return (
                    jsonify(
                        {"error": (f"Sound file not found: {sound_file_path}")}
                    ),
                    404,
                )

            # Check if sound playback is enabled
            if not webui.presets.play_sound:
                logger.warning(
                    "Sound playback is disabled in settings (play_sound=False)"
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Sound playback is disabled "
                            + "in settings",
                        }
                    ),
                    400,
                )

            # Turn on automatic plugs before playing sound
            automatic_plugs = [
                plug
                for plug in webui.plugs.values()
                if plug.get("mode") == "automatic"
                and plug.get("status") == "connected"
            ]

            if automatic_plugs:
                logger.info(
                    "Turning on %d automatic plug(s)", len(automatic_plugs)
                )
                for plug in automatic_plugs:
                    ip_address = plug.get("ip_address")
                    hostname = plug.get("hostname", "unknown")
                    set_shelly_switch(ip_address, True, hostname)
            else:
                logger.debug("No automatic plugs to turn on")

            # Play the sound with configured volume (blocking)
            volume = webui.presets.volume
            logger.info(
                "Starting sound playback: file=%s, volume=%d",
                sound_file_path,
                volume,
            )

            playsound(sound_file_path, volume, blocking=True)
            logger.info("Sound playback completed")

            # Turn off automatic plugs after sound finishes
            if automatic_plugs:
                logger.info(
                    "Turning off %d automatic plug(s)", len(automatic_plugs)
                )
                for plug in automatic_plugs:
                    ip_address = plug.get("ip_address")
                    hostname = plug.get("hostname", "unknown")
                    set_shelly_switch(ip_address, False, hostname)
            else:
                logger.debug("No automatic plugs to turn off")

            return jsonify(
                {
                    "success": True,
                    "message": f"Detection test completed: {sound_file}",
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error testing detection: %s", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/api/models/available", methods=["GET"])
    def get_available_models():
        """Get list of available models with cache status.

        Query parameters:
            type: 'classifier' (*.h5 files) or 'yolo' (*.pt files)
                  Default: 'classifier'
        """
        try:
            model_type = request.args.get("type", "classifier")
            models_dir = get_models_directory()
            available_models = list_available_models()

            # Filter based on model type
            if model_type == "yolo":
                filtered_models = [
                    model
                    for model in available_models
                    if model.endswith(".pt")
                ]
            else:  # Default to classifier
                filtered_models = [
                    model
                    for model in available_models
                    if model.endswith(".h5")
                ]

            model_list = []
            for model_name in filtered_models:
                model_path = models_dir / model_name
                is_cached = False

                # Check if model exists and verify checksum
                if model_path.exists():
                    model_info = MODEL_REGISTRY[model_name]
                    sha256 = model_info.get("sha256")
                    if isinstance(sha256, str):
                        is_cached = verify_file_checksum(model_path, sha256)

                # Get model size info
                size_mb = None
                if model_path.exists():
                    size_mb = model_path.stat().st_size / (1024 * 1024)

                model_list.append(
                    {
                        "name": model_name,
                        "cached": is_cached,
                        "size_mb": size_mb,
                    }
                )

            # Sort models: cached first, then by name
            model_list.sort(key=lambda x: (not x["cached"], x["name"]))

            return jsonify({"models": model_list})

        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error getting available models")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/sounds/available", methods=["GET"])
    def get_available_sounds():
        """Get list of available sound files with file sizes."""
        try:
            sound_path = webui.presets.sound_path
            if not os.path.exists(sound_path):
                return (
                    jsonify({"error": f"Sound path not found: {sound_path}"}),
                    404,
                )

            # Only MP3 files are supported (mpg123 player)
            audio_extensions = {".mp3"}

            sound_files = []
            for filename in os.listdir(sound_path):
                filepath = os.path.join(sound_path, filename)
                if os.path.isfile(filepath):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in audio_extensions:
                        size_mb = os.path.getsize(filepath) / (1024 * 1024)
                        sound_files.append(
                            {
                                "name": filename,
                                "size_mb": size_mb,
                            }
                        )

            # Sort by name
            sound_files.sort(key=lambda x: x["name"])

            return jsonify({"sounds": sound_files})

        except Exception as e:  # pylint: disable=broad-except
            logger.exception("Error getting available sounds")
            return jsonify({"error": str(e)}), 500

    def _validate_uploaded_file():
        """Validate uploaded file exists and has proper format."""
        if "file" not in request.files:
            return {"error": "No file provided"}, 400

        logger.debug("Verifying uploaded sound file")
        uploaded_file = request.files["file"]

        if uploaded_file.filename == "" or uploaded_file.filename is None:
            return {"error": "No file selected"}, 400

        filename = os.path.basename(uploaded_file.filename)
        ext = os.path.splitext(filename)[1].lower()

        if ext != ".mp3":
            return {
                "error": (
                    "Unsupported file type. Only MP3 files are supported."
                )
            }, 400

        return None

    def _validate_mp3_file(filepath):
        """Validate MP3 file integrity and format."""
        # Check file size first
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            os.remove(filepath)
            return {"error": "Uploaded file is empty"}, 400

        # Check MP3 file signature
        with open(filepath, "rb") as f:
            header = f.read(3)
            is_id3 = header == b"ID3"
            is_mpeg = (
                len(header) >= 2
                and header[0] == 0xFF
                and (header[1] & 0xE0) == 0xE0
            )

            if not (is_id3 or is_mpeg):
                os.remove(filepath)
                return {
                    "error": ("File does not appear to be a valid MP3 file")
                }, 400

        # Test with mpg123 to ensure it can play
        try:
            result = subprocess.run(
                ["mpg123", "--test", filepath],
                capture_output=True,
                timeout=5,
                check=False,
            )

            if result.returncode != 0:
                os.remove(filepath)
                return {
                    "error": (
                        "MP3 file validation failed. File may be corrupted."
                    )
                }, 400

        except subprocess.TimeoutExpired:
            os.remove(filepath)
            return {"error": "File validation timeout"}, 400
        except FileNotFoundError:
            logger.warning("mpg123 not found, skipping audio validation")
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("Audio validation failed: %s", e)
            # Don't fail upload if validation fails, just log it

        return None

    @app.route("/api/sounds/upload", methods=["POST"])
    def upload_sound():
        """Upload a new sound file."""
        try:
            # Validate uploaded file
            error = _validate_uploaded_file()
            if error:
                return jsonify(error[0]), error[1]

            file = request.files["file"]
            # Type guard: _validate_uploaded_file ensures filename is not None
            assert file.filename is not None
            filename = secure_filename(file.filename)

            # Ensure sound path exists
            sound_path = webui.presets.sound_path
            os.makedirs(sound_path, exist_ok=True)

            filepath = os.path.join(sound_path, filename)

            # Check if file already exists
            if os.path.exists(filepath):
                msg = (
                    f"File '{filename}' already exists. "
                    "Please rename your file or "
                    "delete the existing one."
                )
                return jsonify({"error": msg}), 409

            # Save the file
            file.save(filepath)
            logger.info("Uploaded sound file: %s", filepath)

            # Validate MP3 file
            error = _validate_mp3_file(filepath)
            if error:
                return jsonify(error[0]), error[1]

            # Get file size
            size_mb = os.path.getsize(filepath) / (1024 * 1024)

            return jsonify(
                {
                    "success": True,
                    "message": f"Sound file uploaded: {filename}",
                    "filename": filename,
                    "size_mb": size_mb,
                }
            )

        except Exception:  # pylint: disable=broad-except
            logger.exception("Error uploading sound file")
            return (
                jsonify(
                    {
                        "error": (
                            "An internal error occurred while uploading the "
                            "sound file."
                        )
                    }
                ),
                500,
            )
