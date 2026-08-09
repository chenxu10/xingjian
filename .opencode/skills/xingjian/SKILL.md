---
name: xingjian
description: Use when working under an active xingjian assertion watcher or when reasoning about red/green commit discipline in this repo. Xingjian executes every saved .py file for its top-level asserts: all pass → auto-commit (GREEN), any fail → git reset --hard (RED, the change is destroyed). Distills the tool's design philosophy, the small-steps test/change/refactor loop it enforces, its alignment and misalignment with human information-processing psychology (loss aversion, operant conditioning, habit loops, Goodhart's law, gaming, risk aversion, learned helplessness), and how to avoid the misalignments while keeping the gate honest. Trigger on: xingjian, assertion watcher, top-level assert, green commit, red revert, reset --hard, small steps, tiny steps, take a smaller step, commit discipline, anti-gaming, Goodhart, don't game the gate, risk aversion, fear of the revert, self-checking asserts.
---

# Xingjian: the assertion watcher

Source of truth: `xingjian.py` in this repo. No external reading required — the
tool *is* the reference.

## What xingjian is (mechanics)

| Element | Behavior |
|---|---|
| Trigger | Any `.py` file saved under the repo (polled every 0.5s, settles 0.8s) |
| Check | The saved file is **executed** (`python file.py`, 15s timeout) so its **top-level `assert` statements** run |
| GREEN | All asserts pass → `git add -A && git commit -m "xingjian: working HH:MM:SS"` |
| RED | Any assert fails (or timeout) → `git reset --hard HEAD` — the change is **destroyed** |
| Daemon | `uv run xingjian.py --detach` (background, logs to `.xingjian.log`), `--stop` to kill; pid in `.xingjian.pid` |
| Scope | Ignores `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`; never executes itself |

The gate runs the changed file **as a program**, not as pytest. Assertions
therefore live *inside* the implementation file, at module top level —
self-checking code that verifies itself on every save.

## Design philosophy

- **The revert is the point.** Failing work is destroyed so the next step must
  be small enough to verify. Small steps are not a style preference; they are
  the *only* move that survives the mechanism.
- **Operant conditioning with maximal contingency.** 0.5s poll, instant
  verdict, no human bookkeeping. Immediate reinforcement beats delayed, every
  time.
- **Loss aversion as the engine.** Losses sting about twice as hard as gains
  (prospect theory). `reset --hard` is the strongest possible feedback a
  version-control tool can deliver — stronger than any "test failed" message.
- **The gate is only as honest as its asserts.** The asserts are simultaneously
  the target and the measure. That is Goodhart's trap: whatever the asserts
  reward, the implementer (human or agent) will learn to satisfy *that*, cheaply,
  if the asserts are weak.
- **"Your last commit is the truth."** Green commits are checkpoints that make
  exploration cheap and memory external.

## The small-steps loop: test, change, refactor

One semantic unit per save. Each save goes through xingjian; each save is
therefore a self-contained verification event.

| Step type | Save content | Expected verdict |
|---|---|---|
| **Test** | Add an assert (or pytest test) for the *next* behavior, before its implementation | RED if the assert is checked by the file and the behavior is missing; green only when the assertion is satisfiable |
| **Change** | Implementation that makes the newly asserted behavior true | GREEN — one behavior, one commit |
| **Refactor** | Behavior-preserving rewrite (rename, delegate to a library, restructure) | GREEN — the asserts are the regression net; no net-new behavior, no net-new risk |

Rules that keep the loop aligned:

1. **Assert first.** Write the assertion that pins the story's acceptance value
   (real data point, e.g. `round(ratio(4.46, 69.83), 4) == 0.0639`), then
   implement until it passes.
2. **Refactor = delegate, don't re-implement.** Prefer an existing library
   function (`numpy.percentile`, scipy, stdlib) over hand-rolled arithmetic.
   The module's top-level asserts are the safety net that makes the swap
   provably behavior-preserving. Pin the library's method explicitly
   (`method="linear"`) so the choice is not silent.
3. **RED → take a smaller step.** A red verdict is not a judgment; it is the
   tool saying "this change was too big to hold in one step." Split it.
4. **Green commit = checkpoint.** After a green, the next experiment costs
   nothing — that cheapness is the anti-risk-aversion property.

## Alignment with human information-processing psychology

| Mechanism | How xingjian aligns |
|---|---|
| **Operant conditioning** | Immediate, unambiguous, automatic contingency on every save — reinforcement/punishment within ~1s of the behavior |
| **Loss aversion (prospect theory)** | The red path converts forgetting a test into real loss; asymmetry of pain does the motivational work that willpower would |
| **Habit loop** | Cue (save) → routine (watcher runs asserts) → reward (commit or revert message). Zero willpower, zero friction: no editor plugin, no config, no ceremony |
| **Working memory limits** | Tiny steps keep the change inside working-memory span (~4 chunks); no step can exceed what one set of asserts can hold |
| **Flow / ZPD** | Step size is self-regulating: too big → red → shrink. Difficulty is forced to the edge of ability |
| **Implementation intentions** | Enforcement is automated, so the "when I save, I'll..." plan cannot be skipped in a moment of fatigue |
| **Cognitive offloading** | Git history + "your last commit is the truth" externalize memory; nothing to hold in your head |
| **Reward timing** | Every green save is an immediate, visible win (commit hash printed) — dopamine loop, not delayed praise |

## Misalignment with human information-processing psychology

| Misalignment | What happens |
|---|---|
| **Sustained punishment** | Chronic reds are stressors: cortisol degrades working memory and narrows attention. Fear-driven discipline works for a sprint, burns out as a permanent lifestyle. The tool is a scaffold, not a guard |
| **Goodhart's law** | Asserts are target and measure at once. Weak asserts (trivial checks, fudged precision, no boundary cases) get satisfied cheaply and the gate stops testing anything real — but *looks* green |
| **Loss aversion → risk aversion** | The engine that drives discipline also suppresses experimentation: every new idea is a possible revert. The result is defensive, minimal, copy-paste coding — the opposite of what exploration needs |
| **Gaming the gate** | Human or agent will, under pressure, learn to satisfy the asserts *cheaply*: `assert True`, remove honest asserts, relax precision, hardcode the expected value, disable the watcher, commit from outside the loop |
| **False-green asymmetry** | Green ≠ correct. Top-level asserts pass ≠ the logic is right and ≠ pytest passes. The auto-commit makes bad-but-passing code *permanent* in history — worse than a failing test |
| **False reds destroy trust** | Autosave/mid-edit saves can fire a red for a transient state. One arbitrary-feeling revert teaches learned helplessness and distrust of the tool → abandonment |
| **Ego threat** | Work destroyed feels like a verdict on the developer, not the step. Rejection sensitivity makes the red path more about identity than information |
| **Feedback ≠ verification** | Running top-level asserts is not running the test suite; a file can be green for xingjian and red for pytest. Two gates, two truths — know which one you just hit |

## How to avoid the misalignments (actionable)

### Keep the gate honest (anti-Goodhart)

- **Pin real acceptance values** from the story, with exact precision — not a
  fudged one (`0.0639` at 4dp, not `0.064` at 3dp). Fudging precision to make a
  number round is the first form of gaming.
- **Add property invariants** a hardcoded or table-lookup answer cannot pass:
  zero input → `0.0`; identity input → `1.0`; linearity (double the input,
  double the output); scale-invariance (`f(4.46, 69.83) == f(8.92, 139.66)`).
- **Pin the method, not just the value.** Assert a number that only the chosen
  method produces (linear-interp `q=10 → 0.244` vs nearest-rank `0.24`) so a
  silent implementation swap fails.
- **Pin degenerate inputs as behavior:** empty series → `ValueError`, not an
  invented answer; boundaries (`q=0 → min`, `q=100 → max`); single-element
  series.
- **Never remove an assert to escape red.** Deleting the check to pass the
  gate is Goodhart maximized — the commit history makes it visible, and the
  story's tests make it fail later.

### Keep the step small

- One file, one semantic unit per save. A red means "split this," not "justify
  this."
- Refactors are behavior-preserving and green from the first save — if a
  refactor is red, it wasn't a refactor.

### Keep trust in the tool

- Understand a red before blaming it: check for mid-edit autosave, check the
  settle window, check the log. A red with a cause is information; a red
  without one is trauma.
- Run the real suite (`pytest`) as the outer gate; xingjian is the inner loop.
  Both matter; neither is a substitute for the other.
- Use xingjian deliberately — as a sprint scaffold (refactor week, story push)
  — not as a permanent guard, or the punishment engine will do what sustained
  punishment always does: grind the operator down.

### The agent's working recipe

1. Verify the daemon is alive (`.xingjian.pid` exists and the process responds)
   before relying on a green commit.
2. Write the assert (real value + properties) → write the implementation →
   save **one file** → wait for the verdict in `.xingjian.log` before the next
   step.
3. After each green, confirm `git log` shows the commit; auto-commit messages
   are timestamp-only, so `git commit --amend` to carry intent ("why").
4. Test files must exit 0 when run standalone (`uv run python tests/...`) —
   xingjian executes them as programs; an import error in a test file is a
   false red.
5. Do not disable, stop, or route around the watcher to get work committed.
   If a step cannot go green honestly, it is not ready to exist yet.
