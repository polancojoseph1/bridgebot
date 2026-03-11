#!/usr/bin/env python3
"""Detached subprocess logger.

Usage: python3 subprocess_logger.py <log_path> <cmd> [args...]

Spawns <cmd> as a child, copies its stdout+stderr to <log_path>
line by line (flushed immediately), then exits with the child's return code.

Run this with start_new_session=True so it survives the parent server dying.
Because output goes to a file (not a server pipe), SIGPIPE cannot kill the CLI.
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: subprocess_logger.py <log_path> <cmd> [args...]\n")
        sys.exit(1)

    log_path = sys.argv[1]
    cmd = sys.argv[2:]

    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

    with open(log_path, "a", buffering=1) as log_file:  # line-buffered = flush after each \n
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
        for line in proc.stdout:
            decoded = line.decode(errors="replace")
            log_file.write(decoded)
        proc.wait()

    sys.exit(proc.returncode or 0)


if __name__ == "__main__":
    main()
