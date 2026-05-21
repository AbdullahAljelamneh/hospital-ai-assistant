"""MCP Server exposing hospital tools.

Usage:
    python mcp_server/server.py
"""

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.hospital_tools import (
    get_department_info,
    check_appointment_availability,
    book_appointment,
    get_patient_queue_status,
    escalate_to_human,
)

mcp = FastMCP(
    "Hospital AI Assistant",
    instructions="""You are connected to a hospital management system.
    Use these tools to help patients with appointments, department info,
    queue status, and emergency escalation. Always prioritize patient safety.""",
)


@mcp.tool()
def lookup_department(department_id: str) -> dict:
    """Look up department details including phone number and current wait time.

    Args:
        department_id: Department identifier. One of: emergency, internal_medicine,
            cardiology, orthopedics, pediatrics, radiology, laboratory, pharmacy, billing
    """
    return get_department_info(department_id)


@mcp.tool()
def check_available_slots(department_id: str, date: str = None) -> dict:
    """Check available appointment slots for a department on a given date.

    Args:
        department_id: Department to check availability for
        date: Optional date in YYYY-MM-DD format. Defaults to next business day.
    """
    return check_appointment_availability(department_id, date)


@mcp.tool()
def schedule_appointment(
    department_id: str, date: str, time: str, patient_name: str
) -> dict:
    """Book a confirmed appointment for a patient.

    Args:
        department_id: Department to book with
        date: Appointment date (YYYY-MM-DD)
        time: Appointment time (HH:MM)
        patient_name: Full name of the patient
    """
    return book_appointment(department_id, date, time, patient_name)


@mcp.tool()
def check_queue(department_id: str) -> dict:
    """Check the current walk-in queue status for a department.

    Args:
        department_id: Department to check queue for
    """
    return get_patient_queue_status(department_id)


@mcp.tool()
def transfer_to_human(reason: str, urgency: str = "normal") -> dict:
    """Transfer the call to a human operator.

    MUST be used when:
    - Caller has life-threatening symptoms (urgency='critical')
    - Caller is confused or incoherent (urgency='high')
    - AI cannot determine severity (urgency='high')
    - Caller explicitly requests a human (urgency='normal')
    - Situation involves a child under 5 (urgency='high')
    - Medication error reported (urgency='high')

    Args:
        reason: Brief description of why the call is being escalated
        urgency: One of 'critical', 'high', 'normal'
    """
    return escalate_to_human(reason, urgency)


if __name__ == "__main__":
    print("Starting Hospital MCP Server...")
    mcp.run(transport="stdio")
