from services.security_service import check_rate_limit, reset_rate_limit


def test_database_backed_rate_limit_blocks_after_limit(db):
    key = "127.0.0.1:test"
    assert check_rate_limit(key, "unit_test", 2, 60)[0] is True
    assert check_rate_limit(key, "unit_test", 2, 60)[0] is True
    allowed, retry_after = check_rate_limit(key, "unit_test", 2, 60)
    assert allowed is False
    assert retry_after > 0


def test_rate_limit_can_be_reset(db):
    key = "127.0.0.1:reset"
    check_rate_limit(key, "unit_test", 1, 60)
    assert check_rate_limit(key, "unit_test", 1, 60)[0] is False
    reset_rate_limit(key, "unit_test")
    assert check_rate_limit(key, "unit_test", 1, 60)[0] is True
