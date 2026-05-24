"""
QuickServe Medical Clinic - Core Data Structures & Algorithms
OPTIMIZED VERSION

Change from Baseline:
  - PriorityQueue: Binary Max-Heap O(log n) → Multi-Level Bucket Queue O(1)
    CONDITION: O(1) performance is valid because clinic urgency levels are
    fixed and limited to exactly 4 discrete values (Normal=1, Moderate=2,
    Urgent=3, Critical=4). This makes bucket-based lookup constant time.

Unchanged:
  - PatientQueue (FIFO) using collections.deque — true O(1) enqueue/dequeue
  - merge_sort() — O(n log n), controls final display order of appointments

Note on SQL vs Merge Sort:
  - SQL ORDER BY appointment_time is used only for data RETRIEVAL from the database.
  - Merge Sort is applied on top of the retrieved list in Python before DISPLAY.
  - The custom Merge Sort controls the final sorted order shown to the user.
"""

from collections import deque


# ── 1. FIFO Queue — UNCHANGED ──────────────────────────────────────────────────

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


# ── 2. Multi-Level Bucket Queue — OPTIMIZED ────────────────────────────────────

class PriorityQueue:
    """
    OPTIMIZED: Multi-Level Bucket Queue for urgent patients.

    O(1) insert and extract — VALID because:
      - Clinic urgency levels are FIXED at exactly 4 discrete values:
          1 = Normal, 2 = Moderate, 3 = Urgent, 4 = Critical
      - With fixed priority levels, a heap is unnecessary overhead.
      - Binary Heap heapify_up/down costs O(log n) for n patients.
      - Bucket Queue directly places patients into 1 of 4 fixed buckets → O(1).
      - Extraction scans exactly 4 buckets (constant) regardless of n → O(1).

    Complexity comparison (valid for fixed 4-level urgency systems):
        Operation     | Binary Heap | Bucket Queue
        insert()      | O(log n)    | O(1)
        extract_max() | O(log n)    | O(1)
        peek()        | O(1)        | O(1)
    """

    LEVELS = [4, 3, 2, 1]  # checked highest-first

    def __init__(self):
        # 4 fixed buckets — one per urgency level
        self._buckets = {4: deque(), 3: deque(), 2: deque(), 1: deque()}
        self._total = 0

    def insert(self, patient):
        """
        O(1) — directly append to the correct urgency bucket.
        No heap restructuring needed because priority levels are fixed.
        """
        level = patient.get("urgency_level", 1)
        if level not in self._buckets:
            level = 1
        self._buckets[level].append(patient)
        self._total += 1

    def extract_max(self):
        """
        O(1) — scan exactly 4 fixed buckets (constant regardless of n patients).
        Returns highest-priority patient; FIFO within same urgency level.
        """
        for level in self.LEVELS:
            if self._buckets[level]:
                self._total -= 1
                return self._buckets[level].popleft()
        return None

    def peek(self):
        """O(1) — look at next patient without removing."""
        for level in self.LEVELS:
            if self._buckets[level]:
                return self._buckets[level][0]
        return None

    def is_empty(self):
        return self._total == 0

    def size(self):
        return self._total

    def all_patients(self):
        """Return all patients ordered by urgency (highest first), FIFO within level."""
        result = []
        for level in self.LEVELS:
            result.extend(list(self._buckets[level]))
        return result


# ── 3. Merge Sort — UNCHANGED ──────────────────────────────────────────────────

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
