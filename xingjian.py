#!/usr/bin/env python3
"""
Xingjian: assertion watcher.

Run this in a terminal while you edit. On every save of a .py file it executes
that file so its top-level `assert` statements are checked:

    all pass -> git add -A && git commit      (green: keep the work)
    any fail -> git reset --hard HEAD         (red: DELETE the change)

The revert is the point: failing work is destroyed, forcing tiny steps.
Ctrl-C to stop. No dependencies, no editor extensions.

    python xingjian.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

IGNORE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
POLL_SECONDS = 0.5
SETTLE_SECONDS = 0.8
RUN_TIMEOUT = 15.0


def snapshot(root: Path) -> dict:
    """Map of every watched .py file -> mtime, so edits/creations/deletions all show up."""
    mtimes = {}
    for path in root.rglob("*.py"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        try:
            mtimes[path] = path.stat().st_mtime_ns
        except OSError:
            pass
    return mtimes


def is_test_file(path: Path) -> bool:
    name = path.name
    return name.startswith("test_") or name.endswith("_test.py")


def run_file(path: Path) -> int:
    """Execute a saved non-test file so its top-level asserts are checked."""
    print(f"xingjian: scanning assertions in {path.name} ...")
    try:
        return subprocess.run(
            [sys.executable, str(path)],
            timeout=RUN_TIMEOUT,
        ).returncode
    except subprocess.TimeoutExpired:
        print(f"xingjian: {path.name} did not exit within {RUN_TIMEOUT:g}s")
        return 124


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def fail(msg: str):
    print(f"xingjian: {msg}", file=sys.stderr)
    sys.exit(1)


def check_preconditions():
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        fail("not inside a git repository")
    if git("rev-parse", "--verify", "HEAD").returncode != 0:
        fail("no commits yet — make a baseline commit first")
    dirty = git("status", "--porcelain").stdout.strip()
    if dirty:
        fail(f"working tree must be clean (revert would destroy this):\n{dirty}")


def commit_green(message: str):
    git("add", "-A")
    result = git("commit", "-m", message)
    if result.returncode == 0:
        short = git("rev-parse", "--short", "HEAD").stdout.strip()
        print(f"✅ green → committed {short}: {message}")
    elif "nothing to commit" in result.stdout + result.stderr:
        print("✅ green — nothing new to commit")
    else:
        fail(f"git commit failed:\n{result.stderr}")


def revert_red():
    git("reset", "--hard", "HEAD")
    removed = git("clean", "-fd").stdout
    for line in removed.splitlines():
        print(f"   {line}")
    print("   back to last green commit. take a smaller step!")


def xingjian_cycle(changed_files, message: str):
    print("\n--- save detected, scanning assertions ---")
    for path in changed_files:
        if run_file(path) != 0:
            print(f"❌ red ({path.name} failed an assertion) → REVERTING your change")
            revert_red()
            return
    commit_green(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--message",
        default="xingjian: working %H:%M:%S",
        help="commit message (strftime allowed) (default: %(default)s)",
    )
    args = parser.parse_args()

    check_preconditions()

    self_path = Path(__file__).resolve()
    print(f"xingjian: watching **/*.py every {POLL_SECONDS}s")
    print("xingjian: GREEN → auto-commit | RED → reset --hard + clean -fd")
    print("xingjian: Ctrl-C to stop")

    before = snapshot(Path.cwd())
    try:
        while True:
            time.sleep(POLL_SECONDS)
            after = snapshot(Path.cwd())
            if after == before:
                continue
            # files changed — wait for the burst of saves to settle
            while True:
                time.sleep(SETTLE_SECONDS)
                settled = snapshot(Path.cwd())
                if settled == after:
                    break
                after = settled
            changed = [
                p for p in after
                if before.get(p) != after[p]   # new or modified
                and p.exists()                 # not deleted in this save burst
                and not is_test_file(p)        # assertions in non-test files
                and p.resolve() != self_path  # never execute the watcher itself
            ]
            xingjian_cycle(changed, time.strftime(args.message))
            # absorb any changes the watcher itself made (a revert rewrites files)
            before = snapshot(Path.cwd())
    except KeyboardInterrupt:
        print("\nxingjian: stopped. your last commit is the truth.")


if __name__ == "__main__":
    main()