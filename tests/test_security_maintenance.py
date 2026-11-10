
from datetime import datetime, timedelta, timezone

from services.cleanup_service import cleanup_expired_security_records
from services.monitoring_service import log_system_event


def timestamp(days=0):
    return (datetime.now() + timedelta(days=days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def test_cleanup_removes_expired_mfa_code(db):
    db.execute(
        """
        INSERT INTO mfa_codes
        (username, code, expires_at, used, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("employee", "111111", timestamp(-1), 0, timestamp(-2)),
    )
    db.commit()

    cleanup_expired_security_records()

    count = db.execute(
        "SELECT COUNT(*) FROM mfa_codes"
    ).fetchone()[0]

    assert count == 0


def test_cleanup_preserves_valid_mfa_code(db):
    db.execute(
        """
        INSERT INTO mfa_codes
        (username, code, expires_at, used, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("employee", "222222", timestamp(1), 0, timestamp()),
    )
    db.commit()

    cleanup_expired_security_records()

    count = db.execute(
        "SELECT COUNT(*) FROM mfa_codes"
    ).fetchone()[0]

    assert count == 1


def test_cleanup_deletes_used_reset_tokens_only(db):
    user_id = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()["id"]

    for token, used in [("used-token", 1), ("active-token", 0)]:
        db.execute(
            """
            INSERT INTO password_reset_tokens
            (user_id, token, expires_at, used, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id, token,
                "12/31/2099 12:00 PM",
                used,
                "01/01/2026 12:00 PM",
            ),
        )
    db.commit()

    cleanup_expired_security_records()

    remaining = [
        row["token"]
        for row in db.execute(
            "SELECT token FROM password_reset_tokens"
        ).fetchall()
    ]

    assert remaining == ["active-token"]


def test_cleanup_removes_old_rate_limits(db):
    for key, days in [("old-bucket", -60), ("new-bucket", 1)]:
        db.execute(
            """
            INSERT INTO security_rate_limits
            (bucket_key, action, attempts, window_start)
            VALUES (?, ?, ?, ?)
            """,
            (key, "login", 2, timestamp(days)),
        )
    db.commit()

    cleanup_expired_security_records()

    remaining = {
        row["bucket_key"]
        for row in db.execute(
            "SELECT bucket_key FROM security_rate_limits"
        ).fetchall()
    }

    assert remaining == {"new-bucket"}


def test_cleanup_is_safe_to_repeat(db):
    cleanup_expired_security_records()
    cleanup_expired_security_records()

    assert db.execute(
        "SELECT COUNT(*) FROM mfa_codes"
    ).fetchone()[0] == 0


def test_production_monitoring_uses_stderr(
    monkeypatch, capsys
):
    monkeypatch.setenv("FLASK_ENV", "production")

    log_system_event("INFO", "Security check")

    captured = capsys.readouterr()

    assert "[INFO] Security check" in captured.err


def test_local_monitoring_writes_log(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.delenv("LOG_TO_STDOUT", raising=False)
    monkeypatch.chdir(tmp_path)

    log_system_event("INFO", "Local test event")

    log_file = tmp_path / "logs" / "system.log"

    assert log_file.exists()
    assert "[INFO] Local test event" in log_file.read_text(
        encoding="utf-8"
    )
