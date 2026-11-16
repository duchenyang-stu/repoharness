import time


def sleep(seconds):
    time.sleep(seconds)


def retry(max_attempts=3, base_delay=0.1, max_delay=2.0, exceptions=(Exception,)):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last = exc
                    sleep(min(base_delay * attempt, max_delay))
            raise last

        return wrapper

    return decorator
