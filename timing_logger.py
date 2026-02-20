import time
import logging
from contextlib import contextmanager

# Captured at import time — as early as possible in the program's lifetime.
# Import this module as the very first import in main.py for accurate elapsed times.
PROGRAM_START = time.perf_counter()


@contextmanager
def log(label: str):
    """
    Context manager that times any block and logs a [TIMING] line at DEBUG level.

    Log format (grep-able):
        [TIMING] <label> | duration=X.XXXs | elapsed=X.XXXs

    Usage:
        from timing_logger import log as tlog

        with tlog("DataLoader.read_ndax('cell_001.ndax')"):
            df = read_ndax(path)
    """
    t0 = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - t0
        elapsed = time.perf_counter() - PROGRAM_START
        logging.debug(f"[TIMING] {label} | duration={duration:.3f}s | elapsed={elapsed:.3f}s")
