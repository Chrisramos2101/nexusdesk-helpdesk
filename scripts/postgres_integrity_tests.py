
import os
import sys
import unittest
import uuid
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db import get_db_connection
from services.security_service import (
    check_rate_limit,
    reset_rate_limit,
)
from services.user_service import create_user_account


def verify_test_database():
    url = urlparse(os.environ.get("DATABASE_URL", ""))

    if (
        os.environ.get("NEXUSDESK_ALLOW_PG_TEST_WRITES") != "1"
        or url.scheme != "postgresql"
        or url.hostname not in ("127.0.0.1", "localhost")
        or url.path != "/nexusdesk_test"
    ):
        raise RuntimeError(
            "PostgreSQL integrity tests require an explicitly "
            "authorized local nexusdesk_test database."
        )


class PostgreSQLIntegrityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        verify_test_database()

    def setUp(self):
        self.prefix = "ci_integrity_" + uuid.uuid4().hex[:12]
        self.ticket_ids = []

    def tearDown(self):
        # Only remove records created by this test.
        connection = get_db_connection()

        try:
            cursor = connection.cursor()

            for ticket_id in self.ticket_ids:
                cursor.execute(
                    "DELETE FROM tickets WHERE id = %s",
                    (ticket_id,),
                )

            cursor.execute(
                "DELETE FROM users WHERE username LIKE %s",
                (self.prefix + "%",),
            )

            cursor.execute(
                "DELETE FROM security_rate_limits "
                "WHERE bucket_key LIKE %s",
                (self.prefix + "%",),
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def create_user(self, suffix):
        username = self.prefix + "_" + suffix

        create_user_account(
            full_name="PostgreSQL Integration Test",
            username=username,
            email=username + "@example.com",
            department="IT",
            password_hash=generate_password_hash(
                "IntegrationPassword123!"
            ),
            role="employee",
        )

        return username

    def test_successful_user_creation_commits(self):
        username = self.create_user("success")

        connection = get_db_connection()

        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT username FROM users "
                "WHERE username = %s",
                (username,),
            )

            row = cursor.fetchone()

            self.assertIsNotNone(row)
            self.assertEqual(row["username"], username)

        finally:
            connection.close()

    def test_duplicate_user_rolls_back_and_recovers(self):
        username = self.create_user("duplicate")

        with self.assertRaises(psycopg2.IntegrityError):
            create_user_account(
                full_name="Duplicate",
                username=username,
                email="duplicate@example.com",
                department="IT",
                password_hash=generate_password_hash(
                    "IntegrationPassword123!"
                ),
                role="employee",
            )

        # The prior integrity error must not poison
        # subsequent database operations.
        recovered = self.create_user("recovered")

        connection = get_db_connection()

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM users
                WHERE username IN (%s, %s)
                """,
                (username, recovered),
            )

            self.assertEqual(
                cursor.fetchone()["count"], 2
            )

        finally:
            connection.close()

    def test_foreign_key_cascade_deletes_children(self):
        username = self.create_user("cascade")
        connection = get_db_connection()

        try:
            cursor = connection.cursor()

            cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,),
            )
            user_id = cursor.fetchone()["id"]

            cursor.execute(
                """
                INSERT INTO tickets (
                    name, department, issue, priority,
                    status, submitted_at, submitted_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    "Integration Test",
                    "IT",
                    self.prefix,
                    "Medium",
                    "Open",
                    "11/11/2026 10:00 AM",
                    username,
                ),
            )

            ticket_id = cursor.fetchone()["id"]
            self.ticket_ids.append(ticket_id)

            cursor.execute(
                """
                INSERT INTO ticket_notes
                (ticket_id, note, created_by, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    ticket_id,
                    "Integration note",
                    username,
                    "11/11/2026 10:01 AM",
                ),
            )

            cursor.execute(
                """
                INSERT INTO password_reset_tokens
                (user_id, token, expires_at, used, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    uuid.uuid4().hex,
                    "11/11/2026 11:00 AM",
                    0,
                    "11/11/2026 10:00 AM",
                ),
            )

            connection.commit()

            cursor.execute(
                "DELETE FROM tickets WHERE id = %s",
                (ticket_id,),
            )

            cursor.execute(
                "DELETE FROM users WHERE id = %s",
                (user_id,),
            )

            connection.commit()

            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM ticket_notes
                WHERE ticket_id = %s
                """,
                (ticket_id,),
            )
            self.assertEqual(
                cursor.fetchone()["count"], 0
            )

            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM password_reset_tokens
                WHERE user_id = %s
                """,
                (user_id,),
            )
            self.assertEqual(
                cursor.fetchone()["count"], 0
            )

        finally:
            connection.close()

    def test_rate_limit_is_database_backed(self):
        key = self.prefix + "_rate"

        self.assertEqual(
            check_rate_limit(key, "login", 2, 60),
            (True, 0),
        )

        self.assertEqual(
            check_rate_limit(key, "login", 2, 60),
            (True, 0),
        )

        allowed, retry_after = check_rate_limit(
            key, "login", 2, 60
        )

        self.assertFalse(allowed)
        self.assertGreaterEqual(retry_after, 1)

        reset_rate_limit(key, "login")

        self.assertEqual(
            check_rate_limit(key, "login", 2, 60),
            (True, 0),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
