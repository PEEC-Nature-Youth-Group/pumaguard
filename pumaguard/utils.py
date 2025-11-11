"""
Some utility functions.
"""

# pylint: disable=wrong-import-position

import datetime
import gc
import glob
import hashlib
import logging
import os
import shutil
import threading
from pathlib import (
    Path,
)
from typing import (
    Tuple,
)

import keras  # type: ignore
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas
import PIL
import tensorflow as tf  # type: ignore
import ultralytics

from pumaguard.model_downloader import (
    ensure_model_available,
)
from pumaguard.presets import (
    Preset,
)

logger = logging.getLogger("PumaGuard")

_MODEL_CACHE = {}
_CACHE_LOCK = threading.Lock()


def get_cached_model(model_type: str, model_path: Path):
    """
    Get a cached model or load it if not in cache.
    Thread-safe model caching to prevent memory leaks.

    Args:
        model_type: Either 'classifier' or 'detector'
        model_path: Path to the model file

    Returns:
        The loaded model from cache or freshly loaded
    """
    cache_key = f"{model_type}:{model_path}"

    with _CACHE_LOCK:
        if cache_key not in _MODEL_CACHE:
            logger.info(
                "Loading %s model from %s (caching for reuse)",
                model_type,
                model_path,
            )
            if model_type == "classifier":
                _MODEL_CACHE[cache_key] = keras.models.load_model(
                    str(model_path)
                )
            elif model_type == "detector":
                _MODEL_CACHE[cache_key] = ultralytics.YOLO(str(model_path))
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            logger.info("Model cached successfully")
        else:
            logger.debug("Using cached %s model", model_type)

    return _MODEL_CACHE[cache_key]


def clear_model_cache():
    """
    Clear the model cache. Use this if you need to reload models or free
    memory.
    **Warning**: Next classification will need to reload models from disk.
    """
    with _CACHE_LOCK:
        logger.info("Clearing model cache")
        _MODEL_CACHE.clear()
        if hasattr(keras.backend, "clear_session"):
            keras.backend.clear_session()
        gc.collect()


def get_duration(
    start_time: datetime.datetime, end_time: datetime.datetime
) -> float:
    """
    Get duration between start and end time in seconds.

    Args:
        start_time (datetime.timezone): The start time.
        end_time (datetime.timezone): The end time.

    Returns:
        float: The duration in seconds.
    """
    duration = end_time - start_time
    return duration / datetime.timedelta(microseconds=1) / 1e6


def copy_images(work_directory, lion_images, no_lion_images):
    """
    Copy images to work directory.
    """
    print(
        "Copying images to working directory "
        + os.path.realpath(work_directory)
    )
    for image in lion_images:
        shutil.copy(image, f"{work_directory}/lion")
    for image in no_lion_images:
        shutil.copy(image, f"{work_directory}/no_lion")
    print("Copied all images")


def organize_data(
    presets: Preset, work_directory: str, validation_directory: str
):
    """
    Organizes the data and splits it into training and validation datasets.
    """
    logger.debug(
        "organizing training data, work directory is %s, "
        + "validation directory is %s",
        work_directory,
        validation_directory,
    )

    logger.debug("lion images in    %s", presets.lion_directories)
    logger.debug("no-lion images in %s", presets.no_lion_directories)
    lion_images = []
    for lion in presets.lion_directories:
        lion_images += glob.glob(os.path.join(lion, "*"))
    no_lion_images = []
    for no_lion in presets.no_lion_directories:
        no_lion_images += glob.glob(os.path.join(no_lion, "*"))

    print(f"Found {len(lion_images)} images tagged as `lion`")
    print(f"Found {len(no_lion_images)} images tagged as `no-lion`")
    print(f"In total {len(lion_images) + len(no_lion_images)} images")

    shutil.rmtree(work_directory, ignore_errors=True)
    os.makedirs(f"{work_directory}/lion")
    os.makedirs(f"{work_directory}/no_lion")

    copy_images(
        work_directory=work_directory,
        lion_images=lion_images,
        no_lion_images=no_lion_images,
    )

    if (
        len(presets.validation_lion_directories) == 0
        and len(presets.validation_no_lion_directories) == 0
    ):
        return

    logger.debug(
        "validation lion images in    %s", presets.validation_lion_directories
    )
    logger.debug(
        "validation no-lion images in %s",
        presets.validation_no_lion_directories,
    )
    lion_images = []
    for lion in presets.validation_lion_directories:
        lion_images += glob.glob(os.path.join(lion, "*"))
    no_lion_images = []
    for no_lion in presets.validation_no_lion_directories:
        no_lion_images += glob.glob(os.path.join(no_lion, "*"))

    print(f"Found {len(lion_images)} images tagged as `lion`")
    print(f"Found {len(no_lion_images)} images tagged as `no-lion`")
    print(f"In total {len(lion_images) + len(no_lion_images)} images")

    shutil.rmtree(validation_directory, ignore_errors=True)
    os.makedirs(f"{validation_directory}/lion")
    os.makedirs(f"{validation_directory}/no_lion")

    copy_images(
        work_directory=validation_directory,
        lion_images=lion_images,
        no_lion_images=no_lion_images,
    )


def image_augmentation(image, with_augmentation: bool, augmentation_layers):
    """
    Use augmentation if `with_augmentation` is set to True
    """
    if with_augmentation:
        for layer in augmentation_layers:
            image = layer(image)
    return image


def create_datasets(
    presets: Preset,
    training_directory: str,
    validation_directory: str,
    color_mode: str,
):
    """
    Create the training and validation datasets.
    """
    # Define augmentation layers which are used in some of the runs
    augmentation_layers = [
        keras.layers.RandomFlip("horizontal"),
        keras.layers.RandomRotation(0.01),
        keras.layers.RandomZoom(0.05),
        keras.layers.RandomBrightness((-0.1, 0.1)),
        keras.layers.RandomContrast(0.1),
        # keras.layers.RandomCrop(200, 200),
        # keras.layers.Rescaling(1./255),
    ]

    with_validation_split = (
        len(presets.validation_lion_directories) == 0
        and len(presets.validation_no_lion_directories) == 0
    )

    # Create datasets(training, validation)
    datasets = keras.preprocessing.image_dataset_from_directory(
        training_directory,
        batch_size=presets.batch_size,
        validation_split=(0.2 if with_validation_split else None),
        subset=("both" if with_validation_split else None),
        # Seed is always the same in order to ensure that we can reproduce
        # the same training session
        seed=123,
        shuffle=True,
        image_size=presets.image_dimensions,
        color_mode=color_mode,
    )

    if with_validation_split:
        training_dataset = datasets[0]
        validation_dataset = datasets[1]
    else:
        training_dataset = datasets
        validation_dataset = keras.preprocessing.image_dataset_from_directory(
            validation_directory,
            batch_size=presets.batch_size,
            seed=123,
            shuffle=True,
            image_size=presets.image_dimensions,
            color_mode=color_mode,
        )

    training_dataset = training_dataset.map(
        lambda img, label: (
            image_augmentation(
                image=img,
                with_augmentation=presets.with_augmentation,
                augmentation_layers=augmentation_layers,
            ),
            label,
        ),
        num_parallel_calls=tf.data.AUTOTUNE,
    )

    training_dataset = training_dataset.prefetch(tf.data.AUTOTUNE)
    validation_dataset = validation_dataset.prefetch(tf.data.AUTOTUNE)

    return training_dataset, validation_dataset


def get_md5(filepath: str) -> str:
    """
    Compute the MD5 hash for a file.
    """
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()


def get_sha256(filepath: str) -> str:
    """
    Compute the SHA-256 hash for a file.
    """
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()


def classify_image(presets: Preset, image_path: str) -> float:
    """
    Classify the image and print out the result.

    Args:
        presets (BasePreset): An instance of the BasePreset class containing
        image processing settings.

        model (keras.Model): A pre-trained Keras model used for image
        classification.

        image_path (str): The file path to the image to be classified.

    Returns:
        float: The classification result as a float value.

    Prints:
        The color mode being used, the image being classified, and the time
        taken for classification.
    """
    model_file = "model-ringtails.h5"
    logger.debug('using color_mode "%s"', presets.color_mode)
    logger.debug("classifying image %s using external model", image_path)
    logger.debug("loading model %s", model_file)

    classifier_model = keras.models.load_model(
        os.path.join(presets.base_output_directory, model_file)
    )
    feature_extractor = keras.applications.Xception(
        weights="imagenet", include_top=True
    )

    try:
        img_array = prepare_image(image_path, presets.image_dimensions)
    except Exception as e:
        logger.error("Failed to load or preprocess image: %s", e)
        raise

    start_time = datetime.datetime.now()

    # Extract features using Xception
    features = feature_extractor.predict(img_array)

    # Predict with the trained classifier
    prediction = classifier_model.predict(features)

    end_time = datetime.datetime.now()
    logger.debug(
        "Classification took %.2f seconds", get_duration(start_time, end_time)
    )

    # Adjusted: Assuming index 0 is 'lion'
    lion_probability = float(prediction[0][0])
    logger.debug("predicted lion probability %.2f", lion_probability)

    return lion_probability


def print_bash_completion(command: str, shell: str):
    """
    Print bash completion script.
    """
    command_string = ""
    if command is not None:
        command_string = f"{command}-"
    shell_suffix = ""
    if shell == "bash":
        shell_suffix = "sh"
    else:
        raise ValueError(f"unknown shell {shell}")
    completions_file = os.path.join(
        os.path.dirname(__file__),
        "completions",
        f"pumaguard-{command_string}completions.{shell_suffix}",
    )
    with open(completions_file, encoding="utf-8") as fd:
        print(fd.read())


def prepare_image(img_path: str, image_dimensions: Tuple[int, int]):
    """
    Prepare the image.
    """
    img = keras.preprocessing.image.load_img(
        img_path, target_size=image_dimensions
    )
    img_array = keras.preprocessing.image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = keras.applications.xception.preprocess_input(img_array)
    return img_array


def cache_model_two_stage(
    yolo_model_filename: str,
    classifier_model_filename: str,
    print_progress: bool = True,
):
    """
    Caches the model weights.
    """
    _ = ensure_model_available(classifier_model_filename, print_progress)
    _ = ensure_model_available(yolo_model_filename, print_progress)


def classify_image_two_stage(
    presets: Preset, image_path: str, print_progress: bool = True
) -> float:
    """
    Classify the image using two-stage approach: YOLO detection + EfficientNet
    classification.

    Args:
        presets (Preset): An instance of the Preset class containing settings.
        image_path (str): The file path to the image to be classified.

    Returns:
        float: Maximum puma probability from all detections (0.0 if no
        detections)
    """

    def expand_box(xyxy, crop_expand, width, height):
        x1, y1, x2, y2 = xyxy
        w, h = x2 - x1, y2 - y1
        dx, dy = w * crop_expand, h * crop_expand
        return [
            max(0, int(x1 - dx)),
            max(0, int(y1 - dy)),
            min(width - 1, int(x2 + dx)),
            min(height - 1, int(y2 + dy)),
        ]

    def prob_puma_from_crop(pil_img):
        arr = keras.utils.img_to_array(
            pil_img.resize((image_size, image_size))
        )
        arr = np.expand_dims(arr, 0)
        arr = keras.applications.efficientnet_v2.preprocess_input(arr)
        p = float(classifier.predict(arr, verbose=0).ravel()[0])
        return p

    logger.debug("classifying image %s using two-stage approach", image_path)

    assert presets is not None

    classifier_model_path = ensure_model_available(
        presets.classifier_model_filename,
        print_progress,
    )
    yolo_model_path = ensure_model_available(
        presets.yolo_model_filename,
        print_progress,
    )

    image_size = 384  # must match training
    iou_thresh = 0.45  # YOLO NMS IoU
    crop_expand = 0.15  # padding around detected box for crop

    classifier = get_cached_model("classifier", classifier_model_path)
    detector = get_cached_model("detector", yolo_model_path)
    best_t = 0.5

    all_rows = []
    image_summary = []

    image_file = Path(image_path)

    try:
        with PIL.Image.open(image_path) as img:
            image = img.convert("RGB")
        width, height = image.size

        res = detector.predict(
            str(image_path),
            imgsz=640,
            conf=presets.yolo_conf_thresh,
            iou=iou_thresh,
            max_det=presets.yolo_max_dets,
            verbose=False,
        )
        boxes = (
            res[0].boxes.xyxy.cpu().numpy()
            if res
            and res[0].boxes is not None
            and res[0].boxes.xyxy is not None
            else []
        )
        logger.debug("boxes:\n%s", boxes)
        logger.debug(
            "box sizes: %s",
            [
                float((x2 - x1) * (y2 - y1) / image_size / image_size)
                for _, (x1, y1, x2, y2) in enumerate(boxes)
            ],
        )

        det_probs, crops_xyxy, crops_imgs = [], [], []
        for j, (x1, y1, x2, y2) in enumerate(boxes):
            # Filter crops smaller than min_size fraction
            if (x2 - x1) * (
                y2 - y1
            ) / image_size / image_size < presets.yolo_min_size:
                logger.debug(
                    "ignoring bounding box below threshold: %s",
                    [float(x1), float(y1), float(x2), float(y2)],
                )
                continue
            x1e, y1e, x2e, y2e = expand_box(
                [x1, y1, x2, y2], crop_expand, width, height
            )
            crop = image.crop((x1e, y1e, x2e, y2e))
            p = prob_puma_from_crop(crop)
            det_probs.append(p)
            crops_xyxy.append((x1e, y1e, x2e, y2e))
            crops_imgs.append(crop)
            all_rows.append(
                {
                    "file": image_path,
                    "det_id": j,
                    "x1": x1e,
                    "y1": y1e,
                    "x2": x2e,
                    "y2": y2e,
                    "prob_puma": p,
                    "pred_label": "Puma" if p >= best_t else "Not-puma",
                }
            )
        rows = 1 + ((len(crops_imgs) + 3) // 4)

        fig = plt.figure(figsize=(max(8, min(16, 4 * 4)), max(5, 3 * rows)))

        # Original with boxes
        ax = fig.add_subplot(rows, 1, 1)
        ax.imshow(image)
        ax.axis("off")
        for p, (x1e, y1e, x2e, y2e) in zip(det_probs, crops_xyxy):
            rect = plt.Rectangle(
                (x1e, y1e),
                x2e - x1e,
                y2e - y1e,
                fill=False,
                color="lime",
                linewidth=2,
            )
            ax.add_patch(rect)
            ax.text(
                x1e,
                max(0, y1e - 5),
                f"{p:.2f}",
                color="black",
                bbox={"facecolor": "lime", "alpha": 0.7, "pad": 2},
            )
        title_probs = (
            ", ".join(f"{i}:{p:.2f}" for i, p in enumerate(det_probs))
            if det_probs
            else "no detections"
        )
        ax.set_title(f"{image_path} — det_probs: {title_probs}")

        idx = 0
        for r in range(1, rows):
            for c in range(1, 5):
                if idx >= len(crops_imgs):
                    break
                axc = fig.add_subplot(rows, 4, r * 4 + c)
                axc.imshow(crops_imgs[idx])
                axc.axis("off")
                lbl = "Puma" if det_probs[idx] >= best_t else "Not-puma"
                axc.set_title(f"det {idx} — {det_probs[idx]:.3f} → {lbl}")
                idx += 1

        out_png = f"{image_file.stem}_viz.png"
        plt.tight_layout()
        plt.savefig(out_png, dpi=160)
        plt.close(fig)
    except OSError as e:
        logger.warning("Cannot open image file: %s", e)
        return 0

    logger.debug("Freeing memory")
    gc.collect()

    # Image-level summary
    if det_probs:
        image_summary.append(
            {
                "file": image_path,
                "num_dets": len(det_probs),
                "mean_prob": float(np.mean(det_probs)),
                "max_prob": float(np.max(det_probs)),
                "agg_label_mean": (
                    "Puma" if np.mean(det_probs) >= best_t else "Not-puma"
                ),
                "agg_label_max": (
                    "Puma" if np.max(det_probs) >= best_t else "Not-puma"
                ),
                "viz_path": str(out_png),
            }
        )
    else:
        image_summary.append(
            {
                "file": image_path,
                "num_dets": 0,
                "mean_prob": 0.0,
                "max_prob": 0.0,
                "agg_label_mean": "Not-puma",
                "agg_label_max": "Not-puma",
                "viz_path": str(out_png),
            }
        )

    # Write CSV outputs
    det_csv = "test_detections_predictions.csv"
    img_csv = "test_image_summary.csv"
    pandas.DataFrame(all_rows).to_csv(det_csv, index=False)
    pandas.DataFrame(image_summary).to_csv(img_csv, index=False)

    logger.debug("probabilities: %s", det_probs)
    if len(det_probs) == 0:
        logger.debug("no detections")
    return max(det_probs) if len(det_probs) > 0 else 0
