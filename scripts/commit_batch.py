"""Commit one batch without Co-authored-by trailers."""
from __future__ import annotations

import subprocess
import sys

GIT = r"C:\Program Files\Git\cmd\git.exe"


def run(*args: str) -> str:
    return subprocess.check_output([GIT, *args], text=True, stderr=subprocess.STDOUT).strip()


def commit_batch(paths: list[str], msg: str) -> str:
    run("add", *paths)
    tree = run("write-tree")
    parent = run("rev-parse", "HEAD")
    new = run("commit-tree", tree, "-p", parent, "-m", msg)
    run("reset", "--hard", new)
    print(f"{msg} -> {new}")
    return new


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: commit_batch.py <message> <path> [path...]", file=sys.stderr)
        sys.exit(1)
    commit_batch(sys.argv[2:], sys.argv[1])
