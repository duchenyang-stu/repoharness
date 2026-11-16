import functools
import time


def sleep(seconds):
    time.sleep(seconds)


def retry(max_attempts=3, base_delay=0.1, max_delay=2.0, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == max_attempts - 1:
                        raise
                    sleep(min(base_delay * 2 ** attempt, max_delay))

        return wrapper

    return decorator
