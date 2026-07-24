# XingJian

> 天行健，君子以自强不息。

> **xingjian is a pathway to autodidact — for a human, and for an AI agent:**
> every change is either a *falisible* effort, **verified* step forward (tests green → committed) 
> or it is erased (tests red → reverted). Nothing unverified survives, so the
> codebase only ever moves in one direction: provably better.


## What's in this repo

| Path | What it is |
|---|---|
| `xingjian.py` | The Xingjian watcher: pure-stdlib Python, watches your saves, enforces the loop |
| `cross_entropy.py` | A minimal, pedagogical `torch.nn.CrossEntropyLoss` — built *with* this watcher (see `git log`) |
| `test_cross_entropy.py` | 16 unittest cases doubling as usage docs for the loss |

## Quick start

```bash
uv run python xingjian.py --detach     # start in background — terminal stays free
tail -f .xingjian.log                  # watch verdicts (optional)
uv run python xingjian.py --stop       # stop
```

## The loop

Every save of a `.py` file triggers the **two-stage gate**:

1. **Execute each saved non-test file** — a failing top-level `assert` is red.
   (Test files are skipped here; the suite covers them.)
2. **Run the test suite** (default: `uv run python -m unittest -v`,
   change with `--cmd "uv run pytest -q"` or `"npm test"`).

```
✅ green → committed 31dd37b: xingjian: working 08:27:29     (work is kept)
❌ red (check_bad.py failed) → REVERTING your change    (work is DELETED)
   Removing check_bad.py
   back to last green commit. take a smaller step!
```

Red means `git reset --hard HEAD` **and** `git clean -fd` — failing edits *and*
failing new files are destroyed. That is the point: the threat of losing work
is what forces genuinely small steps.

### Safety checks at startup

Refuses to start unless: inside a git repo, at least one commit exists, the
working tree is clean, and the gate passes once (baseline green). A revert can
only ever destroy the change made *after* you started watching.

### Flags

| Flag | Effect |
|---|---|
| `--detach` / `--stop` | Background mode; logs to `.xingjian.log`, pid in `.xingjian.pid` |
| `--cmd CMD` | Swap the test gate (pytest, npm, go test, ...) |
| `--run-timeout SECONDS` | Saved file that hangs → fails the gate (default 15) |
| `--no-run-changed` | Suite-only gate; don't execute saved files |
| `--keep-new` | Red resets edits but spares brand-new files (Xingjian-lite) |

## Rules to live by (the watcher enforces the rest)

- **Tiny, smaller and quicker steps.** If you can't say the change in one sentence, split it.
- **After a revert, shrink — never retry the same change.**
- **Only committed work survives.** Stray files in the repo get committed on the next green save; keep the tree intentional.
