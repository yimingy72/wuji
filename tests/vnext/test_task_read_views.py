from __future__ import annotations

import json

from test_task_creation import OWNER, create, creation_case


def bearer(token):
    return {"Authorization": "Bearer " + token}


def seed_read_view_records(connection, task_id):
    owner = (OWNER[0], OWNER[1], task_id)
    connection.execute(
        """INSERT INTO vnext.work_item(
          tenant_id,project_id,task_id,work_item_id,state,kind,blocked_reason)
        VALUES(%s,%s,%s,%s,'running','explore',NULL)""",
        (*owner, "work-visible"),
    )
    connection.execute(
        """INSERT INTO vnext.scheduler_work(
          tenant_id,project_id,task_id,work_item_id,key_digest,key_json,priority)
        VALUES(%s,%s,%s,%s,%s,%s,0)""",
        (*owner, "work-visible", "a" * 64, '{"kind":"fixture"}'),
    )
    connection.execute(
        """INSERT INTO vnext.agent_run(
          tenant_id,project_id,task_id,agent_run_id,work_item_id,receiver_id,
          environment_ref,model_mode)
        VALUES(%s,%s,%s,'run-visible','work-visible','receiver-fixture',
          'environment-fixture','synthetic')""",
        owner,
    )
    connection.execute(
        """INSERT INTO vnext.tool_call(
          tenant_id,project_id,task_id,tool_call_id,session_lineage,message_id,
          provider_call_id,tool_definition_version,work_item_id)
        VALUES(%s,%s,%s,'tool-call','session-fixture','message-fixture',
          'provider-fixture','definition-fixture','work-visible')""",
        owner,
    )
    connection.execute(
        """INSERT INTO vnext.criterion_judgment(
          tenant_id,project_id,task_id,judgment_id,criterion_id,criterion_revision,
          status,applicability,source_receipt_json)
        VALUES(%s,%s,%s,%s,'version',1,'met','stale','{}')""",
        (*owner, "judgment-stale"),
    )
    connection.execute(
        """UPDATE vnext.goal_criterion SET current_judgment_id='judgment-stale'
        WHERE tenant_id=%s AND project_id=%s AND task_id=%s AND criterion_id='version'""",
        owner,
    )
    events = [
        (1, "task.started", {"task_id": task_id}),
        (2, "tool.dispatch_requested", {
            "tool_call_id": "tool-call", "tool_attempt_id": "attempt", "executor_ref": "executor",
        }),
        (3, "work.stop_requested", {
            "work_item_id": "work-visible", "reason": "operator pause", "private": "do-not-return",
        }),
    ]
    for seq, kind, payload in events:
        connection.execute(
            """INSERT INTO vnext.outbox(
              tenant_id,project_id,task_id,event_seq,kind,payload_json,access_level)
            VALUES(%s,%s,%s,%s,%s,%s,0)""",
            (*owner, seq, kind, json.dumps(payload)),
        )
    connection.execute(
        "UPDATE vnext.task SET event_seq=3,board_revision=3 WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
        owner,
    )


def test_task_overview_and_activity_are_acl_scoped_and_cursor_bound(
    db_environment, audit_directory
):
    with creation_case(db_environment, audit_directory) as case:
        created = create(case, key="read-view-task")
        assert created.status_code == 201, created.text
        task_id = created.json()["task_id"]
        reader = case.provider.issue(
            subject="reader-fixture", tenant_id=OWNER[0], roles=["reader"]
        )
        outsider = case.provider.issue(
            subject="outsider-fixture", tenant_id=OWNER[0], roles=["reader"]
        )
        with db_environment.migration_connection() as connection:
            seed_read_view_records(connection, task_id)
            for identity in ("exec-1", "exec-2"):
                connection.execute(
                    """INSERT INTO vnext.tool_attempt(
                      tenant_id,project_id,task_id,tool_attempt_id,tool_call_id,
                      agent_run_id,evidence_origin,capture_layer,receipt_json,
                      status,permit_json,process_action)
                    VALUES(%s,%s,%s,%s,'tool-call','run-visible',
                      'fixture_capture','tool_receipt','{}','complete',%s,'exec')""",
                    (*OWNER[:2], task_id, identity, json.dumps({
                        "arguments": {"command": f"printf {identity}"}
                    })),
                )
                connection.execute(
                    """INSERT INTO vnext.process_execution(
                      tenant_id,project_id,task_id,tool_attempt_id,agent_run_id,
                      state,deadline,finished_at,exit_code,output_completeness)
                    VALUES(%s,%s,%s,%s,'run-visible','exited',
                      clock_timestamp(),clock_timestamp(),0,'complete')""",
                    (*OWNER[:2], task_id, identity),
                )
            connection.execute(
                """INSERT INTO vnext.task_access(
                  tenant_id,project_id,task_id,subject,can_read,clearance)
                VALUES(%s,%s,%s,%s,true,1)""",
                (OWNER[0], OWNER[1], task_id, "reader-fixture"),
            )

        overview = case.client.get(
            f"/api/v2/tasks/{task_id}/overview", headers=bearer(reader)
        )
        assert overview.status_code == 200, overview.text
        document = overview.json()
        assert document["schema_version"] == "wuji.task-overview.v1"
        assert document["budget"] == {"amount": "5", "currency": "USD"}
        assert document["goal"]["criteria"][0]["judgment_status"] == "met"
        assert document["goal"]["criteria"][0]["judgment_applicability"] == "stale"
        assert document["current_work"][0]["work_item_id"] == "work-visible"
        assert document["workspace_capabilities"] == {
            "work_files": False,
            "shared_versions": False,
            "command_output": False,
        }
        assert "spent" not in json.dumps(document)
        assert document["runtime"]["state"] == "not_started"

        commands = case.client.get(
            f"/api/v2/tasks/{task_id}/command-inventory?limit=1",
            headers=bearer(reader),
        )
        assert commands.status_code == 200, commands.text
        assert [item["exec_id"] for item in commands.json()["items"]] == ["exec-1"]
        assert commands.json()["items"][0]["command"] == "printf exec-1"
        assert commands.json()["items"][0]["assurance"] == "executor_reported"
        following = case.client.get(
            f"/api/v2/tasks/{task_id}/command-inventory?limit=1&after={commands.json()['next_after']}",
            headers=bearer(reader),
        )
        assert following.status_code == 200, following.text
        assert [item["exec_id"] for item in following.json()["items"]] == ["exec-2"]
        assert following.json()["next_after"] is None
        publications = case.client.get(
            f"/api/v2/tasks/{task_id}/publications", headers=bearer(reader)
        )
        assert publications.status_code == 200, publications.text
        assert publications.json()["items"] == []

        denied = case.client.get(
            f"/api/v2/tasks/{task_id}/overview", headers=bearer(outsider)
        )
        assert denied.status_code == 404
        assert case.client.get(
            f"/api/v2/tasks/{task_id}/command-inventory", headers=bearer(outsider)
        ).status_code == 404

        first = case.client.get(
            f"/api/v2/tasks/{task_id}/activity?importance=all&limit=2",
            headers=bearer(reader),
        )
        assert first.status_code == 200, first.text
        page = first.json()
        assert [item["category"] for item in page["items"]] == ["work", "tool"]
        assert page["items"][0]["summary"] == "停止工作请求已受理"
        assert page["items"][1]["work_item_id"] == "work-visible"
        assert "do-not-return" not in first.text
        assert page["next_cursor"]

        filtered = case.client.get(
            f"/api/v2/tasks/{task_id}/activity?importance=all&work_item_id=work-visible&limit=10",
            headers=bearer(reader),
        )
        assert filtered.status_code == 200, filtered.text
        assert [item["activity_id"] for item in filtered.json()["items"]] == [
            "event-3", "event-2"
        ]

        second = case.client.get(
            f"/api/v2/tasks/{task_id}/activity?importance=all&limit=2&cursor={page['next_cursor']}",
            headers=bearer(reader),
        )
        assert second.status_code == 200, second.text
        assert [item["summary"] for item in second.json()["items"]] == ["任务已启动"]

        mismatched = case.client.get(
            f"/api/v2/tasks/{task_id}/activity?importance=all&category=work&cursor={page['next_cursor']}",
            headers=bearer(reader),
        )
        assert mismatched.status_code == 422
        both = case.client.get(
            f"/api/v2/tasks/{task_id}/activity?importance=all&cursor={page['next_cursor']}&after_cursor={page['latest_cursor']}",
            headers=bearer(reader),
        )
        assert both.status_code == 422

        with db_environment.migration_connection() as connection:
            for seq, kind, payload in [
                (4, "execution.observed", {"agent_run_id": "run-visible", "kind": "exited"}),
                (5, "work.condition_changed", {"work_item_id": "work-visible", "state": "running"}),
                (6, "work.condition_changed", {"work_item_id": "work-visible", "state": "running"}),
            ]:
                connection.execute(
                    """INSERT INTO vnext.outbox(
                      tenant_id,project_id,task_id,event_seq,kind,payload_json,access_level)
                    VALUES(%s,%s,%s,%s,%s,%s,0)""",
                    (OWNER[0], OWNER[1], task_id, seq, kind, json.dumps(payload)),
                )
            connection.execute(
                "UPDATE vnext.task SET event_seq=6,board_revision=6 WHERE tenant_id=%s AND project_id=%s AND task_id=%s",
                (OWNER[0], OWNER[1], task_id),
            )
        newer = case.client.get(
            f"/api/v2/tasks/{task_id}/activity?importance=all&limit=1&after_cursor={page['latest_cursor']}",
            headers=bearer(reader),
        )
        assert newer.status_code == 200, newer.text
        assert newer.json()["items"] == [{
            **newer.json()["items"][0],
            "status": "info",
            "summary": "执行进程已退出，结果仍需核对",
            "work_item_id": "work-visible",
        }]
        remaining = case.client.get(
            f"/api/v2/tasks/{task_id}/activity?importance=all&after_cursor={newer.json()['latest_cursor']}",
            headers=bearer(reader),
        )
        assert remaining.status_code == 200, remaining.text
        assert [item["activity_id"] for item in remaining.json()["items"]] == [
            "event-5", "event-6"
        ]
