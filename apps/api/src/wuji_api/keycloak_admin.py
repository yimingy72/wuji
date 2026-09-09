"""Trusted, idempotent Keycloak realm/client/user provisioning for local runs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx2


class KeycloakAdminError(RuntimeError):
    pass


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


class KeycloakAdmin:
    def __init__(self, run: dict[str, Any]):
        self.run = run
        self.base_url = run["urls"]["idp"].rstrip("/")
        credentials = run["credentials"]["oidc_keycloak"]
        self.username = credentials["admin_username"]
        self.password = credentials["admin_password"]
        self.client = httpx2.Client(timeout=15.0)

    def close(self) -> None:
        self.client.close()

    def _token(self) -> str:
        response = self.client.post(
            f"{self.base_url}/realms/master/protocol/openid-connect/token",
            data={
                "client_id": "admin-cli",
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
            },
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise KeycloakAdminError("Keycloak admin token response is invalid")
        return token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token()}"}

    def provision(self) -> dict[str, int]:
        headers = self._headers()
        realm = self.run["realm"]["name"]
        encoded_realm = quote(realm, safe="")
        realm_url = f"{self.base_url}/admin/realms/{encoded_realm}"
        response = self.client.get(realm_url, headers=headers)
        created_realm = 0
        if response.status_code == 404:
            response = self.client.post(
                f"{self.base_url}/admin/realms",
                headers=headers,
                json={
                    "realm": realm,
                    "enabled": True,
                    "sslRequired": "none",
                    "registrationAllowed": False,
                    "loginWithEmailAllowed": True,
                    "resetPasswordAllowed": False,
                    "rememberMe": False,
                },
            )
            response.raise_for_status()
            created_realm = 1
        else:
            response.raise_for_status()

        credentials = self.run["credentials"]["oidc_keycloak"]
        client_id = credentials["client_id"]
        clients_url = f"{realm_url}/clients"
        response = self.client.get(
            clients_url, headers=headers, params={"clientId": client_id, "search": "true"}
        )
        response.raise_for_status()
        matches = [item for item in response.json() if item.get("clientId") == client_id]
        client_representation = {
            "clientId": client_id,
            "name": "Wuji Platform",
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "secret": credentials["client_secret"],
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False,
            "redirectUris": [f"{self.run['urls']['web']}/api/v1/auth/callback"],
            "webOrigins": [self.run["urls"]["web"]],
            "attributes": {
                "pkce.code.challenge.method": "S256",
                "post.logout.redirect.uris": "+",
            },
            "defaultClientScopes": ["profile", "email", "roles", "web-origins"],
        }
        created_client = 0
        if matches:
            internal_client_id = matches[0]["id"]
            client_representation["id"] = internal_client_id
            response = self.client.put(
                f"{clients_url}/{quote(internal_client_id, safe='')}",
                headers=headers,
                json=client_representation,
            )
        else:
            response = self.client.post(clients_url, headers=headers, json=client_representation)
            created_client = 1
        response.raise_for_status()

        created_users = 0
        for user in self.run["seed_users"].values():
            response = self.client.get(
                f"{realm_url}/users",
                headers=headers,
                params={"username": user["username"], "exact": "true"},
            )
            response.raise_for_status()
            users = response.json()
            if users:
                keycloak_user_id = users[0]["id"]
            else:
                representation = {
                    "id": user["sub"],
                    "username": user["username"],
                    "enabled": True,
                    "email": user.get("email"),
                    "emailVerified": True,
                    "firstName": user["display_name"],
                    "lastName": "User",
                    "requiredActions": [],
                }
                response = self.client.post(
                    f"{realm_url}/users", headers=headers, json=representation
                )
                response.raise_for_status()
                location = response.headers.get("location", "")
                keycloak_user_id = location.rstrip("/").rsplit("/", 1)[-1]
                if not keycloak_user_id:
                    raise KeycloakAdminError("Keycloak did not identify the created user")
                created_users += 1
            user["sub"] = keycloak_user_id
            response = self.client.put(
                f"{realm_url}/users/{quote(keycloak_user_id, safe='')}",
                headers=headers,
                json={
                    "id": keycloak_user_id,
                    "username": user["username"],
                    "enabled": True,
                    "email": user.get("email"),
                    "emailVerified": True,
                    "firstName": user["display_name"],
                    "lastName": "User",
                    "requiredActions": [],
                },
            )
            response.raise_for_status()
            response = self.client.put(
                f"{realm_url}/users/{quote(keycloak_user_id, safe='')}/reset-password",
                headers=headers,
                json={"type": "password", "temporary": False, "value": user["password"]},
            )
            response.raise_for_status()
        return {
            "realms_created": created_realm,
            "clients_created": created_client,
            "users_created": created_users,
        }


def provision_keycloak(run_path: Path, run: dict[str, Any]) -> dict[str, int]:
    admin = KeycloakAdmin(run)
    try:
        result = admin.provision()
    except httpx2.HTTPError as error:
        raise KeycloakAdminError from error
    finally:
        admin.close()
    _write_private_json(run_path, run)
    return result
