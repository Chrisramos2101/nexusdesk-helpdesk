
from datetime import datetime, timedelta

from services import security_service as security


FIXED_NOW = datetime(2026, 11, 11, 15, 0, 0)


def freeze_time(monkeypatch):
    monkeypatch.setattr(
        security,
        "_utc_now_naive",
        lambda: FIXED_NOW,
    )


def test_first_request_is_allowed(monkeypatch):
    freeze_time(monkeypatch)

    assert security.check_rate_limit(
        "first-user", "login", 3, 60
    ) == (True, 0)


def test_request_is_blocked_after_limit(monkeypatch):
    freeze_time(monkeypatch)

    key = "blocked-user"

    assert security.check_rate_limit(
        key, "login", 2, 60
    ) == (True, 0)

    assert security.check_rate_limit(
        key, "login", 2, 60
    ) == (True, 0)

    allowed, retry_after = security.check_rate_limit(
        key, "login", 2, 60
    )

    assert allowed is False
    assert 1 <= retry_after <= 60


def test_expired_window_resets_attempt_count(
    monkeypatch, db
):
    freeze_time(monkeypatch)

    db.execute(
        """
        INSERT INTO security_rate_limits
        (bucket_key, action, attempts, window_start)
        VALUES (?, ?, ?, ?)
        """,
        (
            "expired-user",
            "login",
            50,
            (FIXED_NOW - timedelta(minutes=10))
            .strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    db.commit()

    assert security.check_rate_limit(
        "expired-user", "login", 3, 60
    ) == (True, 0)

    record = db.execute(
        """
        SELECT attempts
        FROM security_rate_limits
        WHERE bucket_key = ?
        """,
        ("expired-user",),
    ).fetchone()

    assert record["attempts"] == 1


def test_malformed_window_timestamp_is_recovered(
    monkeypatch, db
):
    freeze_time(monkeypatch)

    db.execute(
        """
        INSERT INTO security_rate_limits
        (bucket_key, action, attempts, window_start)
        VALUES (?, ?, ?, ?)
        """,
        ("malformed-user", "login", 99, "invalid"),
    )
    db.commit()

    assert security.check_rate_limit(
        "malformed-user", "login", 3, 60
    ) == (True, 0)


def test_reset_rate_limit_removes_record(
    monkeypatch, db
):
    freeze_time(monkeypatch)

    security.check_rate_limit(
        "reset-user", "login", 2, 60
    )

    security.reset_rate_limit(
        "reset-user", "login"
    )

    count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM security_rate_limits
        WHERE bucket_key = ? AND action = ?
        """,
        ("reset-user", "login"),
    ).fetchone()["count"]

    assert count == 0


def test_rate_limit_actions_are_independent(monkeypatch):
    freeze_time(monkeypatch)

    key = "multi-action-user"

    security.check_rate_limit(
        key, "login", 1, 60
    )

    assert security.check_rate_limit(
        key, "login", 1, 60
    )[0] is False

    assert security.check_rate_limit(
        key, "password_reset", 1, 60
    ) == (True, 0)
