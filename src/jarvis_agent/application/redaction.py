from __future__ import annotations

from typing import Any


_SECRET_MARKERS = ("api_key", "password", "authorization", "secret", "token")


def redact(value: Any, explicit_fields: tuple[str, ...] = ()) -> Any:
    explicit = {field.lower() for field in explicit_fields}
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, nested in value.items():
            lowered = key.lower()
            if lowered in explicit or any(marker in lowered for marker in _SECRET_MARKERS):
                result[key] = "***REDACTED***"
            else:
                result[key] = redact(nested, explicit_fields)
        return result
    if isinstance(value, list):
        return [redact(item, explicit_fields) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item, explicit_fields) for item in value)
    return value
