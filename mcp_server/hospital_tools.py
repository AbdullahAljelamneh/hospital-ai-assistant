"""Hospital tool implementations.

These simulate a real hospital backend. In production, these would
call actual hospital APIs / databases.
"""

from datetime import datetime, timedelta
import random


DEPARTMENTS = {
    "emergency": {
        "name": "Emergency Department",
        "phone": "+962-6-555-0100",
        "wait_time_min": 15,
    },
    "internal_medicine": {
        "name": "Internal Medicine",
        "phone": "+962-6-555-0200",
        "wait_time_min": 45,
    },
    "cardiology": {
        "name": "Cardiology",
        "phone": "+962-6-555-0300",
        "wait_time_min": 30,
    },
    "orthopedics": {
        "name": "Orthopedics",
        "phone": "+962-6-555-0400",
        "wait_time_min": 60,
    },
    "pediatrics": {
        "name": "Pediatrics",
        "phone": "+962-6-555-0500",
        "wait_time_min": 25,
    },
    "radiology": {"name": "Radiology", "phone": "+962-6-555-0600", "wait_time_min": 40},
    "laboratory": {
        "name": "Laboratory",
        "phone": "+962-6-555-0700",
        "wait_time_min": 20,
    },
    "pharmacy": {"name": "Pharmacy", "phone": "+962-6-555-0800", "wait_time_min": 10},
    "billing": {
        "name": "Billing & Insurance",
        "phone": "+962-6-555-0900",
        "wait_time_min": 35,
    },
}


def get_department_info(department_id: str) -> dict:
    """Look up department details including current wait time."""
    dept = DEPARTMENTS.get(department_id.lower())
    if not dept:
        return {
            "error": f"Department '{department_id}' not found. Available: {', '.join(DEPARTMENTS.keys())}"
        }

    current_wait = dept["wait_time_min"] + random.randint(-10, 20)
    current_wait = max(5, current_wait)

    return {
        "department": dept["name"],
        "phone": dept["phone"],
        "estimated_wait_minutes": current_wait,
        "status": "open" if 7 <= datetime.now().hour <= 21 else "closed",
    }


def check_appointment_availability(department_id: str, date: str = None) -> dict:
    """Check available appointment slots for a department."""
    dept = DEPARTMENTS.get(department_id.lower())
    if not dept:
        return {"error": f"Department '{department_id}' not found."}

    if date is None:
        target = datetime.now() + timedelta(days=1)
        while target.weekday() in (4, 5):
            target += timedelta(days=1)
        date = target.strftime("%Y-%m-%d")

    slots = []
    for hour in [8, 9, 10, 11, 13, 14, 15]:
        if random.random() > 0.4:
            slots.append(f"{hour:02d}:00")
        if random.random() > 0.5:
            slots.append(f"{hour:02d}:30")

    return {
        "department": dept["name"],
        "date": date,
        "available_slots": slots,
        "note": "Slots are 30 minutes each. New patients need a GP referral.",
    }


def book_appointment(
    department_id: str, date: str, time: str, patient_name: str
) -> dict:
    """Book an appointment slot."""
    dept = DEPARTMENTS.get(department_id.lower())
    if not dept:
        return {"error": f"Department '{department_id}' not found."}

    confirmation_id = f"APT-{random.randint(10000, 99999)}"

    return {
        "status": "confirmed",
        "confirmation_id": confirmation_id,
        "department": dept["name"],
        "date": date,
        "time": time,
        "patient_name": patient_name,
        "reminder": "You will receive an SMS reminder 24 hours before your appointment.",
        "cancellation_policy": "Cancel at least 24 hours in advance to avoid a 50 JOD fee.",
    }


def get_patient_queue_status(department_id: str) -> dict:
    """Check current queue status for walk-in patients."""
    dept = DEPARTMENTS.get(department_id.lower())
    if not dept:
        return {"error": f"Department '{department_id}' not found."}

    patients_waiting = random.randint(2, 15)
    avg_wait = dept["wait_time_min"]

    return {
        "department": dept["name"],
        "patients_in_queue": patients_waiting,
        "estimated_wait_minutes": patients_waiting * (avg_wait // 3),
        "recommendation": "Consider booking an appointment to avoid waiting."
        if patients_waiting > 8
        else "Walk-in wait time is reasonable.",
    }


def escalate_to_human(reason: str, urgency: str = "normal") -> dict:
    """Transfer the call to a human operator."""
    transfer_targets = {
        "critical": {
            "line": "Emergency Operator",
            "phone": "+962-6-555-0100",
            "priority": "IMMEDIATE",
        },
        "high": {
            "line": "Senior Operator",
            "phone": "+962-6-555-1000",
            "priority": "NEXT AVAILABLE",
        },
        "normal": {
            "line": "General Operator",
            "phone": "+962-6-555-1001",
            "priority": "QUEUE",
        },
    }

    target = transfer_targets.get(urgency, transfer_targets["normal"])

    return {
        "status": "transferring",
        "transfer_to": target["line"],
        "phone": target["phone"],
        "priority": target["priority"],
        "reason_logged": reason,
        "message": "Please hold while I transfer you to a human operator.",
    }
