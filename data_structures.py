"""
QuickServe Medical Clinic - Core Data Structures & Algorithms
BASELINE VERSION

Implementations:
  - PatientQueue  : FIFO Queue using collections.deque — true O(1) enqueue/dequeue
  - PriorityQueue : Binary Max-Heap for urgent patients — O(log n) insert/extract
  - merge_sort()  : Merge Sort for appointment display — O(n log n)

Note on SQL vs Merge Sort:
  - SQL ORDER BY appointment_time is used only for data RETRIEVAL from the database.
  - Merge Sort is applied on top of the retrieved list in Python before DISPLAY.
  - The custom Merge Sort controls the final sorted order shown to the user.
"""

from collections import deque


# ── 1. FIFO Queue ──────────────────────────────────────────────────────────────

class PatientQueue:
    """
    FIFO Queue for normal walk-in patients.
    Uses collections.deque for true O(1) enqueue and dequeue.

    Why deque instead of list:
      - list.pop(0) is O(n) — it shifts all remaining elements left
      - deque.popleft() is O(1) — implemented as a doubly-linked list internally
      - For a patient queue, O(1) dequeue is required for correctness
    """

    def __init__(self):
        self._items = deque()

    def enqueue(self, patient):
        """O(1) — append to right end of deque."""
        self._items.append(patient)

    def dequeue(self):
        """O(1) — remove from left end of deque (true O(1), unlike list.pop(0))."""
        if self.is_empty():
            return None
        return self._items.popleft()

    def peek(self):
        """O(1) — view front patient without removing."""
        return self._items[0] if self._items else None

    def is_empty(self):
        return len(self._items) == 0

    def size(self):
        return len(self._items)

    def all_patients(self):
        return list(self._items)


# ── 2. Binary Max-Heap Priority Queue ─────────────────────────────────────────

class PriorityQueue:
    """
    BASELINE: Binary Max-Heap Priority Queue for urgent patients.
    Higher urgency_level = higher priority.
    O(log n) insert and extract_max.
    """

    def __init__(self):
        self._heap = []

    def _parent(self, i): return (i - 1) // 2
    def _left(self, i):   return 2 * i + 1
    def _right(self, i):  return 2 * i + 2

    def _swap(self, i, j):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _heapify_up(self, i):
        """Bubble up after insert — O(log n)"""
        while i > 0:
            p = self._parent(i)
            if self._heap[i]["urgency_level"] > self._heap[p]["urgency_level"]:
                self._swap(i, p)
                i = p
            else:
                break

    def _heapify_down(self, i):
        """Trickle down after extract — O(log n)"""
        n = len(self._heap)
        while True:
            largest = i
            l, r = self._left(i), self._right(i)
            if l < n and self._heap[l]["urgency_level"] > self._heap[largest]["urgency_level"]:
                largest = l
            if r < n and self._heap[r]["urgency_level"] > self._heap[largest]["urgency_level"]:
                largest = r
            if largest != i:
                self._swap(i, largest)
                i = largest
            else:
                break

    def insert(self, patient):
        """O(log n) — append then heapify_up."""
        self._heap.append(patient)
        self._heapify_up(len(self._heap) - 1)

    def extract_max(self):
        """O(log n) — remove root, move last to root, heapify_down."""
        if self.is_empty():
            return None
        if len(self._heap) == 1:
            return self._heap.pop()
        root = self._heap[0]
        self._heap[0] = self._heap.pop()
        self._heapify_down(0)
        return root

    def peek(self):
        return self._heap[0] if self._heap else None

    def is_empty(self):
        return len(self._heap) == 0

    def size(self):
        return len(self._heap)

    def all_patients(self):
        return sorted(self._heap, key=lambda p: p["urgency_level"], reverse=True)


# ── 3. Merge Sort ──────────────────────────────────────────────────────────────

def merge_sort(appointments, key="appointment_time"):
    """
    Stable O(n log n) Merge Sort.

    Role in the system:
      - SQL retrieves appointments from the database (basic storage retrieval).
      - merge_sort() is then applied in Python to produce the final sorted order
        displayed to the user. The custom algorithm controls display ordering,
        not the database.
    """
    if len(appointments) <= 1:
        return appointments
    mid = len(appointments) // 2
    left  = merge_sort(appointments[:mid], key)
    right = merge_sort(appointments[mid:], key)
    return _merge(left, right, key)


def _merge(left, right, key):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i][key] <= right[j][key]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
