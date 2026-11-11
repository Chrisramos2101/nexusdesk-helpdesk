
import pytest

from services.validation_service import (
    validate_password_strength,
    is_not_empty,
    is_valid_choice,
    VALID_PRIORITIES,
)


@pytest.mark.parametrize(
    "password, expected_message",
    [
        (None, "at least 8 characters"),
        ("Short1!", "at least 8 characters"),
        ("password123!", "uppercase"),
        ("PASSWORD123!", "lowercase"),
        ("Password!!", "number"),
        ("Password123", "special character"),
    ],
)
def test_weak_passwords_are_rejected(
    password, expected_message
):
    valid, message = validate_password_strength(password)

    assert valid is False
    assert expected_message in message


@pytest.mark.parametrize(
    "password",
    [
        "Password1!",
        "SecureTest2026#",
    ],
)
def test_strong_passwords_are_accepted(password):
    valid, message = validate_password_strength(password)

    assert valid is True
    assert message == ""


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, False),
        ("", False),
        ("   ", False),
        ("Valid issue", True),
    ],
)
def test_required_text_validation(value, expected):
    assert is_not_empty(value) is expected


def test_priority_validation_is_case_sensitive():
    assert is_valid_choice(
        "High", VALID_PRIORITIES
    ) is True

    assert is_valid_choice(
        "high", VALID_PRIORITIES
    ) is False
