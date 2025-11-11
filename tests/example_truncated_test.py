#!/usr/bin/env python3
"""
Example demonstrating truncated image handling.
This is a standalone demonstration, not part of the test suite.
"""

import io
import os
import tempfile
import time

from PIL import (
    Image,
)


def create_complete_image(filepath):
    """Create a complete JPEG image."""
    img = Image.new("RGB", (100, 100), color="green")
    img.save(filepath, format="JPEG")
    print(f"✓ Created complete image: {filepath}")


def create_truncated_image(filepath):
    """Create a truncated JPEG image."""
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    full_data = img_bytes.getvalue()

    # Write only 30% of the image
    truncated_data = full_data[: len(full_data) // 3]
    with open(filepath, "wb") as f:
        f.write(truncated_data)
    print(
        f"✗ Created truncated image: {filepath} "
        + f"({len(truncated_data)} of {len(full_data)} bytes)"
    )


def try_open_image(filepath):
    """Try to open an image and report the result."""
    try:
        with Image.open(filepath) as img:
            img.convert("RGB")
        print(f"  ✓ Successfully opened: {filepath}")
        return True
    except OSError as e:
        print(f"  ✗ Failed to open: {e}")
        return False
    except Exception as e:  #  pylint: disable=broad-exception-caught
        print(f"  ✗ Unexpected error: {type(e).__name__}: {e}")
        return False


def demonstrate_truncated_handling():
    """Demonstrate how truncated images are handled."""
    print("=" * 60)
    print("Demonstration: Handling Truncated Images")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Test 1: Complete image
        print("\n1. Complete Image Test:")
        complete_file = os.path.join(temp_dir, "complete.jpg")
        create_complete_image(complete_file)
        try_open_image(complete_file)

        # Test 2: Truncated image
        print("\n2. Truncated Image Test:")
        truncated_file = os.path.join(temp_dir, "truncated.jpg")
        create_truncated_image(truncated_file)
        try_open_image(truncated_file)

        # Test 3: Simulating file completion
        print("\n3. Simulating File Upload/Completion:")
        upload_file = os.path.join(temp_dir, "uploading.jpg")

        print("  Phase 1: Initial incomplete write")
        create_truncated_image(upload_file)
        try_open_image(upload_file)

        print("  Phase 2: Waiting...")
        time.sleep(0.1)

        print("  Phase 3: File upload completes")
        create_complete_image(upload_file)
        try_open_image(upload_file)

    print("\n" + "=" * 60)
    print("Summary:")
    print("- Complete images open successfully")
    print("- Truncated images raise OSError")
    print("- _wait_for_file_stability() retries until success or timeout")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_truncated_handling()
