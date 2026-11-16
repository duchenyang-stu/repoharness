import unittest

from jobsched import Scheduler


class HiddenScheduler(unittest.TestCase):
    def test_exactly_now_is_due(self):
        s = Scheduler()
        s.add("a", 10)
        self.assertEqual(s.pop_due(10), ["a"])
        self.assertEqual(len(s), 0)

    def test_higher_priority_first_at_same_time(self):
        s = Scheduler()
        s.add("low", 10, priority=1)
        s.add("high", 10, priority=5)
        s.add("mid", 10, priority=3)
        self.assertEqual(s.pop_due(10), ["high", "mid", "low"])

    def test_fifo_when_time_and_priority_equal(self):
        s = Scheduler()
        for name in ["zeta", "alpha", "mike"]:
            s.add(name, 10, priority=2)
        self.assertEqual(s.pop_due(10), ["zeta", "alpha", "mike"])

    def test_time_beats_priority(self):
        s = Scheduler()
        s.add("urgent-but-late", 20, priority=99)
        s.add("early", 10, priority=0)
        self.assertEqual(s.pop_due(30), ["early", "urgent-but-late"])

    def test_duplicate_names_are_independent(self):
        s = Scheduler()
        s.add("job", 10)
        s.add("job", 12)
        self.assertEqual(s.pop_due(11), ["job"])
        self.assertEqual(len(s), 1)
        self.assertEqual(s.peek_time(), 12)

    def test_partial_pop_leaves_rest(self):
        s = Scheduler()
        s.add("a", 5)
        s.add("b", 15)
        self.assertEqual(s.pop_due(10), ["a"])
        self.assertEqual(s.pop_due(15), ["b"])


if __name__ == "__main__":
    unittest.main()
