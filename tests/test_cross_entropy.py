import math
import unittest

from src.cross_entropy import (
    CrossEntropyLoss,
    _logsumexp,
    cross_entropy,
    log_softmax,
)


class TestLogSumExp(unittest.TestCase):
    def test_known_value(self):
        # log(e^2 + e^1 + e^0.1), computed by hand / reference implementation
        self.assertAlmostEqual(_logsumexp([2.0, 1.0, 0.1]), 2.4170300162778338)

    def test_large_logits_do_not_overflow(self):
        # exp(1002) overflows a float64; the max-trick must keep this finite
        result = _logsumexp([1000.0, 1001.0, 1002.0])
        self.assertTrue(math.isfinite(result))
        # shift-invariance: lse(x + c) == lse(x) + c  ->  equals lse([0, 1, 2]) + 1000
        self.assertAlmostEqual(result - 1000.0, _logsumexp([0.0, 1.0, 2.0]))


class TestLogSoftmax(unittest.TestCase):
    def test_known_values(self):
        # lse([1, 2, 3]) == 3.4076059644443806
        result = log_softmax([[1.0, 2.0, 3.0]])
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][0], -2.4076059644443806)

    def test_rows_are_log_probabilities(self):
        # exp(log_softmax) is a probability distribution: sums to 1
        for row in log_softmax([[1.0, 2.0, 3.0], [0.1, -0.4, 2.7, 0.0]]):
            self.assertAlmostEqual(sum(math.exp(x) for x in row), 1.0)