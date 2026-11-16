import importlib
import unittest
from unittest import mock

from netutil import retry

retry_module = importlib.import_module("netutil.retry")


class HiddenRetry(unittest.TestCase):
    def failing(self, **options):
        calls = []

        @retry(**options)
        def bad():
            """doc"""
            calls.append(1)
            raise IOError("always")

        return bad, calls

    def test_delay_sequence_and_cap(self):
        bad, calls = self.failing(max_attempts=5, base_delay=1, max_delay=4)
        with mock.patch.object(retry_module, "sleep") as sleep:
            with self.assertRaises(IOError):
                bad()
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2, 4, 4])
        self.assertEqual(len(calls), 5)

    def test_no_sleep_after_final_attempt(self):
        bad, calls = self.failing(max_attempts=1, base_delay=1)
        with mock.patch.object(retry_module, "sleep") as sleep:
            with self.assertRaises(IOError):
                bad()
        sleep.assert_not_called()
        self.assertEqual(len(calls), 1)

    def test_unlisted_exception_is_not_retried(self):
        calls = []

        @retry(max_attempts=4, exceptions=(IOError,))
        def bad():
            calls.append(1)
            raise ValueError("not retryable")

        with mock.patch.object(retry_module, "sleep") as sleep:
            with self.assertRaises(ValueError):
                bad()
        self.assertEqual(len(calls), 1)
        sleep.assert_not_called()

    def test_preserves_metadata(self):
        bad, _ = self.failing(max_attempts=1)
        self.assertEqual(bad.__name__, "bad")
        self.assertEqual(bad.__doc__, "doc")

    def test_raises_last_exception(self):
        errors = iter([IOError("first"), IOError("second")])

        @retry(max_attempts=2, base_delay=0, max_delay=0)
        def bad():
            raise next(errors)

        with mock.patch.object(retry_module, "sleep"):
            with self.assertRaises(IOError) as ctx:
                bad()
        self.assertEqual(str(ctx.exception), "second")


if __name__ == "__main__":
    unittest.main()
