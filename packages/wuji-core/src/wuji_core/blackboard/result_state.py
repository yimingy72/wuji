"""Single projection writer; P04 submissions/receipts remain result authority.

Caller already holds the Task transaction. The database derives status from the
matching stored submission or, for missing output, stored final execution facts.
No model/Agent-provided result state is accepted by this interface.
"""


def project_submission(tx, agent_run_id, submission_id):
    return tx.connection.execute(
        "SELECT vnext.project_run_result(%s,%s,%s,%s,%s)",
        (*tx.owner, agent_run_id, submission_id),
    ).fetchone()[0]


def mark_missing_output(tx, agent_run_id):
    return tx.connection.execute(
        "SELECT vnext.project_run_result(%s,%s,%s,%s,NULL)",
        (*tx.owner, agent_run_id),
    ).fetchone()[0]
