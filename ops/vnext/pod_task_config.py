"""Pure parsing of the runtime host's Task list (no Kubernetes import).

The runtime deployment publishes the Tasks this host must serve, either as the
current `pod_runtime.tasks` list or as the earlier single `task_config` +
`receiver` pair. Keeping this shape check in its own importable module means it
can be verified without the deployment-only Kubernetes client.
"""


def task_entries(config):
    """Return the bounded `(task_id, task_config, receiver)` list to serve."""

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
        if not isinstance(item, dict) or set(item) != {"task_config", "receiver"}:
            raise ValueError("each Task entry carries exactly one config and receiver")
        values = item["task_config"]
        task_id = values.get("task_id") if isinstance(values, dict) else None
        if not isinstance(task_id, str) or not task_id or task_id in seen:
            raise ValueError("each Task entry needs its own Task identifier")
        if not isinstance(item["receiver"], dict):
            raise ValueError("each Task entry needs its own receiver")
        seen.add(task_id)
        entries.append((task_id, values, item["receiver"]))
    return entries


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
