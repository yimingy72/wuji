"""Scheduler factory: one real application PG session owns the Scheduler lock."""

from deployment_common import Deployment, load_settings
from wuji_core.persistence.snapshots import SnapshotRepository
from wuji_core.scheduling.claims import Scheduler, SchedulerOwnership


def build_scheduler():
    deployment = Deployment(load_settings("scheduler"))
    connection = deployment.connect()
    try:
        ownership = SchedulerOwnership(connection)
        return Scheduler(deployment.uow, ownership=ownership,
            accesses=(deployment.access(),), snapshots=SnapshotRepository(deployment.uow),
            registry=deployment.registry, control=deployment.control,
            credential_issuer=deployment.issuer(),
            completion=deployment.completion)
    except BaseException:
        connection.close()
        raise
