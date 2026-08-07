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


class TestCrossEntropyMean(unittest.TestCase):
    def test_single_sample(self):
        # reference: torch.nn.functional.cross_entropy([[2, 1, 0.1]], [0])
        loss = cross_entropy([[0,0]], [0])
        self.assertAlmostEqual(loss, math.log(2))

class TestReductions(unittest.TestCase):
    def test_sum(self):
        logits = [[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]]
        self.assertAlmostEqual(
            cross_entropy(logits, [2, 0], reduction="sum"), 2.815211928888761
        )

    def test_none_returns_per_sample_losses(self):
        logits = [[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]]
        losses = cross_entropy(logits, [2, 0], reduction="none")
        self.assertEqual(len(losses), 2)
        self.assertAlmostEqual(losses[0], 0.4076059644443806)
        self.assertAlmostEqual(losses[1], 2.4076059644443806)

    def test_mean_is_sum_over_n(self):
        # the defining relation between reductions
        logits = [[2.0, 1.0, 0.1], [1.0, 2.0, 3.0], [0.0, 0.0, 1.0]]
        targets = [0, 2, 1]
        total = cross_entropy(logits, targets, reduction="sum")
        mean = cross_entropy(logits, targets, reduction="mean")
        self.assertAlmostEqual(mean, total / 3)


class TestValidation(unittest.TestCase):
    def test_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            cross_entropy([], [])

    def test_batch_target_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cross_entropy([[1.0, 2.0]], [0, 1])

    def test_target_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            cross_entropy([[1.0, 2.0, 3.0]], [3])
        with self.assertRaises(ValueError):
            cross_entropy([[1.0, 2.0, 3.0]], [-1])

    def test_unknown_reduction_raises(self):
        with self.assertRaises(ValueError):
            cross_entropy([[1.0, 2.0]], [0], reduction="median")


class TestCrossEntropyLossClass(unittest.TestCase):
    def test_defaults_to_mean_like_pytorch(self):
        loss_fn = CrossEntropyLoss()
        self.assertAlmostEqual(
            loss_fn([[2.0, 1.0, 0.1]], [0]), 0.41703001627783376
        )

    def test_configured_reduction_is_used(self):
        loss_fn = CrossEntropyLoss(reduction="none")
        losses = loss_fn([[1.0, 2.0, 3.0]], [2])
        self.assertEqual(losses, [0.4076059644443806])


if __name__ == "__main__":
    unittest.main()
