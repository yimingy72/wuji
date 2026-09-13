"""Shared pool locks precede Task on reserve, control and release paths."""

from wuji_core.persistence.uow import DomainError, row


def prelock_pools(connection, owner):
    cursor = connection.execute(
        """SELECT p.* FROM vnext.capacity_pool p JOIN vnext.task_capacity_pool t USING(pool_key)
        WHERE t.tenant_id=%s AND t.project_id=%s AND t.task_id=%s
        ORDER BY CASE WHEN p.tier='tenant' THEN 1 ELSE 0 END,p.pool_key FOR UPDATE OF p""",
        owner,
    )
    pools = []
    while (pool := row(cursor)) is not None:
        if pool["tier"] == "tenant" and pool["tenant_id"] != owner[0]:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        pools.append(pool)
    if not any(p["tier"] == "global" for p in pools) or not any(
        p["tier"] == "tenant" for p in pools
    ):
        raise DomainError("CAPABILITY_UNAVAILABLE", 503)
    return tuple(pools)


class CapacityService:
    @staticmethod
    def reserve(tx, run_id):
        if not tx.capacity_pools or not tx.permissions["can_admit"]:
            raise DomainError("NOT_FOUND_OR_FORBIDDEN")
        run = row(
            tx.connection.execute(
                "SELECT * FROM vnext.agent_run WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s",
                (*tx.owner, run_id),
            )
        )
        if not run:
            raise DomainError("INVALID_REFERENCE", 422)
        work = row(
            tx.connection.execute(
                "SELECT * FROM vnext.work_item WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s FOR UPDATE",
                (*tx.owner, run["work_item_id"]),
            )
        )
        held = tx.connection.execute(
            "SELECT 1 FROM vnext.work_suspension WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND work_item_id=%s LIMIT 1",
            (*tx.owner, run["work_item_id"]),
        ).fetchone()
        if (
            not work
            or held
            or work["desired_state"] != "run"
            or work["state"] not in {"ready", "leased"}
            or work["current_run_id"] != run_id
            or work["run_epoch"] != run["run_epoch"]
            or run["stop_kind"] is not None
        ):
            raise DomainError("STALE_EXECUTION", 409)
        # P09 must call after its full admission checks, before committing Run/outbox.
        from wuji_core.execution.states import task_can_run

        if (
            not task_can_run(tx.task)
            or not run["execution_allowed"]
            or run["execution_epoch"] != tx.task["execution_epoch"]
            or run["runtime_attempt"] != tx.task["runtime_attempt"]
        ):
            raise DomainError("STALE_EXECUTION", 409)
        for pool in tx.capacity_pools:
            old = row(
                tx.connection.execute(
                    "SELECT state FROM vnext.capacity_reservation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND pool_key=%s",
                    (*tx.owner, run_id, pool["pool_key"]),
                )
            )
            if old:
                if old["state"] == "released":
                    raise DomainError("STALE_EXECUTION", 409)
                continue
            updated = tx.connection.execute(
                "UPDATE vnext.capacity_pool SET used=used+1 WHERE pool_key=%s AND used<capacity RETURNING used",
                (pool["pool_key"],),
            ).fetchone()
            if not updated:
                raise DomainError("LIMIT_BLOCKED", 409)
            tx.connection.execute(
                "INSERT INTO vnext.capacity_reservation(tenant_id,project_id,task_id,agent_run_id,pool_key,state) VALUES(%s,%s,%s,%s,%s,'reserved')",
                (*tx.owner, run_id, pool["pool_key"]),
            )

    @staticmethod
    def observe(tx, run):
        if not tx.capacity_pools:
            raise DomainError("CAPABILITY_UNAVAILABLE", 503)
        observation = row(
            tx.connection.execute(
                "SELECT * FROM vnext.execution_observation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND receipt_id=%s AND agent_run_id=%s",
                (*tx.owner, run["last_observation_id"], run["agent_run_id"]),
            )
        )
        if not observation:
            raise DomainError("OPERATION_UNKNOWN", 409)
        release = run["process_state"] == "exited" and observation["kind"] in {
            "not_started",
            "exited",
            "environment_stopped",
        }
        for pool in tx.capacity_pools:
            old = row(
                tx.connection.execute(
                    "SELECT state FROM vnext.capacity_reservation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND pool_key=%s",
                    (*tx.owner, run["agent_run_id"], pool["pool_key"]),
                )
            )
            if not old or old["state"] == "released":
                continue
            state = "released" if release else "running_or_unknown"
            tx.connection.execute(
                "UPDATE vnext.capacity_reservation SET state=%s WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND pool_key=%s",
                (state, *tx.owner, run["agent_run_id"], pool["pool_key"]),
            )
            if release:
                tx.connection.execute(
                    "UPDATE vnext.capacity_pool SET used=used-1 WHERE pool_key=%s AND used>0",
                    (pool["pool_key"],),
                )


def operations_settled(tx, run_id):
    status = tx.connection.execute(
        "SELECT status FROM vnext.run_operation_settlement WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s",
        (*tx.owner, run_id),
    ).fetchone()
    conflict = tx.connection.execute(
        "SELECT 1 FROM vnext.resource_reservation WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND agent_run_id=%s AND state<>'released' LIMIT 1",
        (*tx.owner, run_id),
    ).fetchone()
    return bool(status and status[0] == "settled" and not conflict)
