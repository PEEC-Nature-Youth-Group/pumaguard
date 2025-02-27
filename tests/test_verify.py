"""
Unit tests for accuracy and loss functions in pumaguard.verify.
"""

import unittest

from pumaguard.verify import (
    get_accuracy,
    get_binary_accuracy,
    get_crossentropy_loss,
    get_mean_squared_error,
)


class TestVerify(unittest.TestCase):
    """
    Test verify action.
    """

    def setUp(self):
        self.predictions = [
            ('lion/SYFW0033.JPG',  0.0017, 0, ),
            ('lion/SYFW0271.JPG',  0.0436, 0, ),
            ('lion/SYFW0278.JPG',  0.0212, 0, ),
            ('lion/SYFW1932.JPG',  0.5652, 0, ),
            ('lion/SYFW5844.JPG',  0.8118, 0, ),
            ('no-lion/SYFW0022.JPG',  0.3615, 1, ),
            ('no-lion/SYFW0084.JPG',  0.8778, 1, ),
            ('no-lion/SYFW0119.JPG',  0.3408, 1, ),
            ('no-lion/SYFW0186.JPG',  0.7188, 1, ),
            ('no-lion/SYFW0197.JPG',  0.9999, 1, ),
            ('no-lion/SYFW0220.JPG',  0.9987, 1, ),
            ('no-lion/SYFW0235.JPG',  0.2738, 1, ),
            ('no-lion/SYFW0761.JPG',  0.8309, 1, ),
            ('no-lion/SYFW1915.JPG',  0.4154, 1, ),
            ('no-lion/SYFW6331.JPG',  0.6892, 1, ),
            ('no-lion/SYFW6550.JPG',  0.8819, 1, ),
        ]

    def test_get_accuracy(self):
        """
        Tests the accuracy calculation for given predictions.
        """
        self.assertAlmostEqual(get_accuracy(
            self.predictions), 0.6840755, places=6)

    def test_get_binary_accuracy(self):
        """
        Tests the binary accuracy calculation for given predictions.
        """
        self.assertAlmostEqual(get_binary_accuracy(
            self.predictions), 0.625, places=6)

    def test_get_crossentropy_loss(self):
        """
        Tests the cross-entropy loss calculation for given predictions.
        """
        loss = get_crossentropy_loss(self.predictions)
        self.assertAlmostEqual(loss, 0.4989816722098235, places=6)

    def test_get_mean_squared_error(self):
        """
        Tests the mean squared error calculation for given predictions.
        """
        mse = get_mean_squared_error(self.predictions)
        self.assertAlmostEqual(mse, 0.18283256874999995, places=6)
