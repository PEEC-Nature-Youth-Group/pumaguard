"""
Integration tests for configurable puma threshold feature.

Tests the complete flow from API settings to classification behavior.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import (
    Path,
)
from unittest.mock import (
    MagicMock,
    patch,
)

import numpy as np
from PIL import (
    Image,
)

from pumaguard.presets import (
    Settings,
)
from pumaguard.utils import (
    classify_image_two_stage,
)
from pumaguard.web_ui import (
    WebUI,
)


class TestPumaThresholdIntegration(unittest.TestCase):
    """Test puma threshold configuration end-to-end."""

    def setUp(self):
        """Set up test fixtures."""
        self.presets = Settings()
        self.temp_dir = tempfile.mkdtemp()

        # Create a test image
        self.test_image_path = Path(self.temp_dir) / "test.jpg"
        # Create a simple test image using PIL
        img = Image.new("RGB", (640, 480), color="red")
        img.save(self.test_image_path)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_threshold_is_0_5(self):
        """Test that default puma threshold is 0.5."""
        presets = Settings()
        self.assertEqual(presets.puma_threshold, 0.5)

    def test_threshold_can_be_set(self):
        """Test that puma threshold can be updated."""
        self.presets.puma_threshold = 0.7
        self.assertEqual(self.presets.puma_threshold, 0.7)

    def test_threshold_persists_to_yaml(self):
        """Test that threshold is saved and loaded from YAML."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            settings_file = f.name

        try:
            # Set and save
            self.presets.puma_threshold = 0.75
            self.presets.settings_file = settings_file
            self.presets.save()

            # Load in new instance
            new_presets = Settings()
            new_presets.load(settings_file)

            self.assertEqual(new_presets.puma_threshold, 0.75)
        finally:
            os.unlink(settings_file)

    def test_threshold_in_serialization(self):
        """Test that threshold appears in dict representation."""
        self.presets.puma_threshold = 0.65
        settings_dict = dict(self.presets)

        self.assertIn("puma-threshold", settings_dict)
        self.assertEqual(settings_dict["puma-threshold"], 0.65)

    def test_threshold_validation_rejects_invalid_values(self):
        """Test that invalid threshold values are rejected."""
        # Test zero
        with self.assertRaises(ValueError) as context:
            self.presets.puma_threshold = 0.0
        self.assertIn("between (0, 1]", str(context.exception))

        # Test negative
        with self.assertRaises(ValueError) as context:
            self.presets.puma_threshold = -0.5
        self.assertIn("between (0, 1]", str(context.exception))

        # Test too large
        with self.assertRaises(ValueError) as context:
            self.presets.puma_threshold = 1.5
        self.assertIn("between (0, 1]", str(context.exception))

        # Test non-numeric
        with self.assertRaises(TypeError) as context:
            self.presets.puma_threshold = "0.5"  # type: ignore
        self.assertIn("floating point number", str(context.exception))

    def test_threshold_used_in_visualization(self):
        """Test that threshold affects visualization labeling."""
        with (
            patch("pumaguard.utils.ensure_model_available"),
            patch("pumaguard.utils.get_cached_model"),
            patch("pumaguard.utils.plt"),
        ):
            # Mock detector with one detection
            mock_detector = MagicMock()
            mock_result = MagicMock()
            mock_boxes = MagicMock()
            mock_boxes.xyxy = MagicMock()
            mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.array(
                [[100, 100, 300, 300]]
            )
            mock_result.boxes = mock_boxes
            mock_detector.predict.return_value = [mock_result]

            # Mock classifier returning 0.6 probability
            mock_classifier = MagicMock()
            mock_classifier.predict.return_value = np.array([[0.6]])

            with patch("pumaguard.utils.get_cached_model") as mock_get_cached:
                mock_get_cached.side_effect = [
                    mock_detector,
                    mock_classifier,
                ]

                # Test with threshold 0.5 (0.6 should be "Puma")
                self.presets.puma_threshold = 0.5
                self.presets.yolo_conf_thresh = 0.25
                self.presets.yolo_max_dets = 10  # Must be <= 20
                self.presets.yolo_min_size = 0.001
                self.presets.classifier_model_filename = "classifier.h5"
                self.presets.yolo_model_filename = "yolo.pt"

                result = classify_image_two_stage(
                    self.presets,
                    str(self.test_image_path),
                    print_progress=False,
                )

                self.assertAlmostEqual(result, 0.6, places=5)

    def test_threshold_affects_detection_decision(self):
        """Test that threshold determines detection vs no-detection."""
        # This tests the logic used in server.py
        predictions = [0.45, 0.50, 0.55, 0.75]

        # With threshold 0.5
        self.presets.puma_threshold = 0.5
        detections_at_0_5 = [
            p > self.presets.puma_threshold for p in predictions
        ]
        self.assertEqual(
            detections_at_0_5, [False, False, True, True]
        )  # 0.50 not > 0.5

        # With threshold 0.7
        self.presets.puma_threshold = 0.7
        detections_at_0_7 = [
            p > self.presets.puma_threshold for p in predictions
        ]
        self.assertEqual(detections_at_0_7, [False, False, False, True])

        # With threshold 0.4
        self.presets.puma_threshold = 0.4
        detections_at_0_4 = [
            p > self.presets.puma_threshold for p in predictions
        ]
        self.assertEqual(detections_at_0_4, [True, True, True, True])

    def test_api_can_update_threshold(self):
        """Test threshold can be updated via web API."""
        webui = WebUI(
            presets=self.presets,
            host="127.0.0.1",
            port=5000,
        )
        app = webui.app
        client = app.test_client()

        # Update threshold via API
        response = client.put(
            "/api/settings",
            json={"puma-threshold": 0.8},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])

        # Verify it was set
        self.assertEqual(self.presets.puma_threshold, 0.8)

    def test_api_returns_current_threshold(self):
        """Test threshold is returned in GET /api/settings."""
        self.presets.puma_threshold = 0.65

        webui = WebUI(
            presets=self.presets,
            host="127.0.0.1",
            port=5000,
        )
        app = webui.app
        client = app.test_client()

        response = client.get("/api/settings")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["puma-threshold"], 0.65)

    def test_edge_case_threshold_values(self):
        """Test threshold works correctly at edge values."""
        # Test exactly 1.0
        self.presets.puma_threshold = 1.0
        self.assertEqual(self.presets.puma_threshold, 1.0)

        # Test very small value
        self.presets.puma_threshold = 0.01
        self.assertEqual(self.presets.puma_threshold, 0.01)

        # Test typical values
        for threshold in [0.3, 0.5, 0.7, 0.9]:
            self.presets.puma_threshold = threshold
            self.assertEqual(self.presets.puma_threshold, threshold)

    def test_threshold_accepts_int_and_converts_to_float(self):
        """Test that integer threshold values are accepted and converted."""
        self.presets.puma_threshold = 1  # int
        self.assertEqual(self.presets.puma_threshold, 1.0)
        self.assertIsInstance(self.presets.puma_threshold, float)


if __name__ == "__main__":
    unittest.main()
