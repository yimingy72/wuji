from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qs, urljoin, urlparse
from uuid import UUID

import httpx
import pytest


LOGIN_ERROR_RE = re.compile(
    r"^/login\?error=(UNAUTHENTICATED|FORBIDDEN|SERVICE_UNAVAILABLE|INTERNAL_ERROR)"
    r"&trace_id=([0-9a-fA-F-]{36})$"
)


@dataclass(frozen=True)
class RunManifest:
    path: Path
    data: dict[str, Any]

    def url(self, name: str) -> str:
        return str(self.data["urls"][name]).rstrip("/")

    def seed(self, name: str) -> dict[str, Any]:
        return self.data["seed_users"][name]

    def project_symbol(self, project_id: str) -> str:
        return next(
            symbol
            for symbol, value in self.data["seed_entities"]["projects"].items()
            if value["id"] == project_id
        )

    def tenant_symbol(self, tenant_id: str) -> str:
        return next(
            symbol
            for symbol, value in self.data["seed_entities"]["tenants"].items()
            if value["id"] == tenant_id
        )

    def project(self, project_id: str) -> dict[str, Any]:
        return self.data["seed_entities"]["projects"][self.project_symbol(project_id)]

    @property
    def run_id(self) -> str:
        return str(self.data["run_id"])

    @property
    def artifacts_dir(self) -> Path:
        return Path(self.data["artifacts_dir"])


class Control:
    def __init__(self, manifest: RunManifest) -> None:
        self.manifest = manifest
        self.entrypoint = Path("scripts/platform/control.sh").resolve()

    def run(self, *arguments: str) -> dict[str, Any]:
        result = self.invoke(*arguments)
        if result.returncode:
            # stderr is required to be redacted by the lifecycle command.
            pytest.fail(
                f"control command {arguments!r} exited {result.returncode}: {result.stderr[-2000:]}"
            )
        return self.parse(result)

    def run_expect_failure(self, *arguments: str) -> dict[str, Any]:
        result = self.invoke(*arguments)
        assert result.returncode != 0, f"control command unexpectedly succeeded: {arguments!r}"
        return self.parse(result, stream="stderr")

    def invoke(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(self.entrypoint), "--run-file", str(self.manifest.path), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result

    def parse(
        self, result: subprocess.CompletedProcess[str], stream: str = "stdout"
    ) -> dict[str, Any]:
        raw = result.stdout if stream == "stdout" else result.stderr
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            pytest.fail(f"control command returned non-JSON output: {error}")
        assert payload.get("run_id") in (None, self.manifest.run_id)
        result = payload.get("result")
        return result if isinstance(result, dict) else payload


@pytest.fixture(scope="session")
def run_manifest() -> RunManifest:
    raw_path = os.environ.get("WUJI_TEST_RUN_FILE")
    if not raw_path:
        pytest.fail("WUJI_TEST_RUN_FILE is required for platform tests", pytrace=False)
    path = Path(raw_path)
    assert path.is_absolute(), "WUJI_TEST_RUN_FILE must be absolute"
    assert path.is_file(), "WUJI_TEST_RUN_FILE must refer to a file"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600, "run manifest must have mode 0600"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["source_sha"] == subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    required_urls = {
        "web": 4182,
        "api": 8002,
        "idp": 18082,
        "issuer_fixture": 18083,
        "unmigrated_api": 8003,
        "database": 15434,
    }
    for name, port in required_urls.items():
        parsed = urlparse(data["urls"][name])
        assert parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        assert parsed.port == port
    assert data["namespace"] == "wuji-test"
    assert data["database"]["name"] == f'wuji_test_{data["run_id"]}'
    assert data["run_id"] in data["realm"]["name"]
    artifacts = Path(data["artifacts_dir"])
    assert artifacts.is_absolute() and artifacts.is_dir()
    assert stat.S_IMODE(artifacts.stat().st_mode) == 0o700
    for process_name in ("api", "issuer_fixture"):
        log_path = Path(data["processes"][process_name]["log_path"])
        assert log_path.is_absolute() and log_path.is_file()
        assert stat.S_IMODE(log_path.stat().st_mode) == 0o600
    api_process = data["processes"]["api"]
    assert api_process["reads_run_file"] is False
    assert set(api_process["credential_scopes"]) == {"auth_dsn", "project_dsn", "oidc_client"}
    return RunManifest(path.resolve(), data)


@pytest.fixture(scope="session")
def control(run_manifest: RunManifest) -> Control:
    return Control(run_manifest)


@pytest.fixture
def client(run_manifest: RunManifest) -> Iterator[httpx.Client]:
    with httpx.Client(
        base_url=run_manifest.url("web"),
        follow_redirects=False,
        timeout=15,
        headers={"User-Agent": "wuji-phase1a-independent-test"},
    ) as value:
        yield value


def fixture_control(manifest: RunManifest, scenario: str, user: str = "protocol_user") -> None:
    token = manifest.data["credentials"]["oidc_fixture"]["control_token"]
    response = httpx.post(
        f'{manifest.url("issuer_fixture")}/_control',
        headers={"Authorization": f"Bearer {token}"},
        json={"scenario": scenario, "user": user},
        timeout=5,
    )
    response.raise_for_status()


def release_fixture_token(manifest: RunManifest) -> None:
    token = manifest.data["credentials"]["oidc_fixture"]["control_token"]
    response = httpx.post(
        f'{manifest.url("issuer_fixture")}/_control',
        headers={"Authorization": f"Bearer {token}"},
        json={"action": "release_token"},
        timeout=5,
    )
    response.raise_for_status()


def fixture_stats(manifest: RunManifest) -> dict[str, Any]:
    token = manifest.data["credentials"]["oidc_fixture"]["control_token"]
    response = httpx.get(
        f'{manifest.url("issuer_fixture")}/_control/stats',
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def begin_login(client: httpx.Client, return_to: str = "/projects") -> httpx.Response:
    response = client.get("/api/v1/auth/login", params={"return_to": return_to})
    assert response.status_code == 302
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["location"].startswith("http://127.0.0.1:")
    handshake = next(cookie for cookie in client.cookies.jar if cookie.name != "wuji_session")
    assert handshake.has_nonstandard_attr("HttpOnly")
    assert handshake.path == "/"
    assert handshake.get_nonstandard_attr("SameSite") == "Lax"
    return response


def authorize(client: httpx.Client, login: httpx.Response) -> str:
    response = client.get(login.headers["location"])
    assert response.status_code == 302
    callback = response.headers["location"]
    assert callback.startswith(str(client.base_url.join("/api/v1/auth/callback")))
    return callback


def finish_callback(client: httpx.Client, callback: str) -> httpx.Response:
    return client.get(callback)


def complete_fixture_login(
    client: httpx.Client,
    manifest: RunManifest,
    scenario: str = "valid",
    return_to: str = "/projects",
    user: str = "protocol_user",
) -> httpx.Response:
    fixture_control(manifest, scenario, user)
    login = begin_login(client, return_to)
    callback = authorize(client, login)
    return finish_callback(client, callback)


def assert_safe_callback_failure(response: httpx.Response) -> str:
    assert response.status_code == 303
    assert response.headers["cache-control"] == "no-store"
    location = response.headers["location"]
    match = LOGIN_ERROR_RE.fullmatch(location)
    assert match, location
    UUID(match.group(2))
    lowered = location.lower()
    assert "code=" not in lowered
    assert "state=" not in lowered
    assert "token=" not in lowered
    session_cookie = response.headers.get_list("set-cookie")
    assert not any(value.lower().startswith("wuji_session=") and "max-age=0" not in value.lower() for value in session_cookie)
    return match.group(1)


def query_value(url: str, name: str) -> str:
    values = parse_qs(urlparse(url).query).get(name, [])
    assert len(values) == 1
    return values[0]
