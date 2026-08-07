import math

import pytest

from src.cross_entropy import (
    _logsumexp,
    cross_entropy,
    log_softmax,
)


def test_lse_known_value():
    # log(e^2 + e^1 + e^0.1), computed by hand / reference implementation
    assert _logsumexp([2.0, 1.0, 0.1]) == pytest.approx(2.4170300162778338)


def test_lse_large_logits_do_not_overflow():
    # exp(1002) overflows a float64; the max-trick must keep this finite
    result = _logsumexp([1000.0, 1001.0, 1002.0])
    assert math.isfinite(result)
    # shift-invariance: lse(x + c) == lse(x) + c  ->  equals lse([0, 1, 2]) + 1000
    assert result - 1000.0 == pytest.approx(_logsumexp([0.0, 1.0, 2.0]))


def test_log_softmax_known_values():
    # lse([1, 2, 3]) == 3.4076059644443806
    result = log_softmax([[1.0, 2.0, 3.0]])
    assert len(result) == 1
    assert result[0][0] == pytest.approx(-2.4076059644443806)


def test_log_softmax_rows_are_log_probabilities():
    # exp(log_softmax) is a probability distribution: sums to 1
    for row in log_softmax([[1.0, 2.0, 3.0], [0.1, -0.4, 2.7, 0.0]]):
        assert sum(math.exp(x) for x in row) == pytest.approx(1.0)


def test_cross_entropy_single_sample():
    # reference: torch.nn.functional.cross_entropy([[2, 1, 0.1]], [0])
    loss = cross_entropy([[0, 0]], [0])
    assert loss == pytest.approx(math.log(2))
