import sys
import uuid
from pathlib import Path

# When this file is executed directly from /app/scripts inside Docker,
# Python otherwise puts /app/scripts (not /app) on sys.path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.security import generate_password_hash

from app import app
from database.db import get_db_connection
from database.sql_helpers import db_placeholder, is_postgres
from services.ticket_service import (
    add_ticket_note,
    assign_ticket_to_user,
    close_ticket,
    create_ticket,
    delete_ticket_by_id,
    get_ticket_by_id,
)


def main():
    if not is_postgres():
        raise SystemExit("FAIL: DATABASE_URL is not PostgreSQL.")

    suffix = uuid.uuid4().hex[:8]
    employee = f"phase3_employee_{suffix}"
    admin = f"phase3_admin_{suffix}"
    placeholder = db_placeholder()

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT current_database() AS db")
        row = cursor.fetchone()
        print("PostgreSQL database:", row["db"])

        for username, role in [(employee, "employee"), (admin, "admin")]:
            cursor.execute(
                f"""
                INSERT INTO users
                (full_name, username, email, department, password_hash, role,
                 failed_attempts, locked_until, last_login, last_logout)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder},
                        {placeholder}, {placeholder}, 0, '', '', '')
                """,
                (
                    username,
                    username,
                    f"{username}@example.com",
                    "IT",
                    generate_password_hash("Password1!"),
                    role,
                ),
            )
        connection.commit()
    finally:
        connection.close()

    ticket_id = create_ticket(
        "Phase 3 Test",
        "IT",
        "PostgreSQL integration smoke test",
        "Medium",
        "Software",
        "08/22/2026 12:00 PM",
        employee,
        "08/22/2026 08:00 PM",
    )
    assert ticket_id, "Ticket ID was not returned."

    ticket = get_ticket_by_id(ticket_id)
    assert ticket and ticket["submitted_by"] == employee

    add_ticket_note(ticket_id, "Phase 3 note", admin, "08/22/2026 12:01 PM")
    assign_ticket_to_user(ticket_id, admin)
    close_ticket(ticket_id, "08/22/2026 12:05 PM", admin, "5 minutes", "Yes")

    ticket = get_ticket_by_id(ticket_id)
    assert ticket["status"] == "Closed"
    assert ticket["assigned_to"] == admin

    with app.test_client() as client:
        health = client.get("/healthz")
        assert health.status_code == 200, health.data
        payload = health.get_json()
        assert payload["database"] == "postgresql", payload

        with client.session_transaction() as session:
            session["username"] = admin
            session["role"] = "admin"
            session.permanent = True

        for path in ["/dashboard", "/stats", "/users", "/system_dashboard", "/knowledge_base"]:
            response = client.get(path)
            assert response.status_code == 200, f"{path}: {response.status_code}"

        with client.session_transaction() as session:
            session["username"] = employee
            session["role"] = "employee"
            session.permanent = True

        for path in ["/", "/my_tickets", f"/my_tickets/{ticket_id}", "/profile", "/knowledge_base"]:
            response = client.get(path)
            assert response.status_code == 200, f"{path}: {response.status_code}"

    delete_ticket_by_id(ticket_id)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"DELETE FROM users WHERE username IN ({placeholder}, {placeholder})",
            (employee, admin),
        )
        connection.commit()
    finally:
        connection.close()

    print("POSTGRESQL APPLICATION SMOKE TEST: PASS")


if __name__ == "__main__":
    main()
