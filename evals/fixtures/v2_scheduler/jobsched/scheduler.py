import heapq


class Scheduler:
    def __init__(self):
        self._heap = []

    def add(self, name, run_at, priority=0):
        heapq.heappush(self._heap, (run_at, priority, name))

    def pop_due(self, now):
        due = []
        while self._heap and self._heap[0][0] < now:
            due.append(heapq.heappop(self._heap)[2])
        return due

    def peek_time(self):
        return self._heap[0][0] if self._heap else None

    def __len__(self):
        return len(self._heap)
