import re
from datetime import datetime

from app.models.user_model import USER_ROLES


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).+$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email_address(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_PATTERN.match(email):
        raise ValueError("Email must be a valid address")
    return email


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not PASSWORD_PATTERN.match(password):
        raise ValueError("Password must include uppercase, lowercase, number, and special character")
    return password


def validate_user_role(role: str) -> str:
    if role not in USER_ROLES:
        allowed = ", ".join(sorted(USER_ROLES))
        raise ValueError(f"Role must be one of: {allowed}")
    return role


def validate_non_empty(value: str, field_name: str = "Value") -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    return value


def validate_choice(value: str, allowed_values: set[str], field_name: str) -> str:
    if value not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return value


def validate_year(value: int) -> int:
    max_year = datetime.utcnow().year + 1
    if value < 2000 or value > max_year:
        raise ValueError(f"Year must be between 2000 and {max_year}")
    return value
