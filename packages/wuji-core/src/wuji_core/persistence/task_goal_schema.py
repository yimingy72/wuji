"""Materialize the immutable TaskCreate Goal criteria at Task creation."""

from wuji_core.persistence.problem_core_schema import HEAD as PARENT_HEAD
from wuji_core.persistence.task_creation_schema import _CREATE_TASK


HEAD = "vnext_0033_task_goal_criteria"


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0032_problem_core":
        raise ValueError("task Goal migration parent changed")
    connection.execute(_CREATE_TASK.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1))
    connection.execute("INSERT INTO vnext.schema_migration(head) VALUES(%s)", (HEAD,))
