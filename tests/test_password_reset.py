from datetime import datetime, timedelta

from services.password_reset_service import (
    create_password_reset_token,
    get_valid_reset_token,
    mark_token_used,
)


def test_password_reset_token_can_only_be_used_once(db):
    user_id = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()["id"]
    token = create_password_reset_token(user_id)
    assert get_valid_reset_token(token) is not None
    mark_token_used(token)
    assert get_valid_reset_token(token) is None


def test_expired_password_reset_token_is_rejected(db):
    user_id = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("employee",),
    ).fetchone()["id"]
    token = create_password_reset_token(user_id)
    expired = (datetime.now() - timedelta(minutes=1)).strftime("%m/%d/%Y %I:%M %p")
    db.execute(
        "UPDATE password_reset_tokens SET expires_at = ? WHERE token = ?",
        (expired, token),
    )
    db.commit()
    assert get_valid_reset_token(token) is None
