from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit


class DeploymentConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class LicenseStatus:
    enabled: bool
    status: str
    blocked: bool
    customer_name: str
    expires_at: str | None
    support_message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_license(
    *,
    enabled: bool,
    customer_name: str,
    expires_at: datetime | None,
    support_message: str,
    now: datetime | None = None,
) -> LicenseStatus:
    if not enabled:
        return LicenseStatus(
            enabled=False,
            status="disabled",
            blocked=False,
            customer_name=customer_name,
            expires_at=expires_at.isoformat() if expires_at else None,
            support_message=support_message,
        )

    if expires_at is None or expires_at.tzinfo is None or expires_at.utcoffset() is None:
        return LicenseStatus(
            enabled=True,
            status="invalid_configuration",
            blocked=True,
            customer_name=customer_name,
            expires_at=expires_at.isoformat() if expires_at else None,
            support_message="A timezone-aware LICENSE_EXPIRES_AT value is required.",
        )

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("The license evaluation time must include a timezone")

    expired = current_time.astimezone(timezone.utc) >= expires_at.astimezone(timezone.utc)
    return LicenseStatus(
        enabled=True,
        status="expired" if expired else "active",
        blocked=expired,
        customer_name=customer_name,
        expires_at=expires_at.isoformat(),
        support_message=support_message,
    )


def validate_mongodb_target(
    *,
    uri: str,
    database_name: str,
    validation_enabled: bool,
    allowed_hosts: list[str],
    allowed_databases: list[str],
) -> None:
    if not validation_enabled:
        return

    normalized_hosts = {host.strip().lower() for host in allowed_hosts if host.strip()}
    normalized_databases = {name.strip() for name in allowed_databases if name.strip()}
    if not normalized_hosts or not normalized_databases:
        raise DeploymentConfigurationError(
            "MongoDB target validation requires both ALLOWED_MONGODB_HOSTS and ALLOWED_MONGODB_DATABASES."
        )

    parsed = urlsplit(uri)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"mongodb", "mongodb+srv"} or not host:
        raise DeploymentConfigurationError("MONGODB_URI is missing or is not a valid MongoDB URI.")
    if host not in normalized_hosts:
        raise DeploymentConfigurationError(f"MongoDB host is not approved: {host}")
    if database_name not in normalized_databases:
        raise DeploymentConfigurationError(f"MongoDB database is not approved: {database_name}")
