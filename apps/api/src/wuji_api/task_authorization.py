"""Task-local HTTP authorization; URL paths never grant authority."""
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit
import hashlib
import json
import ipaddress
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from wuji_api.scope_policy import normalize_url

class Endpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheme: Literal["http", "https"]
    port: int = Field(ge=1, le=65535, strict=True)

class HostRule(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    host: str = Field(min_length=1, max_length=253)
    include_subdomains: bool = Field(default=False, strict=True)

    @field_validator("host")
    @classmethod
    def normalize_host(cls, value):
        if any(character in value for character in "/?#@"):
            raise ValueError("host cannot contain URL components")
        try:
            ipaddress.ip_address(value.strip("[]"))
        except ValueError:
            if ":" in value:
                raise ValueError("host cannot contain a port")
        authority = f"[{value}]" if ":" in value and not value.startswith("[") else value
        parsed = urlsplit(normalize_url(f"http://{authority}/"))
        if parsed.port or parsed.path != "/" or parsed.query or parsed.fragment:
            raise ValueError("host cannot contain a port or URL component")
        return parsed.hostname

    @model_validator(mode="after")
    def ip_subdomains(self):
        try: ipaddress.ip_address(self.host)
        except ValueError: return self
        if self.include_subdomains: raise ValueError("IP literals cannot include subdomains")
        return self

class IncludeRule(HostRule):
    endpoint: Endpoint

class ExcludeRule(HostRule):
    endpoints: Literal["all_included"] | list[Endpoint] = Field(default="all_included")

    @field_validator("endpoints")
    @classmethod
    def nonempty_endpoints(cls, value):
        if isinstance(value, list) and not value: raise ValueError("choose all included or explicit endpoints")
        return value

class TaskAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    includes: list[IncludeRule] = Field(default_factory=list, max_length=100)
    excludes: list[ExcludeRule] = Field(default_factory=list, max_length=100)
    valid_until: datetime | None = None

    @field_validator("valid_until")
    @classmethod
    def aware(cls, value):
        if value is not None and value.tzinfo is None: raise ValueError("authorization deadline requires timezone")
        return value

def host_matches(host, rule):
    return host == rule["host"] or (rule["include_subdomains"] and host.endswith("." + rule["host"]))

def permits_url(scope, url):
    parsed = urlsplit(normalize_url(url))
    endpoint = {"scheme": parsed.scheme, "port": parsed.port or (443 if parsed.scheme == "https" else 80)}
    included = any(host_matches(parsed.hostname, r) and r["endpoint"] == endpoint for r in scope["includes"])
    excluded = any(host_matches(parsed.hostname, r) and (r["endpoints"] == "all_included" or endpoint in r["endpoints"]) for r in scope["excludes"])
    return included and not excluded

def authorization_digest(scope):
    value = {"scope": scope, "confirmation_text_version": "1.0"}
    return hashlib.sha256(b"wuji-task-authorization-v1\n" + json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
