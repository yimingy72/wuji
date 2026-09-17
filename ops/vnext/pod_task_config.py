"""Pure parsing of the runtime host's Task list (no Kubernetes import).

The runtime deployment publishes the Tasks this host must serve, either as the
current `pod_runtime.tasks` list or as the earlier single `task_config` +
`receiver` pair. Keeping this shape check in its own importable module means it
can be verified without the deployment-only Kubernetes client.
"""


ENTRY_KEYS = frozenset({"task_config", "receiver"})
ENTRY_KEYS_WITH_ENDPOINT = ENTRY_KEYS | {"service_names", "supervisor_url"}


def task_entries(config):
    """Return the bounded `(task_id, task_config, receiver)` list to serve.

    A Task may also publish its own `service_names` and `supervisor_url`; entries
    without them keep using the deployment's fixed Service names, which is what a
    single-Task deployment configures.
    """

    if not isinstance(config, dict):
        raise ValueError("runtime pod configuration is required")
    raw = config.get("tasks")
    if raw is None:
        if "task_config" not in config or "receiver" not in config:
            raise ValueError("runtime pod configuration carries no Task")
        raw = [{"task_config": config["task_config"], "receiver": config["receiver"]}]
    if not isinstance(raw, list) or not raw or len(raw) > 64:
        raise ValueError("a bounded non-empty Task list is required")
    entries, seen = [], set()
    for item in raw:
        if not isinstance(item, dict) or frozenset(item) not in {
            ENTRY_KEYS,
            ENTRY_KEYS_WITH_ENDPOINT,
        }:
            raise ValueError("each Task entry carries exactly one config and receiver")
        values = item["task_config"]
        task_id = values.get("task_id") if isinstance(values, dict) else None
        if not isinstance(task_id, str) or not task_id or task_id in seen:
            raise ValueError("each Task entry needs its own Task identifier")
        if not isinstance(item["receiver"], dict):
            raise ValueError("each Task entry needs its own receiver")
        entry_service_names(item, {"agent": "task-agent", "kali": "task-kali"})
        task_supervisor_url(item)
        seen.add(task_id)
        entries.append((task_id, values, item["receiver"]))
    return entries


def entry_has_endpoint(config, task_id):
    """Whether this Task published its own Service names."""

    raw = config.get("tasks") if isinstance(config, dict) else None
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        values = item.get("task_config")
        if isinstance(values, dict) and values.get("task_id") == task_id:
            return "service_names" in item
    return False


def entry_service_names(entry, default):
    """The per-Task Service names, or the deployment's fixed pair."""

    names = entry.get("service_names") if isinstance(entry, dict) else None
    if names is None:
        return dict(default)
    if (
        not isinstance(names, dict)
        or set(names) != {"agent", "kali"}
        or any(
            not isinstance(value, str)
            or not 1 <= len(value) <= 63
            or not value.islower()
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in value)
            or value.startswith("-")
            or value.endswith("-")
            for value in names.values()
        )
    ):
        raise ValueError("per-Task Service names must be DNS labels")
    return dict(names)


def task_supervisor_url(entry):
    """The Task's own supervisor origin, or nothing when it has none."""

    url = entry.get("supervisor_url") if isinstance(entry, dict) else None
    if url is None:
        return None
    if not isinstance(url, str) or not 1 <= len(url) <= 256 or not url.startswith("https://"):
        raise ValueError("a per-Task supervisor URL must be a bounded HTTPS origin")
    return url


def start_eligible_task_ids(observations):
    """Tasks whose own Pod reported ready; everything else keeps reconciling."""

    if not isinstance(observations, dict):
        raise ValueError("per-Task observations are required")
    return tuple(
        sorted(
            task_id
            for task_id, value in observations.items()
            if getattr(value, "state", value) == "ready"
        )
    )
