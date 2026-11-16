import unittest

from jobsched import Scheduler


class SchedulerTests(unittest.TestCase):
    def test_orders_by_time(self):
        s = Scheduler()
        s.add("late", 20)
        s.add("early", 10)
        self.assertEqual(s.pop_due(100), ["early", "late"])

    def test_not_due_yet(self):
        s = Scheduler()
        s.add("future", 50)
        self.assertEqual(s.pop_due(10), [])
        self.assertEqual(len(s), 1)

    def test_peek(self):
        s = Scheduler()
        self.assertIsNone(s.peek_time())
        s.add("a", 5)
        self.assertEqual(s.peek_time(), 5)


if __name__ == "__main__":
    unittest.main()
