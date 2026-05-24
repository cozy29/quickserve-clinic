"""
QuickServe Medical Clinic - SQLite Database Layer
Handles all persistence: appointments, walk-in patients, served records.

FIX: serve_patient_by_id() accepts patient_id from the in-memory queue
     so the custom data structure controls serving order, not SQL.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "quickserve.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS appointments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name    TEXT    NOT NULL,
                contact         TEXT,
                appointment_time TEXT   NOT NULL,
                reason          TEXT,
                status          TEXT    DEFAULT 'Scheduled',
                created_at      TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS walkin_queue (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                queue_number    INTEGER NOT NULL,
                patient_name    TEXT    NOT NULL,
                contact         TEXT,
                urgency_level   INTEGER DEFAULT 1,
                urgency_label   TEXT    DEFAULT 'Normal',
                reason          TEXT,
                status          TEXT    DEFAULT 'Waiting',
                is_priority     INTEGER DEFAULT 0,
                created_at      TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS served_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name    TEXT,
                patient_type    TEXT,
                urgency_label   TEXT,
                served_at       TEXT    DEFAULT (datetime('now','localtime'))
            );
        """)


# ── Queue number generator ─────────────────────────────────────────────────────

def next_queue_number():
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(queue_number) as mx FROM walkin_queue WHERE date(created_at) = date('now','localtime')"
        ).fetchone()
        return (row["mx"] or 0) + 1


# ── Appointment CRUD ───────────────────────────────────────────────────────────

def add_appointment(name, contact, appt_time, reason):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO appointments (patient_name, contact, appointment_time, reason) VALUES (?,?,?,?)",
            (name, contact, appt_time, reason)
        )
        return cur.lastrowid


def get_appointments(status_filter=None):
    """
    Retrieves appointments from the database.

    NOTE ON SQL vs MERGE SORT:
      - SQL ORDER BY appointment_time here is used only for consistent
        raw data retrieval from storage.
      - The FINAL display order shown to the user is controlled by
        merge_sort() called in app.py — the custom algorithm re-sorts
        the returned list in Python before rendering.
      - SQL handles persistence; merge_sort() handles display ordering.
    """
    with get_connection() as conn:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM appointments WHERE status=? ORDER BY appointment_time",
                (status_filter,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM appointments ORDER BY appointment_time"
            ).fetchall()
        return [dict(r) for r in rows]


def update_appointment_status(appt_id, status):
    with get_connection() as conn:
        conn.execute("UPDATE appointments SET status=? WHERE id=?", (status, appt_id))


def delete_appointment(appt_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM appointments WHERE id=?", (appt_id,))


# ── Walk-in Queue CRUD ─────────────────────────────────────────────────────────

def add_walkin(name, contact, urgency_level, urgency_label, reason, is_priority):
    qnum = next_queue_number()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO walkin_queue
               (queue_number, patient_name, contact, urgency_level, urgency_label, reason, is_priority)
               VALUES (?,?,?,?,?,?,?)""",
            (qnum, name, contact, urgency_level, urgency_label, reason, int(is_priority))
        )
        return qnum


def get_waiting_walkins():
    """
    Fetch all waiting patients from DB in raw insertion order (ORDER BY id ASC).
    The in-memory queue (PatientQueue or PriorityQueue) determines serve order,
    NOT this SQL query. SQL here only loads the data into memory.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM walkin_queue WHERE status='Waiting' ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_walkins_today():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM walkin_queue WHERE date(created_at)=date('now','localtime') ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def serve_patient_by_id(patient_id, is_priority):
    """
    Serve a specific patient by their DB id.

    DESIGN NOTE:
      The patient_id comes from the in-memory queue's dequeue() or
      extract_max() call. The custom data structure decides WHO gets
      served. This function only marks them as Served in the database
      and logs the action. The database does NOT decide serving order.

    Parameters:
        patient_id  : int  — DB id of patient to serve (from in-memory queue)
        is_priority : bool — True if from PriorityQueue, False if from PatientQueue
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM walkin_queue WHERE id=? AND status='Waiting'",
            (patient_id,)
        ).fetchone()

        if row:
            patient = dict(row)
            conn.execute(
                "UPDATE walkin_queue SET status='Served' WHERE id=?",
                (patient_id,)
            )
            conn.execute(
                "INSERT INTO served_log (patient_name, patient_type, urgency_label) VALUES (?,?,?)",
                (patient["patient_name"],
                 "Priority" if is_priority else "Walk-in",
                 patient["urgency_label"])
            )
            return patient
    return None


def get_served_log():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM served_log ORDER BY served_at DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]


def get_stats():
    with get_connection() as conn:
        waiting    = conn.execute("SELECT COUNT(*) FROM walkin_queue WHERE status='Waiting'").fetchone()[0]
        served_td  = conn.execute(
            "SELECT COUNT(*) FROM served_log WHERE date(served_at)=date('now','localtime')"
        ).fetchone()[0]
        appt_sched = conn.execute(
            "SELECT COUNT(*) FROM appointments WHERE status='Scheduled'"
        ).fetchone()[0]
        priority_w = conn.execute(
            "SELECT COUNT(*) FROM walkin_queue WHERE status='Waiting' AND is_priority=1"
        ).fetchone()[0]
    return {
        "waiting": waiting,
        "served_today": served_td,
        "appointments_scheduled": appt_sched,
        "priority_waiting": priority_w,
    }
