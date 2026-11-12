"""Security regression checks for profile email ownership verification."""
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from werkzeug.security import check_password_hash

from services.email_change_service import confirm_email_change, issue_email_change


def _user_id(db, username="employee"):
    return db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()[0]


def _email(db, username="employee"):
    return db.execute("SELECT email FROM users WHERE username = ?", (username,)).fetchone()["email"]


def _request(client, email="new@example.com", password="Password1!"):
    return client.post("/update_profile", data={
        "full_name": "Updated Employee", "email": email,
        "department": "IT", "current_password": password,
    })


def test_unchanged_email_updates_profile_without_password(client, login_as, db):
    login_as(client)
    response = client.post("/update_profile", data={
        "full_name": "New Name", "email": "employee@example.com", "department": "IT"
    })
    assert response.status_code == 302
    assert db.execute("SELECT full_name FROM users WHERE username='employee'").fetchone()[0] == "New Name"


def test_email_change_requires_current_password(client, login_as, db):
    login_as(client)
    response = _request(client, password="incorrect")
    assert response.status_code == 302
    assert "email_error" in response.headers["Location"]
    assert _email(db) == "employee@example.com"
    assert db.execute("SELECT COUNT(*) FROM email_change_tokens").fetchone()[0] == 0


def test_email_change_requires_email_delivery(client, login_as, db):
    login_as(client)
    with patch("routes.auth.send_email", return_value=False):
        response = _request(client)
    assert "email_error" in response.headers["Location"]
    assert _email(db) == "employee@example.com"
    assert db.execute("SELECT COUNT(*) FROM email_change_tokens WHERE used=0").fetchone()[0] == 0


def test_new_email_stays_pending_until_confirmation(client, login_as, db):
    login_as(client)
    with patch("routes.auth.send_email", return_value=True) as mail:
        response = _request(client)
    assert "email_pending" in response.headers["Location"]
    assert _email(db) == "employee@example.com"
    assert mail.call_count >= 1
    assert mail.call_args_list[0].args[1] == "new@example.com"


def test_valid_token_changes_email_once(client, login_as, db):
    login_as(client)
    token = issue_email_change(_user_id(db), "new@example.com")
    with patch("routes.auth.send_email", return_value=True):
        response = client.post("/confirm_email_change", data={"token": token})
    assert response.status_code == 302
    assert _email(db) == "new@example.com"
    assert confirm_email_change("employee", token)[0] is False


def test_link_preview_does_not_consume_token(client, login_as, db):
    login_as(client)
    token = issue_email_change(_user_id(db), "new@example.com")
    response = client.get("/confirm_email_change", query_string={"token": token})
    assert response.status_code == 200
    assert _email(db) == "employee@example.com"
    assert db.execute("SELECT used FROM email_change_tokens WHERE user_id=?", (_user_id(db),)).fetchone()[0] == 0


def test_expired_token_is_rejected(db):
    token = issue_email_change(_user_id(db), "new@example.com")
    db.execute("UPDATE email_change_tokens SET expires_at=?", ((datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),))
    db.commit()
    assert confirm_email_change("employee", token)[0] is False
    assert _email(db) == "employee@example.com"


def test_token_cannot_be_used_by_another_account(db):
    token = issue_email_change(_user_id(db), "new@example.com")
    assert confirm_email_change("other", token)[0] is False
    assert _email(db) == "employee@example.com"


def test_existing_address_cannot_be_claimed(client, login_as, db):
    login_as(client)
    with patch("routes.auth.send_email", return_value=True) as send:
        response = _request(client, email="ADMIN@example.com")
    assert "email_error" in response.headers["Location"]
    assert not send.called
    assert _email(db) == "employee@example.com"


def test_new_request_revokes_older_link(db):
    old = issue_email_change(_user_id(db), "first@example.com")
    new = issue_email_change(_user_id(db), "second@example.com")
    assert confirm_email_change("employee", old)[0] is False
    assert confirm_email_change("employee", new)[0] is True
    assert _email(db) == "second@example.com"


def test_email_change_revokes_password_reset_tokens(db):
    db.execute("INSERT INTO password_reset_tokens (user_id,token,expires_at,used,created_at) VALUES (?, 'existing', '01/01/2030 10:00 AM',0,'01/01/2026 10:00 AM')", (_user_id(db),))
    db.commit()
    token = issue_email_change(_user_id(db), "new@example.com")
    assert confirm_email_change("employee", token)[0] is True
    assert db.execute("SELECT used FROM password_reset_tokens WHERE token='existing'").fetchone()[0] == 1


def test_email_token_is_stored_hashed(db):
    token = issue_email_change(_user_id(db), "new@example.com")
    saved = db.execute("SELECT token_hash FROM email_change_tokens").fetchone()[0]
    assert saved != token
    assert saved == hashlib.sha256(token.encode()).hexdigest()


def test_email_change_does_not_modify_password(db):
    before = db.execute("SELECT password_hash FROM users WHERE id=?", (_user_id(db),)).fetchone()[0]
    token = issue_email_change(_user_id(db), "new@example.com")
    assert confirm_email_change("employee", token)[0] is True
    after = db.execute("SELECT password_hash FROM users WHERE id=?", (_user_id(db),)).fetchone()[0]
    assert before == after
    assert check_password_hash(after, "Password1!")
