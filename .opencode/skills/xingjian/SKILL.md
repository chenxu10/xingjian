---
name: xingjian
description: Kent Beck's Xingjian workflow — "test && commit || revert". Use when the user says "Xingjian", "test commit revert", "test && commit || revert", or asks to work in strict tiny steps where failing tests wipe the change. Runs a loop of small edits, test runs, auto-commit on green, hard-revert on red.
---

# Xingjian — test && commit || revert

Every change is immediately tested. If the tests pass,
the change is committed. If the tests fail, the change is **reverted** — erased
back to the last green commit, not left lying around to debug. The threat of
losing work forces genuinely small steps.

Invoking this skill IS the user's explicit authorization for the git mutations
below (`git add`, `git commit`, `git reset --hard`). Confirm the preconditions
once at the start; do not re-ask every cycle.

## Preconditions — verify ALL before the first cycle

1. **Clean working tree.** Run `git status --porcelain`. If it prints anything,
   STOP. Xingjian reverts with `git reset --hard HEAD`, which destroys *all*
   uncommitted work — including the user's. Tell the user to commit or stash
   first, and wait.
2. **Warn the user.** State plainly: "Xingjian mode: any failing test run will
   permanently delete the change I just made." Proceed once they accept (their
   invocation of the skill counts as acceptance; the clean-tree check does not).
3. **Know the test command.** Detect it from the project (e.g. `pytest`,
   `npm test`, `go test ./...`, `cargo test`). If ambiguous, ask the user once
   and remember it for the session. The command must run the *whole* relevant
   suite and exit non-zero on failure.
4. **Baseline green.** Run the test command once before changing anything. If
   it fails, STOP — Xingjian requires a green baseline. Report the failure and let
   the user decide.

## The loop

Repeat until the user's task is done:

```
1. Make ONE tiny change (the smallest edit that could plausibly work)
2. Run the full test command
3. Exit 0  →  git add -A && git commit -m "<concise message>"
   Non-zero → git reset --hard HEAD
4. Report the outcome in one line, then start the next cycle
```

## Rules

- **Tiny steps only.** One behavior, one function, one branch per cycle. If you
  can't state the change in one short sentence, it's too big — split it.
- **Never weaken the gate.** Do not skip, delete, xfail, or loosen tests to make
  a cycle green. Do not commit with failing tests. Do not amend prior commits.
- **Revert means revert.** On red, run `git reset --hard HEAD` immediately —
  no "let me just peek at the diff first", no partial fixes. The diff is gone;
  that is the point.
- **After a revert, shrink — don't retry.** Never re-attempt the same change
  unchanged. Either split it into smaller pieces or pick a different approach.
  Two consecutive reverts on the same goal means your step size is wrong.
- **TDD interplay.** A new failing test would instantly revert everything, so
  keep each slice green end-to-end: add the test together with the minimal
  implementation that satisfies it, or grow test and code in alternating
  green slices.
- **Scope of commits.** Only stage and commit files belonging to this task.
  Commit messages: imperative, one line, e.g. `Add parser for header fields`.

## Stop and ask the user when

- The same goal is reverted 3 times in a row (step size or approach is wrong).
- The test command itself is broken, flaky, or slow enough to make the loop
  impractical.
- The task requires a change that cannot be decomposed into green steps
  (e.g. sweeping renames) — propose doing it outside Xingjian mode.
- Anything unexpected appears in `git status` that you did not create.

## Cycle report format

Keep the user oriented without noise — one line per cycle:

```
✅ green → committed a1b2c3d: Add parser for header fields
❌ red → reverted: attempted X; retrying as two smaller steps
```
