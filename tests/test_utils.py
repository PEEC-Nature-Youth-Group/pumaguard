"""
Test utils
"""

import hashlib
import os
import tempfile
import unittest

from pumaguard.utils import (
    get_md5,
    get_sha256,
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
