"""MAF public middleware bridge for bounded blackboard update notices."""

import asyncio

from agent_framework import ChatMiddleware, ContextProvider, Message

from wuji_core.contracts import generated as wire
from wuji_core.http import canonical_json_bytes


NOTICE_SOURCE_ID = "wuji_knowledge_notices"


class _NoticeMiddleware(ChatMiddleware):
    def __init__(self, *, host, assignment, state, limit):
        self.host, self.assignment, self.state, self.limit = (
            host,
            assignment,
            state,
            limit,
        )
        # The SDK finalizes nested per-model streams only when the outer Agent
        # stream settles. Keep the acknowledged candidate in this one-Run
        # middleware so the next model call does not reread the same page. Only
        # the result hook persists it into recoverable Session state.
        self.cursor = state.get("cursor")

    async def process(self, context, call_next):
        if not context.stream:
            raise ValueError("knowledge notices require the native streaming boundary")
        page = wire.KnowledgeNoticesPageV1.model_validate(
            await asyncio.to_thread(
                self.host.knowledge_notices,
                self.assignment,
                cursor=self.cursor,
                limit=self.limit,
            )
        )
        self.cursor = page.next_cursor
        if page.notices:
            message = {
                "schema_version": "wuji.knowledge-notice-message.v1",
                "instruction": (
                    "Blackboard metadata changed. Read an exact notice ref with "
                    "knowledge_read only if it is relevant; this notice is not "
                    "evidence content."
                ),
                "notices": [
                    item.model_dump(mode="json") for item in page.notices
                ],
            }
            context.messages.append(
                Message(
                    role="user",
                    contents=[canonical_json_bytes(message).decode("utf-8")],
                )
            )

        async def advance(response):
            self.state["cursor"] = page.next_cursor
            return response

        context.stream_result_hooks.append(advance)
        await call_next()


class KnowledgeNoticeProvider(ContextProvider):
    """Poll once per model call; persist only the acknowledged opaque cursor."""

    def __init__(self, *, host, assignment, limit=16):
        super().__init__(NOTICE_SOURCE_ID)
        if type(limit) is not int or not 1 <= limit <= 16:
            raise ValueError("knowledge notice limit must be bounded")
        self.host, self.assignment, self.limit = host, assignment, limit
        self._middleware = None

    async def before_run(self, *, agent, session, context, state):
        if set(state) - {"cursor"} or (
            "cursor" in state
            and (not isinstance(state["cursor"], str) or not state["cursor"])
        ):
            raise ValueError("restored knowledge notice state is invalid")
        self._middleware = _NoticeMiddleware(
            host=self.host,
            assignment=self.assignment,
            state=state,
            limit=self.limit,
        )
        context.extend_middleware(self.source_id, self._middleware)

    async def after_run(self, *, agent, session, context, state):
        if self._middleware is not None and self._middleware.cursor is not None:
            state["cursor"] = self._middleware.cursor
        self._middleware = None
