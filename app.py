"""
QuickServe Medical Clinic
BASELINE VERSION — Binary Max-Heap Priority Queue

FIX: Serve Patients page now uses in-memory queue dequeue/extract_max
     to decide WHO gets served, then passes that patient's DB id
     to serve_patient_by_id(). The custom data structure controls
     serving order — NOT SQL ORDER BY.
"""

import streamlit as st
import time
from datetime import datetime, date

import database as db
from data_structures import PatientQueue, PriorityQueue, merge_sort

st.set_page_config(page_title="QuickServe Medical Clinic", page_icon="🏥", layout="wide")
db.init_db()

def build_in_memory_queues():
    """
    Load all waiting patients from DB (raw insertion order),
    then insert into the appropriate in-memory data structure.
    The data structure — not the DB — determines serve order.
    """
    walkins = db.get_waiting_walkins()
    fifo_q  = PatientQueue()
    prio_q  = PriorityQueue()
    for w in walkins:
        if w["is_priority"]:
            prio_q.insert(w)   # Binary Heap insert — O(log n)
        else:
            fifo_q.enqueue(w)  # FIFO enqueue — O(1)
    return fifo_q, prio_q

URGENCY = {
    "Normal":   (1, False),
    "Moderate": (2, True),
    "Urgent":   (3, True),
    "Critical": (4, True),
}
URGENCY_COLORS = {
    "Normal": "🟢", "Moderate": "🟡", "Urgent": "🟠", "Critical": "🔴"
}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/hospital.png", width=80)
    st.title("QuickServe Clinic")
    st.caption("Smart Appointment & Queue System")
    st.caption("📌 Baseline — Binary Heap Priority Queue")
    st.divider()
    page = st.radio("Navigate", [
        "📊 Dashboard", "📅 Book Appointment", "🚶 Walk-in Registration",
        "🏥 Serve Patients", "📋 Appointments List", "📜 Served Log"
    ], label_visibility="collapsed")
    st.divider()
    stats = db.get_stats()
    st.metric("⏳ Waiting",           stats["waiting"])
    st.metric("✅ Served Today",       stats["served_today"])
    st.metric("📅 Scheduled Appts",   stats["appointments_scheduled"])
    st.metric("🚨 Priority Waiting",  stats["priority_waiting"])

# ── Dashboard ──────────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    st.title("🏥 QuickServe Medical Clinic")
    st.subheader("Smart Appointment & Queue Management Dashboard")
    st.caption(f"🕐 {datetime.now().strftime('%A, %B %d %Y  |  %I:%M %p')}")
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⏳ Patients Waiting",       stats["waiting"])
    c2.metric("✅ Served Today",           stats["served_today"])
    c3.metric("📅 Scheduled Appointments", stats["appointments_scheduled"])
    c4.metric("🚨 Priority Queue",         stats["priority_waiting"])
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("🚶 Walk-in Queue (FIFO)")
        walkins = db.get_waiting_walkins()
        fifo_patients = [w for w in walkins if not w["is_priority"]]
        if fifo_patients:
            for p in fifo_patients:
                st.info(f"**Q{p['queue_number']}** — {p['patient_name']}  🟢 Normal")
        else:
            st.success("Queue is empty.")
    with col_r:
        st.subheader("🚨 Priority Queue (Binary Heap)")
        _, prio_q = build_in_memory_queues()
        prio_sorted = prio_q.all_patients()
        if prio_sorted:
            for p in prio_sorted:
                icon = URGENCY_COLORS.get(p["urgency_label"], "🟠")
                st.warning(f"**Q{p['queue_number']}** — {p['patient_name']}  {icon} {p['urgency_label']}")
        else:
            st.success("Priority queue is empty.")
    st.divider()
    st.subheader("📅 Today's Upcoming Appointments")
    appts = db.get_appointments(status_filter="Scheduled")
    today_str = date.today().strftime("%Y-%m-%d")
    today_appts = [a for a in appts if a["appointment_time"].startswith(today_str)]
    sorted_appts = merge_sort(today_appts, key="appointment_time")
    if sorted_appts:
        for a in sorted_appts:
            t = datetime.strptime(a["appointment_time"], "%Y-%m-%d %H:%M").strftime("%I:%M %p")
            st.info(f"🕐 **{t}** — {a['patient_name']}  |  _{a['reason'] or 'General Consultation'}_")
    else:
        st.success("No appointments scheduled for today.")

# ── Book Appointment ───────────────────────────────────────────────────────────
elif page == "📅 Book Appointment":
    st.title("📅 Book an Appointment")
    st.divider()
    with st.form("appointment_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name    = c1.text_input("Patient Name *", placeholder="Juan dela Cruz")
        contact = c2.text_input("Contact Number", placeholder="09XX-XXX-XXXX")
        c3, c4  = st.columns(2)
        appt_date = c3.date_input("Appointment Date", min_value=date.today())
        appt_time = c4.time_input("Appointment Time",
            value=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0).time())
        reason    = st.text_area("Reason / Concern")
        submitted = st.form_submit_button("📌 Confirm Appointment", use_container_width=True)
    if submitted:
        if not name.strip():
            st.error("Patient name is required.")
        else:
            appt_dt = f"{appt_date.strftime('%Y-%m-%d')} {appt_time.strftime('%H:%M')}"
            db.add_appointment(name.strip(), contact.strip(), appt_dt, reason.strip())
            st.success(f"✅ Appointment booked for **{name}** on **{appt_dt}**.")
            st.balloons()

# ── Walk-in Registration ───────────────────────────────────────────────────────
elif page == "🚶 Walk-in Registration":
    st.title("🚶 Walk-in Patient Registration")
    st.divider()
    with st.form("walkin_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name    = c1.text_input("Patient Name *", placeholder="Maria Santos")
        contact = c2.text_input("Contact Number", placeholder="09XX-XXX-XXXX")
        urgency_label = st.selectbox("Urgency Level *", list(URGENCY.keys()),
            help="Normal → FIFO | Moderate/Urgent/Critical → Binary Heap Priority Queue")
        reason  = st.text_area("Reason / Symptoms")
        submitted = st.form_submit_button("✅ Register Patient", use_container_width=True)
    if submitted:
        if not name.strip():
            st.error("Patient name is required.")
        else:
            level, is_priority = URGENCY[urgency_label]
            qnum = db.add_walkin(name.strip(), contact.strip(), level,
                                 urgency_label, reason.strip(), is_priority)
            icon = URGENCY_COLORS[urgency_label]
            queue_type = "Priority Queue (Binary Heap)" if is_priority else "FIFO Queue"
            st.success(f"✅ **{name}** registered!\n\n🎫 Queue Number: **Q{qnum}**  |  {icon} {urgency_label}  |  📋 {queue_type}")
            if is_priority:
                st.warning("⚠️ Patient placed in the **Priority Queue** due to urgency level.")

# ── Serve Patients ─────────────────────────────────────────────────────────────
elif page == "🏥 Serve Patients":
    st.title("🏥 Serve Next Patient")
    st.caption("✅ Serving order is controlled by the in-memory data structure, not SQL.")
    st.divider()

    # Build in-memory queues from DB
    fifo_q, prio_q = build_in_memory_queues()

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("🚨 Priority Queue (Binary Heap)")
        if prio_q.peek():
            next_p = prio_q.peek()
            icon = URGENCY_COLORS.get(next_p["urgency_label"], "🟠")
            st.warning(
                f"Next: **Q{next_p['queue_number']}** — {next_p['patient_name']}\n\n"
                f"{icon} **{next_p['urgency_label']}**  |  _{next_p['reason'] or '—'}_"
            )
            if st.button("➡️ Serve Priority Patient", use_container_width=True, type="primary"):
                # KEY FIX: extract_max() from Binary Heap decides who is served
                start = time.perf_counter()
                patient = prio_q.extract_max()   # O(log n) Binary Heap extract
                elapsed = time.perf_counter() - start
                if patient:
                    # Pass patient's DB id — DB just marks them served
                    served = db.serve_patient_by_id(patient["id"], is_priority=True)
                    if served:
                        st.success(
                            f"✅ Serving **{served['patient_name']}** (Q{served['queue_number']})\n\n"
                            f"⏱ Binary Heap extract_max: **{elapsed*1000:.6f} ms**"
                        )
                        st.rerun()
        else:
            st.info("Priority queue is empty.")
        st.divider()
        st.caption("All Priority Patients (heap order — highest urgency first)")
        for p in prio_q.all_patients():
            icon = URGENCY_COLORS.get(p["urgency_label"], "🟠")
            st.text(f"  Q{p['queue_number']}  {icon} {p['urgency_label']}  —  {p['patient_name']}")

    with col_r:
        st.subheader("🚶 FIFO Queue (Normal Patients)")
        if fifo_q.peek():
            next_f = fifo_q.peek()
            st.info(
                f"Next: **Q{next_f['queue_number']}** — {next_f['patient_name']}\n\n"
                f"🟢 **Normal**  |  _{next_f['reason'] or '—'}_"
            )
            if st.button("➡️ Serve Next Walk-in", use_container_width=True):
                # KEY FIX: dequeue() from FIFO Queue decides who is served
                start = time.perf_counter()
                patient = fifo_q.dequeue()       # O(1) FIFO dequeue
                elapsed = time.perf_counter() - start
                if patient:
                    served = db.serve_patient_by_id(patient["id"], is_priority=False)
                    if served:
                        st.success(
                            f"✅ Serving **{served['patient_name']}** (Q{served['queue_number']})\n\n"
                            f"⏱ FIFO dequeue: **{elapsed*1000:.6f} ms**"
                        )
                        st.rerun()
        else:
            st.info("FIFO queue is empty.")
        st.divider()
        st.caption("All FIFO Patients (arrival order)")
        for p in fifo_q.all_patients():
            st.text(f"  Q{p['queue_number']}  🟢  —  {p['patient_name']}")

    st.divider()
    st.subheader("📅 Serve Appointment Patient")
    appts = db.get_appointments(status_filter="Scheduled")
    sorted_appts = merge_sort(appts, key="appointment_time")
    if sorted_appts:
        options = {
            f"{a['patient_name']} | {a['appointment_time']} | {a['reason'] or 'General'}": a["id"]
            for a in sorted_appts
        }
        selected = st.selectbox("Select appointment to serve", list(options.keys()))
        if st.button("✅ Mark as Served", use_container_width=True):
            appt_id = options[selected]
            patient_name = selected.split("|")[0].strip()
            db.update_appointment_status(appt_id, "Served")
            with db.get_connection() as conn:
                conn.execute(
                    "INSERT INTO served_log (patient_name, patient_type, urgency_label) VALUES (?,?,?)",
                    (patient_name, "Appointment", "N/A")
                )
            st.success(f"✅ {patient_name}'s appointment marked as Served.")
            st.rerun()
    else:
        st.info("No scheduled appointments to serve.")

# ── Appointments List ──────────────────────────────────────────────────────────
elif page == "📋 Appointments List":
    st.title("📋 All Appointments")
    st.write("Sorted chronologically using **Merge Sort** algorithm.")
    st.divider()
    status_filter = st.selectbox("Filter by Status", ["All", "Scheduled", "Served", "Cancelled"])
    appts = db.get_appointments(None if status_filter == "All" else status_filter)
    sorted_appts = merge_sort(appts, key="appointment_time")
    if sorted_appts:
        for a in sorted_appts:
            status_icon = {"Scheduled": "📌", "Served": "✅", "Cancelled": "❌"}.get(a["status"], "•")
            t = datetime.strptime(a["appointment_time"], "%Y-%m-%d %H:%M").strftime("%b %d, %Y  %I:%M %p")
            with st.expander(f"{status_icon} {a['patient_name']}  |  {t}  |  {a['status']}"):
                c1, c2 = st.columns(2)
                c1.write(f"**Patient:** {a['patient_name']}")
                c1.write(f"**Contact:** {a['contact'] or '—'}")
                c2.write(f"**Date & Time:** {t}")
                c2.write(f"**Reason:** {a['reason'] or '—'}")
                if a["status"] == "Scheduled":
                    bc1, bc2 = st.columns(2)
                    if bc1.button("✅ Mark Served", key=f"srv_{a['id']}"):
                        db.update_appointment_status(a["id"], "Served")
                        st.rerun()
                    if bc2.button("❌ Cancel", key=f"cnl_{a['id']}"):
                        db.update_appointment_status(a["id"], "Cancelled")
                        st.rerun()
    else:
        st.info("No appointments found.")

# ── Served Log ─────────────────────────────────────────────────────────────────
elif page == "📜 Served Log":
    st.title("📜 Served Patients Log")
    st.divider()
    log = db.get_served_log()
    if log:
        type_colors = {"Appointment": "🔵", "Walk-in": "🟢", "Priority": "🔴"}
        for entry in log:
            icon = type_colors.get(entry["patient_type"], "•")
            t = datetime.strptime(entry["served_at"], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p")
            st.write(f"{icon} **{entry['patient_name']}**  |  {entry['patient_type']}  |  "
                     f"Urgency: {entry['urgency_label']}  |  🕐 {t}")
        st.divider()
        st.info(f"Total served: **{len(log)}** patient(s)")
    else:
        st.info("No patients served yet today.")
