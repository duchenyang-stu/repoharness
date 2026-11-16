import unittest

from netutil import retry


class RetryTests(unittest.TestCase):
    def test_returns_value_on_first_success(self):
        @retry(max_attempts=3, base_delay=0, max_delay=0)
        def ok():
            return 42

        self.assertEqual(ok(), 42)

    def test_eventually_succeeds(self):
        calls = []

        @retry(max_attempts=3, base_delay=0, max_delay=0)
        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise IOError("boom")
            return "done"

        self.assertEqual(flaky(), "done")
        self.assertEqual(len(calls), 3)

    def test_raises_after_exhausting_attempts(self):
        @retry(max_attempts=2, base_delay=0, max_delay=0)
        def bad():
            raise IOError("always")

        with self.assertRaises(IOError):
            bad()


if __name__ == "__main__":
    unittest.main()
