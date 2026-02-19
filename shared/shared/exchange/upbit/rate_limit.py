import time

class SimpleRateLimiter:
    def __init__(self, min_interval_sec: float = 0.12):
        self.min_interval = min_interval_sec
        self._last = 0.0

    def wait(self):
        now = time.time()
        dt = now - self._last
        if dt < self.min_interval:
            time.sleep(self.min_interval - dt)
        self._last = time.time()
