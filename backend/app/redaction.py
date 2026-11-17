from __future__ import annotations

import re


# Authorization headers can contain a scheme (Bearer, Basic, etc.) followed by
# a credential. Consume the entire value before applying generic key/value rules.
_AUTHORIZATION_ASSIGNMENT = re.compile(
    r'''(?i)\bauthorization\b\s*[:=]\s*["']?(?:[A-Za-z][A-Za-z0-9_-]*\s+)?[^\s"',;]+["']?'''
)
_CREDENTIAL_ASSIGNMENT = re.compile(
    r'''(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\b\s*[:=]\s*["']?([^\s"',;]+)["']?'''
)
_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    flags=re.DOTALL,
)


def redact_secrets(value: str) -> str:
    """Remove common inline credentials and private keys from stored or external text."""
    cleaned = _AUTHORIZATION_ASSIGNMENT.sub("Authorization=[REDACTED]", str(value or ""))
    cleaned = _CREDENTIAL_ASSIGNMENT.sub(r"\1=[REDACTED]", cleaned)
    cleaned = _BEARER_TOKEN.sub("Bearer [REDACTED]", cleaned)
    return _PRIVATE_KEY.sub("[REDACTED PRIVATE KEY]", cleaned)
