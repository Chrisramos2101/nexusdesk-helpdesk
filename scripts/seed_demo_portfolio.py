import argparse
import os
import random
import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from database.db import get_db_connection
from database.sql_helpers import is_postgres


SEED_ACTOR = "SYSTEM_DEMO_SEED_V1"
SEED_VERSION = "v1"
RANDOM_SEED = 20260822

DEMO_USERS = [
    ("demo_olivia.chen", "Olivia Chen", "IT", "admin"),
    ("demo_marcus.reed", "Marcus Reed", "IT", "admin"),
    ("demo_avery.brooks", "Avery Brooks", "Finance", "employee"),
    ("demo_maya.patel", "Maya Patel", "HR", "employee"),
    ("demo_lucas.martin", "Lucas Martin", "Operations", "employee"),
    ("demo_sofia.ramirez", "Sofia Ramirez", "Sales", "employee"),
    ("demo_ethan.walker", "Ethan Walker", "Management", "employee"),
    ("demo_nora.kim", "Nora Kim", "Finance", "employee"),
    ("demo_jordan.lee", "Jordan Lee", "HR", "employee"),
    ("demo_camila.torres", "Camila Torres", "Operations", "employee"),
    ("demo_noah.wilson", "Noah Wilson", "Sales", "employee"),
    ("demo_grace.hall", "Grace Hall", "Management", "employee"),
    ("demo_liam.scott", "Liam Scott", "IT", "employee"),
    ("demo_zoe.adams", "Zoe Adams", "Sales", "employee"),
]

ISSUES = {
    "Account Access": [
        "Account locked after password attempts",
        "New employee account provisioning request",
        "Shared drive permission request",
        "Cannot access payroll portal",
        "MFA enrollment needs to be reset",
        "Password reset link not arriving",
    ],
    "Hardware": [
        "Laptop battery drains unusually fast",
        "Docking station not detecting monitors",
        "Keyboard intermittently stops responding",
        "Laptop fan running loudly and overheating",
        "Second monitor flickers during meetings",
        "Printer is showing an offline status",
    ],
    "Software": [
        "Microsoft Teams crashes on startup",
        "Spreadsheet application freezes on large files",
        "CRM desktop client will not launch",
        "PDF editor license is not activating",
        "Required software install request",
        "Browser extension blocked by policy",
    ],
    "Network": [
        "VPN disconnects every few minutes",
        "Office Wi-Fi connection is unstable",
        "Ethernet connection has no internet access",
        "Remote desktop session times out",
        "Conference room network connection is slow",
        "Internal website only works intermittently",
    ],
    "Security": [
        "Suspicious sign-in notification received",
        "Possible phishing email reported",
        "Lost company phone needs access revoked",
        "USB device blocked by security policy",
        "Security software reports outdated definitions",
        "Unexpected MFA prompt reported",
    ],
    "Other": [
        "New hire workstation setup",
        "Conference room equipment setup request",
        "Employee offboarding technology checklist",
        "Mobile device email setup",
        "Headset replacement request",
        "General IT consultation request",
    ],
}

NOTE_TEMPLATES = [
    "Initial triage completed and the issue has been categorized.",
    "User confirmed the issue is still occurring after restart.",
    "Technician reviewed logs and reproduced the reported behavior.",
    "Requested additional details from the employee.",
    "Applied the standard troubleshooting procedure and monitored results.",
    "User confirmed normal operation after the change.",
    "Escalation was not required; issue resolved during first-line support.",
    "Follow-up scheduled to confirm the fix remains stable.",
]

ARTICLE_SLUGS = [
    "password-reset",
    "wifi-network",
    "slow-computer",
    "software-not-opening",
]


def fmt(dt: datetime) -> str:
    return dt.strftime("%m/%d/%Y %I:%M %p")


def resolution_label(delta: timedelta) -> str:
    total_minutes = max(1, int(delta.total_seconds() // 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours} hr {minutes} min"
    return f"{minutes} min"


def build_demo_plan(now: datetime | None = None) -> dict:
    now = now or datetime.now()
    rng = random.Random(RANDOM_SEED)

    employees = [u for u in DEMO_USERS if u[3] == "employee"]
    technicians = [u for u in DEMO_USERS if u[3] == "admin"]

    tickets = []
    notes = []
    audit_events = []

    categories = list(ISSUES.keys())
    priorities = ["High", "Medium", "Medium", "Medium", "Low", "Low"]

    for index in range(72):
        employee = employees[index % len(employees)]
        username, full_name, department, _ = employee

        category = categories[index % len(categories)]
        issue = ISSUES[category][(index // len(categories)) % len(ISSUES[category])]
        priority = priorities[index % len(priorities)]

        age_days = 1 + ((index * 7) % 89)
        age_hours = rng.randint(0, 20)
        submitted_at_dt = now - timedelta(days=age_days, hours=age_hours)

        if priority == "High":
            sla_delta = timedelta(hours=1)
        elif priority == "Medium":
            sla_delta = timedelta(hours=8)
        else:
            sla_delta = timedelta(hours=24)

        sla_due_dt = submitted_at_dt + sla_delta

        # Portfolio-friendly lifecycle distribution:
        # 42 closed, 18 in progress, 12 open.
        if index < 42:
            status = "Closed"
        elif index < 60:
            status = "In Progress"
        else:
            status = "Open"

        assigned_to = "Unassigned"
        completed_by = ""
        closed_at = ""
        resolution_time = ""
        sla_met = ""

        tech = technicians[index % len(technicians)][0]

        if status in {"Closed", "In Progress"}:
            assigned_to = tech

        if status == "Closed":
            # About one quarter of closed tickets intentionally breach SLA.
            if index % 4 == 0:
                close_delta = sla_delta + timedelta(
                    hours=2 + (index % 5),
                    minutes=rng.randint(5, 45),
                )
            else:
                fraction = 0.25 + ((index % 5) * 0.12)
                close_delta = timedelta(
                    seconds=max(900, int(sla_delta.total_seconds() * fraction))
                )

            closed_dt = submitted_at_dt + close_delta
            closed_at = fmt(closed_dt)
            completed_by = tech
            resolution_time = resolution_label(close_delta)
            sla_met = "Yes" if closed_dt <= sla_due_dt else "No"

        tickets.append(
            {
                "name": full_name,
                "department": department,
                "issue": issue,
                "priority": priority,
                "status": status,
                "submitted_at": fmt(submitted_at_dt),
                "closed_at": closed_at,
                "assigned_to": assigned_to,
                "completed_by": completed_by,
                "notes": "Synthetic portfolio demonstration ticket.",
                "category": category,
                "sla_due_at": fmt(sla_due_dt),
                "submitted_by": username,
                "resolution_time": resolution_time,
                "sla_met": sla_met,
                "_submitted_dt": submitted_at_dt,
            }
        )

        note_count = 1 if status == "Open" else (2 if status == "In Progress" else 3)
        for note_index in range(note_count):
            author = (
                username
                if note_index == 0
                else tech
            )
            note_time = submitted_at_dt + timedelta(
                minutes=20 + (note_index * 55) + (index % 17)
            )
            notes.append(
                {
                    "ticket_index": index,
                    "note": NOTE_TEMPLATES[
                        (index + note_index) % len(NOTE_TEMPLATES)
                    ],
                    "created_by": author,
                    "created_at": fmt(note_time),
                }
            )

        audit_events.append(
            {
                "actor": username,
                "action": "CREATE_TICKET",
                "target_type": "ticket",
                "details": "[DEMO] Synthetic portfolio ticket created",
                "created_at": fmt(submitted_at_dt),
            }
        )

        if assigned_to != "Unassigned":
            audit_events.append(
                {
                    "actor": tech,
                    "action": "ASSIGN_TICKET",
                    "target_type": "ticket",
                    "details": f"[DEMO] Assigned ticket to {tech}",
                    "created_at": fmt(submitted_at_dt + timedelta(minutes=15)),
                }
            )

        if status == "Closed":
            audit_events.append(
                {
                    "actor": tech,
                    "action": "CLOSE_TICKET",
                    "target_type": "ticket",
                    "details": f"[DEMO] Closed ticket; SLA met={sla_met}",
                    "created_at": closed_at,
                }
            )

    login_events = []
    for user_index, user in enumerate(DEMO_USERS):
        username = user[0]
        for event_index in range(16):
            days_ago = 2 + ((user_index * 5 + event_index * 3) % 84)
            event_dt = now - timedelta(
                days=days_ago,
                hours=(user_index + event_index) % 11,
            )
            login_events.append(
                {
                    "username": username,
                    "event_type": "login" if event_index % 2 == 0 else "logout",
                    "event_time": fmt(event_dt),
                }
            )

    article_views = []
    for index in range(120):
        username = DEMO_USERS[index % len(DEMO_USERS)][0]
        slug = ARTICLE_SLUGS[index % len(ARTICLE_SLUGS)]
        viewed_at = now - timedelta(
            days=1 + ((index * 3) % 75),
            minutes=(index * 11) % 1440,
        )
        article_views.append(
            {
                "article_slug": slug,
                "username": username,
                "viewed_at": fmt(viewed_at),
            }
        )

    feedback = []
    for index in range(28):
        username = DEMO_USERS[(index * 3) % len(DEMO_USERS)][0]
        slug = ARTICLE_SLUGS[index % len(ARTICLE_SLUGS)]
        helpful = "no" if index in {5, 13, 22} else "yes"
        detail = (
            "Reason: clear | Details: The steps were easy to follow."
            if helpful == "yes"
            else "Reason: missing detail | Details: A screenshot would make this clearer."
        )
        created = now - timedelta(days=2 + ((index * 4) % 70))
        feedback.append(
            {
                "article_slug": slug,
                "username": username,
                "was_helpful": helpful,
                "feedback": detail,
                "created_at": fmt(created),
            }
        )

    return {
        "users": DEMO_USERS,
        "tickets": tickets,
        "notes": notes,
        "login_events": login_events,
        "audit_events": audit_events,
        "article_views": article_views,
        "article_feedback": feedback,
    }


def plan_summary(plan: dict) -> dict:
    return {
        "demo_users": len(plan["users"]),
        "tickets": len(plan["tickets"]),
        "ticket_notes": len(plan["notes"]),
        "login_events": len(plan["login_events"]),
        "audit_events": len(plan["audit_events"]),
        "article_views": len(plan["article_views"]),
        "article_feedback": len(plan["article_feedback"]),
    }


def seed_demo_data() -> bool:
    if not is_postgres():
        raise RuntimeError("Portfolio demo seeding is PostgreSQL-only.")

    requested = os.getenv("SEED_DEMO_DATA", "false").strip().lower() == "true"
    if not requested:
        print("Portfolio demo seed disabled.", flush=True)
        return False

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM audit_logs
            WHERE actor = %s
              AND action = 'DEMO_SEED_COMPLETE'
              AND details = %s
            LIMIT 1
            """,
            (SEED_ACTOR, f"[DEMO] seed-version={SEED_VERSION}"),
        )
        if cursor.fetchone():
            print(
                f"Portfolio demo seed {SEED_VERSION} already present; skipping.",
                flush=True,
            )
            return False

        plan = build_demo_plan()

        demo_password_hashes = {}
        for username, full_name, department, role in plan["users"]:
            demo_password_hashes[username] = generate_password_hash(
                secrets.token_urlsafe(32)
            )
            cursor.execute(
                """
                INSERT INTO users (
                    username, password_hash, role, full_name, department, email,
                    failed_attempts, locked_until, last_login, last_logout,
                    mfa_enabled, mfa_secret
                )
                VALUES (%s, %s, %s, %s, %s, %s, 0, '', '', '', 0, '')
                ON CONFLICT (username) DO NOTHING
                """,
                (
                    username,
                    demo_password_hashes[username],
                    role,
                    full_name,
                    department,
                    f"{username.removeprefix('demo_')}@example.com",
                ),
            )

        ticket_ids = []
        for ticket in plan["tickets"]:
            cursor.execute(
                """
                INSERT INTO tickets (
                    name, department, issue, priority, status, submitted_at,
                    closed_at, assigned_to, completed_by, notes, category,
                    sla_due_at, submitted_by, resolution_time, sla_met
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    ticket["name"],
                    ticket["department"],
                    ticket["issue"],
                    ticket["priority"],
                    ticket["status"],
                    ticket["submitted_at"],
                    ticket["closed_at"],
                    ticket["assigned_to"],
                    ticket["completed_by"],
                    ticket["notes"],
                    ticket["category"],
                    ticket["sla_due_at"],
                    ticket["submitted_by"],
                    ticket["resolution_time"],
                    ticket["sla_met"],
                ),
            )
            ticket_ids.append(cursor.fetchone()["id"])

        for note in plan["notes"]:
            cursor.execute(
                """
                INSERT INTO ticket_notes (
                    ticket_id, note, created_by, created_at
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    ticket_ids[note["ticket_index"]],
                    note["note"],
                    note["created_by"],
                    note["created_at"],
                ),
            )

        for event in plan["login_events"]:
            cursor.execute(
                """
                INSERT INTO login_events (username, event_type, event_time)
                VALUES (%s, %s, %s)
                """,
                (
                    event["username"],
                    event["event_type"],
                    event["event_time"],
                ),
            )

        for event in plan["audit_events"]:
            # Associate ticket-oriented synthetic logs with a stable ticket ID
            # in insertion order where possible.
            ticket_id = ticket_ids[len(ticket_ids) and (
                len(event["details"]) + len(event["actor"])
            ) % len(ticket_ids)]
            cursor.execute(
                """
                INSERT INTO audit_logs (
                    actor, action, target_type, target_id, details, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    event["actor"],
                    event["action"],
                    event["target_type"],
                    str(ticket_id),
                    event["details"],
                    event["created_at"],
                ),
            )

        for row in plan["article_views"]:
            cursor.execute(
                """
                INSERT INTO article_views (
                    article_slug, username, viewed_at
                )
                VALUES (%s, %s, %s)
                """,
                (
                    row["article_slug"],
                    row["username"],
                    row["viewed_at"],
                ),
            )

        for row in plan["article_feedback"]:
            cursor.execute(
                """
                INSERT INTO article_feedback (
                    article_slug, username, was_helpful, feedback, created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    row["article_slug"],
                    row["username"],
                    row["was_helpful"],
                    row["feedback"],
                    row["created_at"],
                ),
            )

        cursor.execute(
            """
            INSERT INTO audit_logs (
                actor, action, target_type, target_id, details, created_at
            )
            VALUES (%s, 'DEMO_SEED_COMPLETE', 'system', '', %s, %s)
            """,
            (
                SEED_ACTOR,
                f"[DEMO] seed-version={SEED_VERSION}",
                fmt(datetime.now()),
            ),
        )

        connection.commit()

        summary = plan_summary(plan)
        print("Portfolio demo data seeded successfully:", flush=True)
        for key, value in summary.items():
            print(f"  {key}: {value}", flush=True)
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print deterministic portfolio dataset counts without touching a database.",
    )
    args = parser.parse_args()

    if args.dry_run:
        summary = plan_summary(build_demo_plan(datetime(2026, 8, 22, 14, 45)))
        print("NexusDesk portfolio demo seed plan")
        print("=" * 48)
        for key, value in summary.items():
            print(f"{key:20} {value}")
        print("DRY RUN: no database rows modified.")
        return

    seed_demo_data()


if __name__ == "__main__":
    main()
