"""Platform-side authorization scope for tools that touch a real target.

A Task carries an ``authorization_scope`` of explicitly approved assets
(``host`` plus ``protocol`` and ``port``). The platform -- not the model and not
the tool -- decides whether one concrete request stays inside that scope:

- the URL must be an absolute ``http``/``https`` URL with no userinfo and no
  control characters;
- the host is matched **exactly** against an approved asset (case-insensitive,
  trailing dot removed). A newly discovered subdomain is therefore *not*
  silently in scope, which is what "发现的新资产不自动纳入 Scope" requires;
- the scheme and the effective port (``http`` 80 / ``https`` 443 when omitted)
  must match the same entry.

The normalized ``host:port`` becomes the permit's resource key, so the Kali
executor can refuse anything that does not match the exact target the platform
already approved.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from wuji_core.persistence.uow import DomainError

READ_ONLY_METHODS = ("GET", "HEAD", "OPTIONS")
SCHEMES = {"http": 80, "https": 443}
MAX_URL_LENGTH = 4096
MAX_HOST_LENGTH = 253


@dataclass(frozen=True)
class Target:
    scheme: str
    host: str
    port: int

    @property
    def key(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"


def method_allowed(method) -> bool:
    return isinstance(method, str) and method in READ_ONLY_METHODS


def parse_target(url) -> Target:
    """Normalize one absolute http(s) URL or refuse it as an invalid request."""

    if (
        not isinstance(url, str)
        or not 1 <= len(url) <= MAX_URL_LENGTH
        or any(character in url for character in "\x00\r\n\t ")
    ):
        raise DomainError("INVALID_SCHEMA", 422)
    parts = urlsplit(url)
    if parts.scheme not in SCHEMES:
        raise DomainError("INVALID_SCHEMA", 422)
    if parts.username is not None or parts.password is not None:
        raise DomainError("INVALID_SCHEMA", 422)
    host = (parts.hostname or "").rstrip(".")
    if not 1 <= len(host) <= MAX_HOST_LENGTH or "%" in host:
        raise DomainError("INVALID_SCHEMA", 422)
    try:
        port = parts.port or SCHEMES[parts.scheme]
    except ValueError as error:
        raise DomainError("INVALID_SCHEMA", 422) from error
    if not 1 <= port <= 65535:
        raise DomainError("INVALID_SCHEMA", 422)
    return Target(parts.scheme, host.lower(), port)


def approved_assets(scope):
    """Read the approved assets from a Task definition's scope list."""

    assets = []
    for entry in scope or ():
        if isinstance(entry, Target):
            assets.append(entry)
            continue
        if not isinstance(entry, dict):
            continue
        host = entry.get("host")
        protocol = entry.get("protocol")
        port = entry.get("port")
        if (
            isinstance(host, str)
            and 1 <= len(host) <= MAX_HOST_LENGTH
            and protocol in SCHEMES
            and isinstance(port, int)
            and not isinstance(port, bool)
            and 1 <= port <= 65535
        ):
            assets.append(Target(protocol, host.rstrip(".").lower(), port))
    return tuple(assets)


def require_in_scope(scope, url) -> Target:
    """The one gate every target-touching tool call passes before a permit."""

    target = parse_target(url)
    if target not in approved_assets(scope):
        raise DomainError("FORBIDDEN_TARGET", 403)
    return target


def permit_target_matches(resource_keys, url) -> Target:
    """Executor-side recheck: the URL must be the exact approved resource.

    The platform records ``target:<scheme>://<host>:<port>`` as the permit's
    resource key (a read claim appends the Run); the Kali executor refuses any
    URL that does not line up with one of them, so a tampered or replayed permit
    cannot reach a different host.
    """

    target = parse_target(url)
    expected = "target:" + target.key
    for key in resource_keys or ():
        if key == expected or key.startswith(expected + ":read:"):
            return target
    raise DomainError("FORBIDDEN_TARGET", 403)
