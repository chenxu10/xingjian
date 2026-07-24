#!/usr/bin/env python3
"""

Run this in a terminal while you edit. On every save of a .py file it:

    1. executes each saved non-test file (a failing top-level assert is RED;
       test files are skipped here — the suite below covers them)
    2. runs the gate command (default: the unittest suite)
    3. all pass  -> git add -A && git commit       (green: keep the work)
       any fails -> git reset --hard HEAD
                    git clean -fd                  (red: DELETE the change)

The revert is the point: failing work is destroyed, forcing tiny steps.
Ctrl-C to stop. No dependencies, no editor extensions.

Examples:
    python xingjian.py                                  # foreground, unittest gate
    python xingjian.py --detach                         # background; logs to .xingjian.log
    python xingjian.py --stop                           # stop the background watcher
    python xingjian.py --cmd "uv run pytest -q"         # pytest gate
    python xingjian.py --cmd "npm test"                 # any project
    python xingjian.py --keep-new                       # red resets tracked files
                                                   # but spares new untracked files
    python xingjian.py --no-run-changed                 # gate = test suite only
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
SETTLE_SECONDS = 0.8  # wait for saves to stop before running the gate
PID_FILE = Path(".xingjian.pid")
LOG_FILE = Path(".xingjian.log")


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


def run_changed_file(path: Path, timeout: float) -> int:
    """Execute a saved non-test file so its top-level asserts are checked."""
    print(f"xingjian: executing {path.name} ...")
    try:
        return subprocess.run(
            [sys.executable, str(path)],  # same interpreter/env as the watcher
            timeout=timeout or None,
        ).returncode
    except subprocess.TimeoutExpired:
        print(f"xingjian: {path.name} did not exit within {timeout:g}s")
        return 124


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def fail(msg: str):
    print(f"xingjian: {msg}", file=sys.stderr)
    sys.exit(1)


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
    # sys.stdout keeps its old block buffer across dup2 — force line buffering
    # so verdicts appear in the log in order and promptly for `tail -f`
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


def check_preconditions(cmd: str):
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        fail("not inside a git repository")
    if git("rev-parse", "--verify", "HEAD").returncode != 0:
        fail("no commits yet — make a baseline commit first")
    dirty = git("status", "--porcelain").stdout.strip()
    if dirty:
        fail(f"working tree must be clean (revert would destroy this):\n{dirty}")
    print(f"xingjian: baseline run of gate: {cmd}", flush=True)
    if subprocess.run(cmd, shell=True).returncode != 0:
        fail("baseline is RED — fix the suite before starting Xingjian")


def commit_green(message: str):
    git("add", "-A")  # -A so new files are committed too (git commit -am misses them)
    result = git("commit", "-m", message)
    if result.returncode == 0:
        short = git("rev-parse", "--short", "HEAD").stdout.strip()
        print(f"✅ green → committed {short}: {message}")
    elif "nothing to commit" in result.stdout + result.stderr:
        print("✅ green — nothing new to commit")
    else:
        fail(f"git commit failed:\n{result.stderr}")


def revert_red(keep_new: bool):
    git("reset", "--hard", "HEAD")
    if not keep_new:
        # Xingjian purity: a failing NEW file must die too, not just edits.
        removed = git("clean", "-fd").stdout
        for line in removed.splitlines():
            print(f"   {line}")
    print("   back to last green commit. take a smaller step!")


def xingjian_cycle(args, changed_files):
    print("\n--- change detected, running gate ---")
    for path in changed_files:
        if run_changed_file(path, args.run_timeout) != 0:
            print(f"❌ red ({path.name} failed) → REVERTING your change")
            revert_red(args.keep_new)
            return
    rc = subprocess.run(args.cmd, shell=True).returncode
    if rc == 0:
        commit_green(time.strftime(args.message))
    else:
        print(f"❌ red (gate exit {rc}) → REVERTING your change")
        revert_red(args.keep_new)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--cmd",
        default="uv run python -m unittest -v",
        help="gate command; must exit non-zero on failure (default: %(default)s)",
    )
    parser.add_argument(
        "--message",
        default="xingjian: working %H:%M:%S",
        help="commit message (strftime allowed) (default: %(default)s)",
    )
    parser.add_argument(
        "--keep-new",
        action="store_true",
        help="on red, reset tracked files but keep new untracked files",
    )
    parser.add_argument(
        "--no-run-changed",
        dest="run_changed",
        action="store_false",
        help="do not execute saved non-test files; gate = test suite only "
             "(default: run them, so a failing top-level assert reverts)",
    )
    parser.add_argument(
        "--run-timeout",
        type=float,
        default=15.0,
        metavar="SECONDS",
        help="max seconds a saved file may run before it fails the gate "
             "(0 = no limit) (default: %(default)s)",
    )
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
    args = parser.parse_args()

    if args.stop:
        stop_daemon()
        return
    pid = running_pid()
    if pid:
        fail(f"a background xingjian.py is already running (pid {pid}); "
             "stop it first: python xingjian.py --stop")

    check_preconditions(args.cmd)  # foreground, so failures are visible immediately
    if args.run_changed:
        print(f"xingjian: saved non-test files will be executed "
              f"(timeout {args.run_timeout:g}s); disable with --no-run-changed")

    if args.detach:
        pid = detach()
        if pid > 0:
            print(f"xingjian: running in background (pid {pid}) — terminal is yours")
            print(f"xingjian: watch verdicts → tail -f {LOG_FILE}")
            print(f"xingjian: stop           → python xingjian.py --stop")
            return
        # daemon child falls through into the watch loop

    signal.signal(signal.SIGTERM, remove_pid_and_exit)
    print(f"xingjian: watching **/*.py every {POLL_SECONDS}s")
    print("xingjian: GREEN → auto-commit everything | RED → reset --hard"
          + ("" if args.keep_new else " + clean -fd (new files deleted)"))
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
            if args.run_changed:
                self_path = Path(__file__).resolve()
                changed = [
                    p for p in after
                    if before.get(p) != after[p]  # new or modified
                    and p.exists()                # not deleted in this save burst
                    and not is_test_file(p)       # the suite covers test files
                    and p.resolve() != self_path  # never execute the watcher itself
                ]
            else:
                changed = []
            xingjian_cycle(args, changed)
            # absorb any changes the watcher itself made (a revert rewrites files)
            before = snapshot(Path.cwd())
    except KeyboardInterrupt:
        print("\nxingjian: stopped. your last commit is the truth.")


if __name__ == "__main__":
    main()
