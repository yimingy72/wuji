"""Restore lifecycle signals before replacing this process with an owned child."""

from __future__ import annotations

import os
import signal
import sys


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(64)
    ready_fd_value = os.environ.pop("WUJI_CHILD_EXEC_READY_FD", None)
    if ready_fd_value is None:
        raise SystemExit(64)
    ready_fd = int(ready_fd_value)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT, signal.SIGTERM})
    os.set_inheritable(ready_fd, False)
    os.execvpe(sys.argv[1], sys.argv[1:], os.environ)


if __name__ == "__main__":
    main()
