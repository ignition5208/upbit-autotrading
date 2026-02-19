import time
from typing import Callable, TypeVar

T = TypeVar("T")

def retry(fn: Callable[[], T], tries: int = 3, delay: float = 0.2) -> T:
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(delay * (i + 1))
    raise last  # type: ignore
