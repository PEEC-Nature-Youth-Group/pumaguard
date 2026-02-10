"""
Test basic TensorFlow functions.
"""

import logging
import os
import unittest

import tensorflow as tf  # type:ignore


class TestTensorFlow(unittest.TestCase):
    """
    Test TensorFlow.
    """

    def test_tensorflow_devices(self):
        """
        Check TensorFlow devices.
        """
        conf = tf.config.list_physical_devices("CPU")
        self.assertTrue(len(conf) > 0)

    def test_onednn_opts(self):
        """
        Test whether the TF_ONEDNN_OPTS are enabled.
        """
        logger = logging.getLogger("tests")
        onednn_opts = os.environ.get("TF_ENABLE_ONEDNN_OPTS", default="unset")
        logger.info("Option TF_ENABLE_ONEDNN_OPTS = %s", onednn_opts)
