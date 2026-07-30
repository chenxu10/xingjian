"""A minimal, pedagogical re-implementation of torch.nn.CrossEntropyLoss.

Mimicked (the common case):
  * input  : raw (unnormalized) logits, shape (N, C) -- plain Python lists
  * target : class indices, shape (N,)
  * reduction: "mean" (default) | "sum" | "none"

Deliberately omitted (this is for learning, not production):
  weight, ignore_index, label_smoothing, autograd, tensors/GPU.
"""

import math


def _logsumexp(row):
    """log(sum(exp(row))) via the max-subtraction trick.

    exp() of a large logit overflows, so subtract max(row) first:
    log(sum(exp(x))) == m + log(sum(exp(x - m)))  for any m.
    """
    m = max(row)
    return m + math.log(sum(math.exp(x - m) for x in row))


def log_softmax(logits):
    """Row-wise log-softmax of a 2-D list of logits, shape (N, C).

    log_softmax(x)_i = x_i - logsumexp(x)
    Working in log-space keeps every step numerically stable.
    """
    return [[x - _logsumexp(row) for x in row] for row in logits]


def cross_entropy(logits, targets, reduction="mean"):
    """Cross-entropy loss between raw logits and class-index targets.

    Mirrors torch.nn.functional.cross_entropy for the common case:
    per-sample loss is the negative log-likelihood of the true class,
        loss_i = -(log_softmax(logits_i)[target_i])
               = logsumexp(logits_i) - logits_i[target_i]
    then combined according to `reduction`.
    """
    if len(logits) == 0:
        raise ValueError("logits must be a non-empty batch")
    if len(logits) != len(targets):
        raise ValueError(
            f"batch size mismatch: {len(logits)} logit rows vs {len(targets)} targets"
        )
    losses = []
    for row, target in zip(logits, targets):
        if not 0 <= target < len(row):
            raise ValueError(
                f"target {target} out of range for {len(row)} classes"
            )
        losses.append(_logsumexp(row) - row[target])
    if reduction == "mean":
        return sum(losses) / len(losses)
    if reduction == "sum":
        return sum(losses)
    if reduction == "none":
        return losses
    raise ValueError(f"unknown reduction: {reduction!r}")


class CrossEntropyLoss:
    """Mimics torch.nn.CrossEntropyLoss: a callable loss object.

    Usage:
        loss_fn = CrossEntropyLoss(reduction="sum")
        loss = loss_fn(logits, targets)
    """

    def __init__(self, reduction="mean"):
        self.reduction = reduction

    def __call__(self, logits, targets):
        return cross_entropy(logits, targets, reduction=self.reduction)