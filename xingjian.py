#!/usr/bin/env python3
"""
Xingjian: assertion watcher.

Run this in a terminal while you edit. On every save of a .py file it executes
that file so its top-level `assert` statements are checked:

    all pass -> git add -A && git commit      (green: keep the work)
    any fail -> git reset --hard HEAD         (red: DELETE the change)

The revert is the point: failing work is destroyed, forcing tiny steps.
Ctrl-C to stop. No dependencies, no editor extensions.

    python xingjian.py              # foreground
    python xingjian.py --detach     # background; logs to .xingjian.log
    python xingjian.py --stop       # stop the background watcher
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

IGNORE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
POLL_SECONDS = 0.5
SETTLE_SECONDS = 0.8
RUN_TIMEOUT = 15.0
COMMIT_MESSAGE = "xingjian: working %H:%M:%S"
PID_FILE = Path(".xingjian.pid")
LOG_FILE = Path(".xingjian.log")


def is_ignored(path: Path) -> bool:
    """True if any path component (e.g. __pycache__) is on the ignore list."""
    return any(part in IGNORE_DIRS for part in path.parts)


def mtime_or_none(path: Path) -> int | None:
    """Modification time in ns, or None if the file vanished before we could stat it."""
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def snapshot(root: Path) -> dict:
    """Map of every watched .py file -> mtime, so edits/creations/deletions all show up."""
    modification_times = {}
    for path in root.rglob("*.py"):
        if not is_ignored(path):
            mtime = mtime_or_none(path)
            if mtime is not None:
                modification_times[path] = mtime
    return modification_times


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
    print("   back to last green commit. take a smaller step!")


def xingjian_cycle(changed_files):
    print("\n--- save detected, scanning assertions ---")
    for path in changed_files:
        if run_file(path) != 0:
            print(f"❌ red ({path.name} failed an assertion) → REVERTING your change")
            revert_red()
            return
    commit_green(time.strftime(COMMIT_MESSAGE))


def detect_changed(before, after, self_path):
    """Return saved non-test .py files that are new or modified in `after`."""
    changed = []
    for path in after:
        is_changed = before.get(path) != after[path]  # new or modified
        was_deleted = not path.exists()                # deleted during the save burst
        is_test = is_test_file(path)                   # suite covers test files
        is_watcher = path.resolve() == self_path      # never execute the watcher itself
        if is_changed and not was_deleted and not is_test and not is_watcher:
            changed.append(path)
    return changed


def wait_until_settled(after):
    """Poll until the workspace stops changing; return the final snapshot."""
    settled = snapshot(Path.cwd())
    while settled != after:
        time.sleep(SETTLE_SECONDS)
        after = settled
        settled = snapshot(Path.cwd())
    return settled


def running_pid():
    """Pid of a live background watcher, or None."""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)  # signal 0: existence check only
    except (ValueError, OSError):
        return None
    return pid


def detach():
    """Fork into the background. Parent returns the child pid; child returns 0."""
    if not hasattr(os, "fork"):
        fail("--detach needs a Unix-like OS (fork unavailable)")
    pid = running_pid()
    if pid:
        fail(f"already running in background (pid {pid}); stop with: python xingjian.py --stop")
    sys.stdout.flush()  # flush BEFORE fork so the child doesn't re-emit buffered lines
    sys.stderr.flush()
    pid = os.fork()
    if pid > 0:
        return pid  # parent: report and exit, freeing the terminal
    # child: become session leader, drop the terminal, log to file
    os.setsid()
    log = open(LOG_FILE, "a", buffering=1)  # line-buffered: tail -f friendly
    os.dup2(log.fileno(), sys.stdout.fileno())
    os.dup2(log.fileno(), sys.stderr.fileno())
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, sys.stdin.fileno())
    PID_FILE.write_text(str(os.getpid()))
    return 0


def stop_daemon():
    pid = running_pid()
    if pid is None:
        PID_FILE.unlink(missing_ok=True)
        fail("no background xingjian.py is running")
    os.kill(pid, signal.SIGTERM)
    PID_FILE.unlink(missing_ok=True)
    print(f"xingjian: stopped background watcher (pid {pid})")


def remove_pid_and_exit(signum, frame):
    PID_FILE.unlink(missing_ok=True)
    sys.exit(0)


def parse_args():
    """Build the CLI parser and return the parsed arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--detach",
        action="store_true",
        help=f"run in the background, logging verdicts to {LOG_FILE}",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="stop a background xingjian.py started with --detach",
    )
    return parser.parse_args()


def handle_stop_or_running_daemon(args):
    """ Honour --stop and refuse to start a second daemon. Returns when the
        caller may proceed to start watching."""
    if args.stop:
        stop_daemon()
        sys.exit(0)
    pid = running_pid()
    if pid:
        fail(f"a background xingjian.py is already running (pid {pid}); "
             "stop it first: python xingjian.py --stop")


def main():
    args = parse_args()
    handle_stop_or_running_daemon(args)

    check_preconditions()

    if args.detach:
        pid = detach()
        if pid > 0:
            print(f"xingjian: running in background (pid {pid}) — terminal is yours")
            print(f"xingjian: watch verdicts → tail -f {LOG_FILE}")
            print(f"xingjian: stop           → python xingjian.py --stop")
            return
        # daemon child falls through into the watch loop

    signal.signal(signal.SIGTERM, remove_pid_and_exit)

    self_path = Path(__file__).resolve()
    print(f"xingjian: watching **/*.py every {POLL_SECONDS}s")
    print("xingjian: GREEN → auto-commit | RED → reset --hard")
    print("xingjian: Ctrl-C to stop")

    before = snapshot(Path.cwd())
    try:
        while True:
            time.sleep(POLL_SECONDS)
            after = snapshot(Path.cwd())
            if after != before:
                after = wait_until_settled(after)
                changed = detect_changed(before, after, self_path)
                xingjian_cycle(changed)
                # absorb any changes the watcher itself made (a revert rewrites files)
                before = snapshot(Path.cwd())
    except KeyboardInterrupt:
        print("\nxingjian: stopped. your last commit is the truth.")

