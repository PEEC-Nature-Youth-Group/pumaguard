"""Tests for lock manager."""

# pylint: disable=protected-access
# Tests intentionally access protected members to verify internal state

import threading
import time
from unittest.mock import (
    MagicMock,
)

import pytest

from pumaguard.lock_manager import (
    _GLOBAL_LOCK,
    PumaGuardLock,
    acquire_lock,
    release,
)


def test_pumaguard_lock_initialization():
    """Test PumaGuardLock initialization."""
    mock_lock = MagicMock(spec=threading.Lock)
    lock = PumaGuardLock(mock_lock)

    assert lock._lock == mock_lock
    assert lock._acquire_started_at is None


def test_pumaguard_lock_acquire_success():
    """Test acquiring lock successfully."""
    mock_lock = MagicMock(spec=threading.Lock)
    mock_lock.acquire.return_value = True
    lock = PumaGuardLock(mock_lock)

    result = lock.acquire()

    assert result is True
    assert lock._acquire_started_at is not None
    mock_lock.acquire.assert_called_once()


def test_pumaguard_lock_acquire_failure():
    """Test acquiring lock when it fails."""
    mock_lock = MagicMock(spec=threading.Lock)
    mock_lock.acquire.return_value = False
    lock = PumaGuardLock(mock_lock)

    with pytest.raises(RuntimeError, match="Unable to acquire lock"):
        lock.acquire()

    assert lock._acquire_started_at is None


def test_pumaguard_lock_release():
    """Test releasing lock."""
    mock_lock = MagicMock(spec=threading.Lock)
    mock_lock.acquire.return_value = True
    lock = PumaGuardLock(mock_lock)

    # Acquire first
    lock.acquire()
    assert lock._acquire_started_at is not None

    # Then release
    lock.release()

    mock_lock.release.assert_called_once()
    assert lock._acquire_started_at is None


def test_pumaguard_lock_time_waited_not_acquired():
    """Test time_waited when lock not acquired."""
    mock_lock = MagicMock(spec=threading.Lock)
    lock = PumaGuardLock(mock_lock)

    waited = lock.time_waited()

    assert waited == 0.0


def test_pumaguard_lock_time_waited_acquired():
    """Test time_waited returns elapsed time since acquire."""
    mock_lock = MagicMock(spec=threading.Lock)
    mock_lock.acquire.return_value = True
    lock = PumaGuardLock(mock_lock)

    lock.acquire()
    time.sleep(0.1)  # Wait a bit
    waited = lock.time_waited()

    assert waited >= 0.1
    assert waited < 0.2  # Should be close to 0.1 seconds


def test_pumaguard_lock_time_waited_after_release():
    """Test time_waited returns 0 after release."""
    mock_lock = MagicMock(spec=threading.Lock)
    mock_lock.acquire.return_value = True
    lock = PumaGuardLock(mock_lock)

    lock.acquire()
    time.sleep(0.05)
    lock.release()

    waited = lock.time_waited()
    assert waited == 0.0


def test_release_function():
    """Test release function calls lock.release()."""
    mock_lock = MagicMock(spec=threading.Lock)
    mock_lock.acquire.return_value = True
    lock = PumaGuardLock(mock_lock)
    lock.acquire()

    release(lock)

    mock_lock.release.assert_called_once()
    assert lock._acquire_started_at is None


def test_acquire_lock_function():
    """Test acquire_lock function returns PumaGuardLock."""
    # This uses the global lock, so we can't mock it easily
    # Just verify it returns correct type
    lock = acquire_lock()

    assert isinstance(lock, PumaGuardLock)
    assert lock._lock == _GLOBAL_LOCK
    assert lock._acquire_started_at is not None

    # Clean up - release the lock
    lock.release()


def test_acquire_lock_blocks_other_threads():
    """Test that acquire_lock properly blocks other threads."""
    results = []

    def thread1():
        lock = acquire_lock()
        results.append("thread1_acquired")
        time.sleep(0.1)
        release(lock)
        results.append("thread1_released")

    def thread2():
        time.sleep(0.05)  # Start slightly after thread1
        results.append("thread2_waiting")
        lock = acquire_lock()
        results.append("thread2_acquired")
        release(lock)
        results.append("thread2_released")

    t1 = threading.Thread(target=thread1)
    t2 = threading.Thread(target=thread2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Verify proper ordering
    assert results[0] == "thread1_acquired"
    assert results[1] == "thread2_waiting"
    assert results[2] == "thread1_released"
    assert results[3] == "thread2_acquired"
    assert results[4] == "thread2_released"


def test_pumaguard_lock_multiple_acquire_release_cycles():
    """Test multiple acquire/release cycles."""
    mock_lock = MagicMock(spec=threading.Lock)
    mock_lock.acquire.return_value = True
    lock = PumaGuardLock(mock_lock)

    # First cycle
    lock.acquire()
    assert lock._acquire_started_at is not None
    first_time = lock._acquire_started_at
    lock.release()
    assert lock._acquire_started_at is None

    # Second cycle
    lock.acquire()
    assert lock._acquire_started_at is not None
    second_time = lock._acquire_started_at
    assert second_time != first_time  # Different time
    lock.release()
    assert lock._acquire_started_at is None


def test_pumaguard_lock_time_waited_precision():
    """Test time_waited provides reasonable precision."""
    mock_lock = MagicMock(spec=threading.Lock)
    mock_lock.acquire.return_value = True
    lock = PumaGuardLock(mock_lock)

    lock.acquire()

    # Measure multiple times to verify monotonic increase
    waited1 = lock.time_waited()
    time.sleep(0.01)
    waited2 = lock.time_waited()
    time.sleep(0.01)
    waited3 = lock.time_waited()

    assert waited2 > waited1
    assert waited3 > waited2

    lock.release()


def test_acquire_lock_with_real_global_lock():
    """Test acquire_lock uses the actual global lock."""
    lock1 = acquire_lock()

    # Second call should block (we test this doesn't hang)
    # We'll use a thread with timeout to verify blocking behavior
    acquired = []

    def try_acquire():
        lock2 = acquire_lock()
        acquired.append(True)
        release(lock2)

    thread = threading.Thread(target=try_acquire)
    thread.start()

    # Give thread time to try acquiring
    time.sleep(0.1)

    # Thread should still be blocked
    assert len(acquired) == 0

    # Now release first lock
    release(lock1)

    # Thread should now complete
    thread.join(timeout=1.0)
    assert len(acquired) == 1


def test_release_function_logs_debug(caplog):
    """Test release function logs debug message."""
    mock_lock = MagicMock(spec=threading.Lock)
    mock_lock.acquire.return_value = True
    lock = PumaGuardLock(mock_lock)
    lock.acquire()

    with caplog.at_level("DEBUG"):
        release(lock)

    assert "Releasing lock" in caplog.text


def test_acquire_lock_function_logs_debug(caplog):
    """Test acquire_lock function logs debug message."""
    with caplog.at_level("DEBUG"):
        lock = acquire_lock()
        release(lock)

    assert "Acquiring lock" in caplog.text
