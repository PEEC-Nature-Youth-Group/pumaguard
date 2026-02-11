"""
Test utils
"""
# pylint: disable=too-many-lines,import-outside-toplevel

import csv
import datetime
import hashlib
import os
import tempfile
import threading
import unittest
from pathlib import (
    Path,
)
from unittest.mock import (
    MagicMock,
    mock_open,
    patch,
)

import numpy as np
import PIL.Image

from pumaguard.presets import (
    Settings,
)
from pumaguard.utils import (
    cache_model_two_stage,
    classify_image_two_stage,
    clear_model_cache,
    get_cached_model,
    get_duration,
    get_md5,
    get_sha256,
    prepare_image,
)


class TestHashFunctions(unittest.TestCase):
    """
    Test Hash functions for files.
    """

    def test_get_sha256(self):
        """
        Test the sha256 function.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"Hello PumaGuard")
            tmp_name = tmp.name
        try:
            expected = hashlib.sha256(b"Hello PumaGuard").hexdigest()
            result = get_sha256(tmp_name)
            self.assertEqual(result, expected)
        finally:
            os.remove(tmp_name)

    def test_get_md5(self):
        """
        Test the md5 function.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"Hello PumaGuard")
            tmp_name = tmp.name
        try:
            expected = hashlib.md5(b"Hello PumaGuard").hexdigest()
            result = get_md5(tmp_name)
            self.assertEqual(result, expected)
        finally:
            os.remove(tmp_name)

    def test_get_sha256_large_file(self):
        """
        Test sha256 with a file larger than read buffer.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            # Write more than 65536 bytes (the buffer size)
            data = b"PumaGuard" * 10000
            tmp.write(data)
            tmp_name = tmp.name
        try:
            expected = hashlib.sha256(data).hexdigest()
            result = get_sha256(tmp_name)
            self.assertEqual(result, expected)
        finally:
            os.remove(tmp_name)

    def test_get_md5_large_file(self):
        """
        Test md5 with a file larger than read buffer.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            # Write more than 65536 bytes (the buffer size)
            data = b"PumaGuard" * 10000
            tmp.write(data)
            tmp_name = tmp.name
        try:
            expected = hashlib.md5(data).hexdigest()
            result = get_md5(tmp_name)
            self.assertEqual(result, expected)
        finally:
            os.remove(tmp_name)

    def test_get_sha256_empty_file(self):
        """
        Test sha256 with an empty file.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
        try:
            expected = hashlib.sha256(b"").hexdigest()
            result = get_sha256(tmp_name)
            self.assertEqual(result, expected)
        finally:
            os.remove(tmp_name)

    def test_get_md5_empty_file(self):
        """
        Test md5 with an empty file.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
        try:
            expected = hashlib.md5(b"").hexdigest()
            result = get_md5(tmp_name)
            self.assertEqual(result, expected)
        finally:
            os.remove(tmp_name)


class TestGetDuration(unittest.TestCase):
    """Test get_duration function."""

    def test_get_duration_one_second(self):
        """Test duration calculation for one second."""
        start = datetime.datetime(2024, 1, 1, 12, 0, 0)
        end = datetime.datetime(2024, 1, 1, 12, 0, 1)
        duration = get_duration(start, end)
        self.assertAlmostEqual(duration, 1.0, places=5)

    def test_get_duration_microseconds(self):
        """Test duration calculation with microseconds."""
        start = datetime.datetime(2024, 1, 1, 12, 0, 0, 0)
        end = datetime.datetime(2024, 1, 1, 12, 0, 0, 500000)
        duration = get_duration(start, end)
        self.assertAlmostEqual(duration, 0.5, places=5)

    def test_get_duration_zero(self):
        """Test duration calculation for same time."""
        time = datetime.datetime(2024, 1, 1, 12, 0, 0)
        duration = get_duration(time, time)
        self.assertAlmostEqual(duration, 0.0, places=5)

    def test_get_duration_multiple_minutes(self):
        """Test duration calculation for multiple minutes."""
        start = datetime.datetime(2024, 1, 1, 12, 0, 0)
        end = datetime.datetime(2024, 1, 1, 12, 5, 30)
        duration = get_duration(start, end)
        self.assertAlmostEqual(duration, 330.0, places=5)


class TestModelCache(unittest.TestCase):
    """Test model caching functionality."""

    def setUp(self):
        """Clear model cache before each test."""
        clear_model_cache()

    def tearDown(self):
        """Clear model cache after each test."""
        clear_model_cache()

    @patch("pumaguard.utils.keras.models.load_model")
    def test_get_cached_model_classifier_first_load(self, mock_load):
        """Test loading classifier model for the first time."""
        mock_model = MagicMock()
        mock_load.return_value = mock_model
        model_path = Path("/fake/path/model.h5")

        result = get_cached_model("classifier", model_path)

        mock_load.assert_called_once_with(str(model_path))
        self.assertEqual(result, mock_model)

    @patch("pumaguard.utils.ultralytics.YOLO")
    def test_get_cached_model_detector_first_load(self, mock_yolo):
        """Test loading detector model for the first time."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        model_path = Path("/fake/path/yolo.pt")

        result = get_cached_model("detector", model_path)

        mock_yolo.assert_called_once_with(str(model_path))
        self.assertEqual(result, mock_model)

    @patch("pumaguard.utils.keras.models.load_model")
    def test_get_cached_model_uses_cache_on_second_call(self, mock_load):
        """Test that model is loaded from cache on second call."""
        mock_model = MagicMock()
        mock_load.return_value = mock_model
        model_path = Path("/fake/path/model.h5")

        # First call
        result1 = get_cached_model("classifier", model_path)
        # Second call
        result2 = get_cached_model("classifier", model_path)

        # Should only load once
        mock_load.assert_called_once()
        self.assertEqual(result1, result2)
        self.assertIs(result1, result2)

    def test_get_cached_model_invalid_type(self):
        """Test that invalid model type raises ValueError."""
        model_path = Path("/fake/path/model.h5")

        with self.assertRaises(ValueError) as context:
            get_cached_model("invalid_type", model_path)

        self.assertIn("Unknown model type", str(context.exception))

    @patch("pumaguard.utils.keras.models.load_model")
    def test_get_cached_model_different_paths_different_cache(self, mock_load):
        """Test that different paths create different cache entries."""
        mock_model1 = MagicMock()
        mock_model2 = MagicMock()
        mock_load.side_effect = [mock_model1, mock_model2]

        path1 = Path("/fake/path/model1.h5")
        path2 = Path("/fake/path/model2.h5")

        result1 = get_cached_model("classifier", path1)
        result2 = get_cached_model("classifier", path2)

        self.assertEqual(mock_load.call_count, 2)
        self.assertIsNot(result1, result2)

    @patch("pumaguard.utils.ultralytics.YOLO")
    @patch("pumaguard.utils.keras.models.load_model")
    def test_get_cached_model_different_types_same_path(
        self, mock_load, mock_yolo
    ):
        """
        Test that different types with same path create different cache
        entries.
        """
        mock_classifier = MagicMock()
        mock_detector = MagicMock()
        mock_load.return_value = mock_classifier
        mock_yolo.return_value = mock_detector

        model_path = Path("/fake/path/model")

        result1 = get_cached_model("classifier", model_path)
        result2 = get_cached_model("detector", model_path)

        mock_load.assert_called_once()
        mock_yolo.assert_called_once()
        self.assertIsNot(result1, result2)

    @patch("pumaguard.utils.keras.models.load_model")
    def test_get_cached_model_thread_safety(self, mock_load):
        """Test that model caching is thread-safe."""
        mock_model = MagicMock()
        mock_load.return_value = mock_model
        model_path = Path("/fake/path/model.h5")

        results = []
        exceptions = []

        def load_model():
            try:
                result = get_cached_model("classifier", model_path)
                results.append(result)
            except Exception as e:  # pylint: disable=broad-exception-caught
                exceptions.append(e)

        # Create multiple threads trying to load the same model
        threads = [threading.Thread(target=load_model) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should not have any exceptions
        self.assertEqual(len(exceptions), 0)
        # All results should be the same cached model
        self.assertEqual(len(results), 10)
        for result in results:
            self.assertIs(result, mock_model)
        # Should only load once despite multiple threads
        mock_load.assert_called_once()

    @patch("pumaguard.utils.keras.backend.clear_session")
    @patch("pumaguard.utils.gc.collect")
    def test_clear_model_cache(self, mock_gc_collect, mock_clear_session):
        """Test clearing the model cache."""
        # First add something to cache
        with patch("pumaguard.utils.keras.models.load_model") as mock_load:
            mock_load.return_value = MagicMock()
            get_cached_model("classifier", Path("/fake/path/model.h5"))

        # Clear cache
        clear_model_cache()

        mock_clear_session.assert_called_once()
        mock_gc_collect.assert_called_once()

        # Next load should call load_model again (not use cache)
        with patch("pumaguard.utils.keras.models.load_model") as mock_load2:
            mock_load2.return_value = MagicMock()
            get_cached_model("classifier", Path("/fake/path/model.h5"))
            mock_load2.assert_called_once()


class TestPrepareImage(unittest.TestCase):
    """Test prepare_image function."""

    @patch("pumaguard.utils.keras.applications.xception.preprocess_input")
    @patch("pumaguard.utils.keras.preprocessing.image.img_to_array")
    @patch("pumaguard.utils.keras.preprocessing.image.load_img")
    def test_prepare_image_basic(
        self, mock_load_img, mock_img_to_array, mock_preprocess
    ):
        """Test basic image preparation."""
        mock_img = MagicMock()
        mock_load_img.return_value = mock_img
        mock_array = np.array([[[1, 2, 3]]])
        mock_img_to_array.return_value = mock_array
        mock_preprocess.return_value = mock_array

        image_path = "/fake/path/image.jpg"
        dimensions = (224, 224)

        result = prepare_image(image_path, dimensions)

        mock_load_img.assert_called_once_with(
            image_path, target_size=dimensions
        )
        mock_img_to_array.assert_called_once_with(mock_img)
        mock_preprocess.assert_called_once()
        # Result should have batch dimension
        self.assertEqual(result.shape[0], 1)

    @patch("pumaguard.utils.keras.preprocessing.image.load_img")
    def test_prepare_image_different_dimensions(self, mock_load_img):
        """Test image preparation with different target dimensions."""
        mock_img = MagicMock()
        mock_load_img.return_value = mock_img

        with patch(
            "pumaguard.utils.keras.preprocessing.image.img_to_array"
        ) as mock_img_to_array:
            mock_img_to_array.return_value = np.zeros((384, 384, 3))
            with patch(
                "pumaguard.utils.keras.applications.xception.preprocess_input"
            ) as mock_preprocess:
                mock_preprocess.return_value = np.zeros((1, 384, 384, 3))

                image_path = "/fake/path/image.jpg"
                dimensions = (384, 384)

                prepare_image(image_path, dimensions)

                mock_load_img.assert_called_once_with(
                    image_path, target_size=dimensions
                )


class TestCacheModelTwoStage(unittest.TestCase):
    """Test cache_model_two_stage function."""

    @patch("pumaguard.utils.ensure_model_available")
    def test_cache_model_two_stage_both_models(self, mock_ensure):
        """Test caching both models."""
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        cache_model_two_stage("yolo.pt", "classifier.h5", print_progress=True)

        self.assertEqual(mock_ensure.call_count, 2)
        mock_ensure.assert_any_call("classifier.h5", True)
        mock_ensure.assert_any_call("yolo.pt", True)

    @patch("pumaguard.utils.ensure_model_available")
    def test_cache_model_two_stage_no_progress(self, mock_ensure):
        """Test caching models without progress printing."""
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        cache_model_two_stage("yolo.pt", "classifier.h5", print_progress=False)

        self.assertEqual(mock_ensure.call_count, 2)
        mock_ensure.assert_any_call("classifier.h5", False)
        mock_ensure.assert_any_call("yolo.pt", False)


class TestClassifyImageTwoStage(unittest.TestCase):
    """Test classify_image_two_stage function."""

    def setUp(self):
        """Set up test fixtures."""
        clear_model_cache()
        self.temp_dir = tempfile.mkdtemp()
        # Create a simple test image
        self.test_image_path = os.path.join(self.temp_dir, "test.jpg")
        img = PIL.Image.new("RGB", (640, 480), color="red")
        img.save(self.test_image_path)

    def tearDown(self):
        """Clean up test fixtures."""
        clear_model_cache()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("pumaguard.utils.ensure_model_available")
    @patch("pumaguard.utils.get_cached_model")
    def test_classify_image_two_stage_no_detections(
        self, mock_get_cached, mock_ensure
    ):
        """Test classification when YOLO detects nothing."""
        # Setup
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        # Mock detector with no detections
        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.boxes = None
        mock_detector.predict.return_value = [mock_result]

        mock_classifier = MagicMock()

        mock_get_cached.side_effect = [mock_detector, mock_classifier]

        presets = MagicMock(spec=Settings)
        presets.yolo_conf_thresh = 0.25
        presets.yolo_max_dets = 300
        presets.yolo_min_size = 0.02
        presets.classifier_model_filename = "classifier.h5"
        presets.yolo_model_filename = "yolo.pt"

        # Execute
        with patch("pumaguard.utils.plt"):
            result = classify_image_two_stage(
                presets, self.test_image_path, print_progress=False
            )

        # Verify
        self.assertEqual(result, 0.0)
        mock_detector.predict.assert_called_once()
        # Classifier should not be called if no detections
        mock_classifier.predict.assert_not_called()

    @patch("pumaguard.utils.ensure_model_available")
    @patch("pumaguard.utils.get_cached_model")
    def test_classify_image_two_stage_with_detections(
        self, mock_get_cached, mock_ensure
    ):
        """Test classification with YOLO detections."""
        # Setup
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        # Mock detector with one detection
        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_boxes = MagicMock()
        # Create a detection box [x1, y1, x2, y2]
        mock_boxes.xyxy = MagicMock()
        mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.array(
            [[100, 100, 300, 300]]
        )
        mock_result.boxes = mock_boxes
        mock_detector.predict.return_value = [mock_result]

        # Mock classifier returning 0.8 probability
        mock_classifier = MagicMock()
        mock_classifier.predict.return_value = np.array([[0.8]])

        mock_get_cached.side_effect = [mock_detector, mock_classifier]

        presets = MagicMock(spec=Settings)
        presets.yolo_conf_thresh = 0.25
        presets.yolo_max_dets = 300
        presets.yolo_min_size = (
            0.001  # Low threshold to ensure detection passes
        )
        presets.classifier_model_filename = "classifier.h5"
        presets.yolo_model_filename = "yolo.pt"

        # Execute
        with patch("pumaguard.utils.plt"):
            result = classify_image_two_stage(
                presets, self.test_image_path, print_progress=False
            )

        # Verify
        self.assertAlmostEqual(result, 0.8, places=5)
        mock_detector.predict.assert_called_once()
        mock_classifier.predict.assert_called_once()

    @patch("pumaguard.utils.ensure_model_available")
    @patch("pumaguard.utils.get_cached_model")
    def test_classify_image_two_stage_filters_small_boxes(
        self, mock_get_cached, mock_ensure
    ):
        """Test that small detections are filtered out."""
        # Setup
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        # Mock detector with one small detection
        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_boxes = MagicMock()
        # Create a very small detection box
        mock_boxes.xyxy = MagicMock()
        mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.array(
            [[100, 100, 105, 105]]  # 5x5 pixel box (very small)
        )
        mock_result.boxes = mock_boxes
        mock_detector.predict.return_value = [mock_result]

        mock_classifier = MagicMock()
        mock_get_cached.side_effect = [mock_detector, mock_classifier]

        presets = MagicMock(spec=Settings)
        presets.yolo_conf_thresh = 0.25
        presets.yolo_max_dets = 300
        presets.yolo_min_size = 0.1  # High threshold to filter small boxes
        presets.classifier_model_filename = "classifier.h5"
        presets.yolo_model_filename = "yolo.pt"

        # Execute
        with patch("pumaguard.utils.plt"):
            result = classify_image_two_stage(
                presets, self.test_image_path, print_progress=False
            )

        # Verify - should be 0 because box was filtered
        self.assertEqual(result, 0.0)
        mock_classifier.predict.assert_not_called()

    @patch("pumaguard.utils.ensure_model_available")
    @patch("pumaguard.utils.get_cached_model")
    def test_classify_image_two_stage_multiple_detections(
        self, mock_get_cached, mock_ensure
    ):
        """
        Test classification with multiple detections returns max
        probability.
        """
        # Setup
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        # Mock detector with multiple detections
        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_boxes = MagicMock()
        mock_boxes.xyxy = MagicMock()
        mock_boxes.xyxy.cpu.return_value.numpy.return_value = np.array(
            [[100, 100, 300, 300], [350, 100, 550, 300], [100, 350, 300, 550]]
        )
        mock_result.boxes = mock_boxes
        mock_detector.predict.return_value = [mock_result]

        # Mock classifier returning different probabilities
        mock_classifier = MagicMock()
        mock_classifier.predict.side_effect = [
            np.array([[0.3]]),
            np.array([[0.9]]),
            np.array([[0.5]]),
        ]

        mock_get_cached.side_effect = [mock_detector, mock_classifier]

        presets = MagicMock(spec=Settings)
        presets.yolo_conf_thresh = 0.25
        presets.yolo_max_dets = 300
        presets.yolo_min_size = 0.001
        presets.classifier_model_filename = "classifier.h5"
        presets.yolo_model_filename = "yolo.pt"

        # Execute
        with patch("pumaguard.utils.plt"):
            result = classify_image_two_stage(
                presets, self.test_image_path, print_progress=False
            )

        # Verify - should return max probability (0.9)
        self.assertAlmostEqual(result, 0.9, places=5)
        self.assertEqual(mock_classifier.predict.call_count, 3)

    @patch("pumaguard.utils.ensure_model_available")
    @patch("pumaguard.utils.get_cached_model")
    def test_classify_image_two_stage_creates_visualization(
        self, mock_get_cached, mock_ensure
    ):
        """Test that visualization files are created."""
        # Setup
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.boxes = None
        mock_detector.predict.return_value = [mock_result]

        mock_classifier = MagicMock()
        mock_get_cached.side_effect = [mock_detector, mock_classifier]

        presets = MagicMock(spec=Settings)
        presets.yolo_conf_thresh = 0.25
        presets.yolo_max_dets = 300
        presets.yolo_min_size = 0.02
        presets.classifier_model_filename = "classifier.h5"
        presets.yolo_model_filename = "yolo.pt"

        # Execute
        with patch("pumaguard.utils.plt") as mock_plt:
            classify_image_two_stage(
                presets,
                self.test_image_path,
                print_progress=False,
                intermediate_dir=self.temp_dir,
            )

            # Verify plot was saved
            mock_plt.savefig.assert_called_once()
            saved_path = mock_plt.savefig.call_args[0][0]
            self.assertTrue(saved_path.startswith(self.temp_dir))

    @patch("pumaguard.utils.ensure_model_available")
    @patch("pumaguard.utils.get_cached_model")
    def test_classify_image_two_stage_creates_csv_files(
        self, mock_get_cached, mock_ensure
    ):
        """Test that CSV files are created."""
        # Setup
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

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

        mock_classifier = MagicMock()
        mock_classifier.predict.return_value = np.array([[0.8]])
        mock_get_cached.side_effect = [mock_detector, mock_classifier]

        presets = MagicMock(spec=Settings)
        presets.yolo_conf_thresh = 0.25
        presets.yolo_max_dets = 300
        presets.yolo_min_size = 0.001
        presets.classifier_model_filename = "classifier.h5"
        presets.yolo_model_filename = "yolo.pt"

        # Execute
        with patch("pumaguard.utils.plt"):
            classify_image_two_stage(
                presets,
                self.test_image_path,
                print_progress=False,
                intermediate_dir=self.temp_dir,
            )

        # Verify CSV files exist
        detection_csv = os.path.join(
            self.temp_dir, "test_detections_predictions.csv"
        )
        image_csv = os.path.join(self.temp_dir, "test_image_summary.csv")

        self.assertTrue(os.path.exists(detection_csv))
        self.assertTrue(os.path.exists(image_csv))

        # Verify CSV content
        with open(detection_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["file"], self.test_image_path)
            self.assertAlmostEqual(float(rows[0]["prob_puma"]), 0.8, places=5)

        with open(image_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["file"], self.test_image_path)
            self.assertEqual(int(rows[0]["num_dets"]), 1)

    @patch("pumaguard.utils.ensure_model_available")
    @patch("pumaguard.utils.get_cached_model")
    def test_classify_image_two_stage_file_not_found(
        self, mock_get_cached, mock_ensure
    ):
        """Test that FileNotFoundError is raised for missing image."""
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        mock_detector = MagicMock()
        mock_classifier = MagicMock()
        mock_get_cached.side_effect = [mock_detector, mock_classifier]

        presets = MagicMock(spec=Settings)
        presets.classifier_model_filename = "classifier.h5"
        presets.yolo_model_filename = "yolo.pt"

        with self.assertRaises(FileNotFoundError):
            classify_image_two_stage(
                presets, "/nonexistent/image.jpg", print_progress=False
            )

    @patch("pumaguard.utils.ensure_model_available")
    @patch("pumaguard.utils.get_cached_model")
    @patch("pumaguard.utils.gc.collect")
    def test_classify_image_two_stage_calls_gc(
        self, mock_gc_collect, mock_get_cached, mock_ensure
    ):
        """Test that garbage collection is called after classification."""
        # Setup
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.boxes = None
        mock_detector.predict.return_value = [mock_result]

        mock_classifier = MagicMock()
        mock_get_cached.side_effect = [mock_detector, mock_classifier]

        presets = MagicMock(spec=Settings)
        presets.yolo_conf_thresh = 0.25
        presets.yolo_max_dets = 300
        presets.yolo_min_size = 0.02
        presets.classifier_model_filename = "classifier.h5"
        presets.yolo_model_filename = "yolo.pt"

        # Execute
        with patch("pumaguard.utils.plt"):
            classify_image_two_stage(
                presets, self.test_image_path, print_progress=False
            )

        # Verify gc.collect was called
        mock_gc_collect.assert_called()

    @patch("pumaguard.utils.ensure_model_available")
    @patch("pumaguard.utils.get_cached_model")
    def test_classify_image_two_stage_respects_print_progress(
        self, mock_get_cached, mock_ensure
    ):
        """Test that print_progress parameter is passed through."""
        mock_ensure.side_effect = [
            Path("/fake/classifier.h5"),
            Path("/fake/yolo.pt"),
        ]

        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.boxes = None
        mock_detector.predict.return_value = [mock_result]

        mock_classifier = MagicMock()
        mock_get_cached.side_effect = [mock_detector, mock_classifier]

        presets = MagicMock(spec=Settings)
        presets.yolo_conf_thresh = 0.25
        presets.yolo_max_dets = 300
        presets.yolo_min_size = 0.02
        presets.classifier_model_filename = "classifier.h5"
        presets.yolo_model_filename = "yolo.pt"

        # Test with print_progress=True
        with patch("pumaguard.utils.plt"):
            classify_image_two_stage(
                presets, self.test_image_path, print_progress=True
            )

        # Verify ensure_model_available was called with print_progress=True
        mock_ensure.assert_any_call("classifier.h5", True)
        mock_ensure.assert_any_call("yolo.pt", True)


class TestCopyImages(unittest.TestCase):
    """Test copy_images function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.work_dir = os.path.join(self.temp_dir, "work")
        os.makedirs(os.path.join(self.work_dir, "lion"))
        os.makedirs(os.path.join(self.work_dir, "no_lion"))

        # Create test images
        self.lion_images = []
        self.no_lion_images = []
        for i in range(2):
            img_path = os.path.join(self.temp_dir, f"lion_{i}.jpg")
            img = PIL.Image.new("RGB", (100, 100), color="red")
            img.save(img_path)
            self.lion_images.append(img_path)

        for i in range(3):
            img_path = os.path.join(self.temp_dir, f"no_lion_{i}.jpg")
            img = PIL.Image.new("RGB", (100, 100), color="blue")
            img.save(img_path)
            self.no_lion_images.append(img_path)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_copy_images_basic(self):
        """Test basic image copying."""
        from pumaguard.utils import (
            copy_images,
        )

        copy_images(self.work_dir, self.lion_images, self.no_lion_images)

        # Verify lion images were copied
        for img in self.lion_images:
            dest = os.path.join(self.work_dir, "lion", os.path.basename(img))
            self.assertTrue(os.path.exists(dest))

        # Verify no_lion images were copied
        for img in self.no_lion_images:
            dest = os.path.join(
                self.work_dir, "no_lion", os.path.basename(img)
            )
            self.assertTrue(os.path.exists(dest))

    def test_copy_images_empty_lists(self):
        """Test copying with empty image lists."""
        from pumaguard.utils import (
            copy_images,
        )

        copy_images(self.work_dir, [], [])

        # Should not raise error, just not copy anything
        lion_dir = os.path.join(self.work_dir, "lion")
        no_lion_dir = os.path.join(self.work_dir, "no_lion")
        self.assertEqual(len(os.listdir(lion_dir)), 0)
        self.assertEqual(len(os.listdir(no_lion_dir)), 0)

    def test_copy_images_prints_status(self, _capsys=None):
        """Test that copy_images prints status messages."""
        import sys
        from io import (
            StringIO,
        )

        from pumaguard.utils import (
            copy_images,
        )

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            copy_images(self.work_dir, self.lion_images, self.no_lion_images)
            output = captured_output.getvalue()

            self.assertIn("Copying images to working directory", output)
            self.assertIn("Copied all images", output)
            self.assertIn(os.path.realpath(self.work_dir), output)
        finally:
            sys.stdout = sys.__stdout__


class TestClassifyImageLegacy(unittest.TestCase):
    """Test classify_image (legacy function)."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = os.path.join(self.temp_dir, "test.jpg")
        img = PIL.Image.new("RGB", (224, 224), color="green")
        img.save(self.test_image_path)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("pumaguard.utils.keras.applications.Xception")
    @patch("pumaguard.utils.keras.models.load_model")
    @patch("pumaguard.utils.prepare_image")
    def test_classify_image_basic(
        self, mock_prepare, mock_load_model, mock_xception
    ):
        """Test basic legacy image classification."""
        from pumaguard.utils import (
            classify_image,
        )

        # Setup mocks
        mock_classifier = MagicMock()
        mock_classifier.predict.return_value = np.array([[0.75]])
        mock_load_model.return_value = mock_classifier

        mock_feature_extractor = MagicMock()
        mock_feature_extractor.predict.return_value = np.zeros((1, 2048))
        mock_xception.return_value = mock_feature_extractor

        mock_prepare.return_value = np.zeros((1, 224, 224, 3))

        presets = MagicMock(spec=Settings)
        presets.color_mode = "RGB"
        presets.image_dimensions = (224, 224)
        presets.base_output_directory = self.temp_dir

        # Create fake model file
        model_path = os.path.join(self.temp_dir, "model-ringtails.h5")
        with open(model_path, "w", encoding="utf-8") as f:
            f.write("fake model")

        result = classify_image(presets, self.test_image_path)

        self.assertAlmostEqual(result, 0.75, places=5)
        mock_load_model.assert_called_once()
        mock_xception.assert_called_once_with(
            weights="imagenet", include_top=True
        )
        mock_prepare.assert_called_once_with(
            self.test_image_path, presets.image_dimensions
        )

    @patch("pumaguard.utils.keras.applications.Xception")
    @patch("pumaguard.utils.keras.models.load_model")
    @patch("pumaguard.utils.prepare_image")
    def test_classify_image_handles_preprocessing_error(
        self, mock_prepare, mock_load_model, mock_xception
    ):
        """Test that preprocessing errors are handled and re-raised."""
        from pumaguard.utils import (
            classify_image,
        )

        # Setup mocks
        mock_classifier = MagicMock()
        mock_load_model.return_value = mock_classifier
        mock_feature_extractor = MagicMock()
        mock_xception.return_value = mock_feature_extractor

        mock_prepare.side_effect = Exception("Failed to load image")

        presets = MagicMock(spec=Settings)
        presets.color_mode = "RGB"
        presets.image_dimensions = (224, 224)
        presets.base_output_directory = self.temp_dir

        # Create fake model file
        model_path = os.path.join(self.temp_dir, "model-ringtails.h5")
        with open(model_path, "w", encoding="utf-8") as f:
            f.write("fake model")

        with self.assertRaises(Exception) as context:
            classify_image(presets, self.test_image_path)

        self.assertIn("Failed to load image", str(context.exception))


class TestPrintBashCompletion(unittest.TestCase):
    """Test print_bash_completion function."""

    @patch(
        "builtins.open", new_callable=mock_open, read_data="completion script"
    )
    @patch("pumaguard.utils.os.path.join")
    @patch("pumaguard.utils.os.path.dirname")
    def test_print_bash_completion_with_command(
        self, mock_dirname, mock_join, mock_file
    ):
        """Test printing bash completion with a command."""
        import sys
        from io import (
            StringIO,
        )

        from pumaguard.utils import (
            print_bash_completion,
        )

        mock_dirname.return_value = "/fake/pumaguard"
        mock_join.return_value = (
            "/fake/pumaguard/completions/pumaguard-test-completions.sh"
        )

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            print_bash_completion("test", "bash")
            output = captured_output.getvalue()

            self.assertEqual(output, "completion script\n")
            mock_file.assert_called_once_with(
                "/fake/pumaguard/completions/pumaguard-test-completions.sh",
                encoding="utf-8",
            )
        finally:
            sys.stdout = sys.__stdout__

    @patch(
        "builtins.open", new_callable=mock_open, read_data="main completion"
    )
    @patch("pumaguard.utils.os.path.join")
    @patch("pumaguard.utils.os.path.dirname")
    def test_print_bash_completion_without_command(
        self, mock_dirname, mock_join, _mock_file
    ):
        """Test printing bash completion without a command (main script)."""
        import sys
        from io import (
            StringIO,
        )

        from pumaguard.utils import (
            print_bash_completion,
        )

        mock_dirname.return_value = "/fake/pumaguard"
        mock_join.return_value = (
            "/fake/pumaguard/completions/pumaguard--completions.sh"
        )

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            print_bash_completion(None, "bash")
            output = captured_output.getvalue()

            self.assertEqual(output, "main completion\n")
            # Should have empty command string when None
            # (just "pumaguard-completions.sh")
            mock_join.assert_called()
            call_args = mock_join.call_args[0]
            self.assertIn("pumaguard-completions.sh", call_args)
        finally:
            sys.stdout = sys.__stdout__

    def test_print_bash_completion_invalid_shell(self):
        """Test that invalid shell raises ValueError."""
        from pumaguard.utils import (
            print_bash_completion,
        )

        with self.assertRaises(ValueError) as context:
            print_bash_completion("test", "zsh")

        self.assertIn("unknown shell", str(context.exception))
        self.assertIn("zsh", str(context.exception))
