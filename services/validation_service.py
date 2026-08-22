VALID_DEPARTMENTS = [
    "Finance",
    "HR",
    "IT",
    "Management",
    "Operations",
    "Sales"
]

VALID_PRIORITIES = [
    "High",
    "Medium",
    "Low"
]

VALID_CATEGORIES = [
    "Hardware",
    "Software",
    "Network",
    "Account Access",
    "Security",
    "Other"
]

VALID_STATUSES = [
    "Open",
    "In Progress",
    "Closed"
]

VALID_ROLES = [
    "employee",
    "admin"
]


def is_valid_choice(value, allowed_values):
    return value in allowed_values


def is_not_empty(value):
    return value is not None and value.strip() != ""


def validate_password_strength(password):
    if password is None or len(password) < 8:
        return False, "Password must be at least 8 characters."

    has_uppercase = any(char.isupper() for char in password)
    has_lowercase = any(char.islower() for char in password)
    has_number = any(char.isdigit() for char in password)
    has_symbol = any(not char.isalnum() for char in password)

    if not has_uppercase:
        return False, "Password must include at least one uppercase letter."

    if not has_lowercase:
        return False, "Password must include at least one lowercase letter."

    if not has_number:
        return False, "Password must include at least one number."

    if not has_symbol:
        return False, "Password must include at least one special character."

    return True, ""