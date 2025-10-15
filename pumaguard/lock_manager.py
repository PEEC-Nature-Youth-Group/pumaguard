"""
A simple lock manager.
"""

import logging
import threading
import time

logger = logging.getLogger("PumaGuard")

_GLOBAL_LOCK = threading.Lock()


class PumaGuardLock:
    """
    A global lock.
    """

    def __init__(self, lock: threading.Lock):
        self._lock = lock
        self._acquire_started_at: float | None = None

    def acquire(self) -> bool:
        """
        Acquire the lock. Record when the acquire attempt started so we
        can measure how long we have been waiting or have held the lock
        since the call.
        """
        self._acquire_started_at = time.monotonic()
        ok = self._lock.acquire()
        if not ok:
            self._acquire_started_at = None
            raise RuntimeError("Unable to acquire lock")
        return True

    def release(self):
        """
        Releases the lock.
        """
        self._lock.release()
        self._acquire_started_at = None

    def time_waited(self) -> float:
        """
        Return the time since acquire() was called (how long
        we've been waiting/held).
        """
        return (
            0.0
            if self._acquire_started_at is None
            else time.monotonic() - self._acquire_started_at
        )


def release(lock: PumaGuardLock):
    """
    Release the lock.
    """
    logger.debug("Releasing lock")
    lock.release()


def acquire_lock() -> PumaGuardLock:
    """
    Acquire the lock.

    This method will block until the lock is available.
    """
    logger.debug("Acquiring lock")
    lock = PumaGuardLock(_GLOBAL_LOCK)
    lock.acquire()
    return lock
