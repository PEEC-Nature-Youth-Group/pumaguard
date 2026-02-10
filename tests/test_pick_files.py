"""
Tests for the pick_files script.
"""

import os
import shutil
import tempfile
import unittest

from scripts.pick_files import (
    pick_files,
)


class TestPickFiles(unittest.TestCase):
    """
    Test the pick_files script.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.src_dirs = [tempfile.mkdtemp(dir=self.test_dir) for _ in range(3)]
        self.dest_dir = tempfile.mkdtemp(dir=self.test_dir)
        self.files = []
        for i, src_dir in enumerate(self.src_dirs):
            for j in range(5):
                file_path = os.path.join(src_dir, f"file_{i}_{j}.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"content of file {i}_{j}")
                self.files.append(file_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_pick_files(self):
        """
        Test pick_files().
        """
        num_files_to_pick = 5
        pick_files(self.src_dirs, num_files_to_pick, self.dest_dir)
        picked_files = os.listdir(self.dest_dir)
        self.assertEqual(len(picked_files), num_files_to_pick)
        for file in picked_files:
            self.assertTrue(os.path.exists(os.path.join(self.dest_dir, file)))

    def test_pick_files_with_nonexistent_directory(self):
        """
        Test pick_files() with a non-existent directory.
        """
        with self.assertRaises(FileNotFoundError):
            pick_files(self.src_dirs + ["nonexistent_dir"], 5, self.dest_dir)

    def test_pick_files_with_zero_files(self):
        """
        Test pick_files() with no files.
        """
        pick_files(self.src_dirs, 0, self.dest_dir)
        picked_files = os.listdir(self.dest_dir)
        self.assertEqual(len(picked_files), 0)


if __name__ == "__main__":
    unittest.main()
