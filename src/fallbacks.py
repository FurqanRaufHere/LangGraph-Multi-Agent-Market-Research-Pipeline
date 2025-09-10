# src/fallbacks.py
import time
from functools import wraps

def retry_backoff(max_retries=2):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            attempts = 0
            while True:
                try:
                    return fn(*a, **kw)
                except Exception as e:
                    attempts += 1
                    if attempts > max_retries:
                        raise
                    wait = 1 * (2 ** (attempts - 1))
                    time.sleep(wait)
        return wrapper
    return deco

class CircuitBreaker:
    def __init__(self, threshold=3):
        self.threshold = threshold
        self.failures = 0

    def record_failure(self):
        self.failures += 1

    def ok(self):
        return self.failures < self.threshold
