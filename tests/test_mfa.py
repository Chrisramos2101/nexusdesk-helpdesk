from services.mfa_service import generate_mfa_code, verify_mfa_code


def test_mfa_code_is_one_time_use(db):
    code = generate_mfa_code("employee")
    assert verify_mfa_code("employee", code) is True
    assert verify_mfa_code("employee", code) is False


def test_new_mfa_code_invalidates_old_code(db):
    generate_mfa_code("employee")
    first_record = db.execute(
        "SELECT id FROM mfa_codes WHERE username = ? ORDER BY id DESC LIMIT 1",
        ("employee",),
    ).fetchone()

    second = generate_mfa_code("employee")
    invalidated = db.execute(
        "SELECT used FROM mfa_codes WHERE id = ?",
        (first_record["id"],),
    ).fetchone()

    assert invalidated["used"] == 1
    assert verify_mfa_code("employee", second) is True


def test_mfa_challenge_locks_after_five_wrong_codes(db):
    correct = generate_mfa_code("employee")
    for _ in range(5):
        assert verify_mfa_code("employee", "000000") is False

    assert verify_mfa_code("employee", correct) is False
    record = db.execute(
        "SELECT attempts, used FROM mfa_codes WHERE username = ? ORDER BY id DESC LIMIT 1",
        ("employee",),
    ).fetchone()
    assert record["attempts"] == 5
    assert record["used"] == 1
