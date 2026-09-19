"""Refresh the deployment's fixed bearer material with a bounded lifetime.

Every consumer of the isolated namespace mounts one of four Secrets, and the
Task Pod supervisor compares the controller bearer byte-for-byte with the copy
its attempt mounted. A rotation is therefore only safe while no runtime attempt
can still serve: this command refuses while any Task is inside its attempt
window or still holds an enabled receiver, unless the operator says otherwise.

The command mints one token per fixed subject with a bounded TTL, patches only
the deployment Secrets, prints only subjects/roles/TTL (never token bytes), and
can roll the Deployments that read a bearer at startup.
"""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CONTEXT = "docker-desktop"
NAMESPACE = "wuji-vnext-test"
BOOTSTRAP_CONFIG_SECRET = "bootstrap-input-topo0915"
SIGNING_KEY_SECRET = "runtime-credentials"
SIGNING_KEY_FIELD = "signing.key"
POSTGRES_LABEL = "wuji.dev/service=postgres"
MIN_TTL_HOURS, MAX_TTL_HOURS = 1, 72
BACKDATE_SECONDS = 30

# secret -> field -> (subject, roles). Every deployment consumer of a bounded
# bearer appears exactly once; nothing here mints an operator bearer, which the
# owner tools mint per action instead.
PLAN = {
    "runtime-credentials": {
        "receiver.token": ("receiver", ["controller"]),
        "service.token": ("pod-controller", ["controller"]),
    },
    "scheduler-credentials": {"service.token": ("scheduler", ["scheduler"])},
    "gates-credentials": {
        "collector.token": ("collector", ["collector"]),
        "service.token": ("gate", ["gate"]),
    },
    "api-credentials": {"service.token": ("operator", ["operator"])},
}
CONSUMER_DEPLOYMENTS = ("api", "runtime", "scheduler", "gates")

# A Task is only counted as live while its attempt window is open (the permit
# the runtime obeys) or while its receiver is still enabled. Stale Runs from old
# Tasks never block a rotation.
LIVE_WINDOW_SQL = """
SELECT
 (SELECT count(*) FROM vnext.task t
   WHERE t.activated_at IS NOT NULL
     AND now() < t.activated_at + make_interval(secs => GREATEST(1,
        COALESCE((t.definition_json::jsonb->'runtime_profile'->'limits'->>'max_elapsed_seconds')::int, 1)))
 ) AS tasks_in_window,
 (SELECT count(*) FROM vnext.scheduler_receiver r WHERE r.enabled) AS enabled_receivers,
 (SELECT count(*) FROM vnext.agent_run a WHERE a.process_state <> 'exited') AS unexited_runs
"""


def parse_ttl_hours(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("ttl_hours must be a number")
    hours = float(value)
    if not MIN_TTL_HOURS <= hours <= MAX_TTL_HOURS:
        raise ValueError(
            "ttl_hours must stay within %d..%d" % (MIN_TTL_HOURS, MAX_TTL_HOURS)
        )
    return hours


def claims_for(subject, roles, *, tenant_id, issuer, audience, ttl_seconds, moment=None):
    """One bounded bearer for one fixed deployment subject."""

    if not subject or not isinstance(roles, list) or not roles:
        raise ValueError("a fixed subject and role set are required")
    if type(ttl_seconds) is not int or ttl_seconds < 60:
        raise ValueError("a bounded bearer lifetime is required")
    now = int((moment or datetime.now(timezone.utc)).timestamp())
    return {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "tenant_id": tenant_id,
        "roles": list(roles),
        "iat": now,
        "nbf": now - BACKDATE_SECONDS,
        "exp": now + ttl_seconds,
        "jti": _jti(),
    }


def _jti():
    from uuid import uuid4

    return str(uuid4())


def mint(claims, *, signing_key_pem):
    from joserfc import jwt
    from joserfc.jwk import RSAKey

    key = RSAKey.import_key(signing_key_pem)
    token = jwt.encode(
        {"alg": "RS256", "kid": "deployment-key"}, claims, key, algorithms=["RS256"]
    )
    return token.decode() if isinstance(token, bytes) else token


def refresh_plan(*, tenant_id, issuer, audience, ttl_seconds, signing_key_pem, moment=None):
    """Mint every planned bearer; returns only bounded metadata per target."""

    material, summary = {}, []
    for secret, fields in sorted(PLAN.items()):
        patch = {}
        for field, (subject, roles) in sorted(fields.items()):
            token = mint(
                claims_for(
                    subject,
                    roles,
                    tenant_id=tenant_id,
                    issuer=issuer,
                    audience=audience,
                    ttl_seconds=ttl_seconds,
                    moment=moment,
                ),
                signing_key_pem=signing_key_pem,
            )
            patch[field] = base64.b64encode(token.encode()).decode()
            summary.append(
                {
                    "secret": secret,
                    "field": field,
                    "subject": subject,
                    "roles": list(roles),
                    "ttl_seconds": ttl_seconds,
                }
            )
        material[secret] = patch
    return material, summary


def guard_live_attempts(counts, *, allow=False):
    """Refuse a rotation that could strand a running attempt's bearer."""

    in_window = int(counts.get("tasks_in_window", 0))
    receivers = int(counts.get("enabled_receivers", 0))
    if (in_window or receivers) and not allow:
        raise RuntimeError(
            "refusing to rotate bearers: tasks_in_window=%d enabled_receivers=%d"
            " (pass --allow-active-attempts only when those attempts are known dead)"
            % (in_window, receivers)
        )
    return {
        "tasks_in_window": in_window,
        "enabled_receivers": receivers,
        "unexited_runs": int(counts.get("unexited_runs", 0)),
    }


def _kubectl(args, *, context, namespace, check=True, input_text=None):
    command = ["kubectl", "--context", context, "--namespace", namespace, *args]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False, input=input_text)
    if check and result.returncode:
        raise RuntimeError("kubectl %s failed" % (args[0] if args else "?"))
    return result.stdout


def _secret_value(context, namespace, name, field):
    raw = _kubectl(
        ["get", "secret", name, "-o", "jsonpath={.data.%s}" % field.replace(".", "\\.")],
        context=context,
        namespace=namespace,
    ).strip()
    if not raw:
        raise RuntimeError("secret %s has no %s" % (name, field))
    return base64.b64decode(raw)


def deployment_identity(context, namespace):
    raw = _kubectl(
        ["get", "secret", BOOTSTRAP_CONFIG_SECRET, "-o", "jsonpath={.data.config\\.json}"],
        context=context,
        namespace=namespace,
    ).strip()
    if not raw:
        raise RuntimeError("bootstrap config secret is missing")
    document = json.loads(base64.b64decode(raw))
    owner = document.get("owner")
    identity = document.get("identity")
    database = document.get("database")
    roles = document.get("roles")
    if (
        not isinstance(owner, list)
        or len(owner) != 3
        or not isinstance(identity, dict)
        or not isinstance(database, dict)
        or not isinstance(roles, dict)
        or not isinstance(roles.get("wuji_migration"), str)
    ):
        raise RuntimeError("bootstrap config does not describe the deployment")
    return {
        "tenant_id": str(owner[0]),
        "issuer": identity.get("issuer"),
        "audience": identity.get("audience"),
        "database": database,
        "migration_password": roles["wuji_migration"],
    }


def live_counts(context, namespace, identity, *, timeout=30):
    pod = _kubectl(
        ["get", "pods", "-l", POSTGRES_LABEL, "-o", "jsonpath={.items[0].metadata.name}"],
        context=context,
        namespace=namespace,
    ).strip()
    if not pod:
        raise RuntimeError("postgres pod is not running")
    result = subprocess.run(
        [
            "kubectl", "--context", context, "--namespace", namespace,
            "exec", "-i", pod, "--",
            "sh", "-c", 'IFS= read -r PGPASSWORD\nexport PGPASSWORD\nexec psql -U wuji_migration -d "$1" -tAc "$2"',
            "sh", identity["database"]["dbname"], LIVE_WINDOW_SQL,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        input=identity["migration_password"] + "\n",
        check=False,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError("live-attempt query failed")
    fields = result.stdout.strip().split("|")
    if len(fields) != 3 or not all(field.strip().isdigit() for field in fields):
        raise RuntimeError("live-attempt query returned an unexpected shape")
    return dict(zip(("tasks_in_window", "enabled_receivers", "unexited_runs"), fields))


def patch_secrets(material, *, context, namespace):
    patched = []
    for secret, fields in sorted(material.items()):
        document = json.dumps({"data": fields})
        _kubectl(
            ["patch", "secret", secret, "--type", "merge", "--patch-file", "/dev/stdin"],
            context=context,
            namespace=namespace,
            input_text=document,
        )
        patched.append(secret)
    return patched


def restart_consumers(*, context, namespace):
    rolled = []
    for name in CONSUMER_DEPLOYMENTS:
        _kubectl(["rollout", "restart", "deployment/%s" % name], context=context, namespace=namespace)
        rolled.append(name)
    return rolled


def main(argv=None):
    parser = argparse.ArgumentParser(description="bounded deployment bearer refresh")
    parser.add_argument("--context", default=CONTEXT)
    parser.add_argument("--namespace", default=NAMESPACE)
    parser.add_argument("--ttl-hours", type=float, default=24.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-active-attempts", action="store_true")
    parser.add_argument(
        "--restart",
        action="store_true",
        help="roll the Deployments that read a bearer at startup",
    )
    args = parser.parse_args(argv)
    try:
        ttl_hours = parse_ttl_hours(args.ttl_hours)
    except ValueError as error:
        raise SystemExit(str(error))
    identity = deployment_identity(args.context, args.namespace)
    counts = live_counts(args.context, args.namespace, identity)
    allowed = guard_live_attempts(counts, allow=args.allow_active_attempts)
    signing_key = _secret_value(
        args.context, args.namespace, SIGNING_KEY_SECRET, SIGNING_KEY_FIELD
    )
    material, summary = refresh_plan(
        tenant_id=identity["tenant_id"],
        issuer=identity["issuer"],
        audience=identity["audience"],
        ttl_seconds=int(ttl_hours * 3600),
        signing_key_pem=signing_key,
    )
    report = {
        "context": args.context,
        "namespace": args.namespace,
        "ttl_seconds": int(ttl_hours * 3600),
        "live": allowed,
        "dry_run": bool(args.dry_run),
        "planned": summary,
    }
    if args.dry_run:
        print(json.dumps(report, sort_keys=True))
        return 0
    report["patched"] = patch_secrets(
        material, context=args.context, namespace=args.namespace
    )
    if args.restart:
        report["restarted"] = restart_consumers(
            context=args.context, namespace=args.namespace
        )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
