"""Public MAF history observation and bounded, snapshot-owned file storage.

Nothing in this module chooses the next model turn or implements compaction.
The native provider owns history persistence; the platform owns publication.
"""

from hashlib import sha256

from agent_framework import AgentFileStore, ContextProvider, FileStoreEntry, InMemoryHistoryProvider, Message

from wuji_core.http import canonical_json_bytes, strict_json_loads


def native_messages(messages):
    """Copy the complete public serialization, including exclusion annotations."""
    return tuple(strict_json_loads(canonical_json_bytes(m.to_dict())) for m in messages)


def digest(value):
    return sha256(canonical_json_bytes(value)).hexdigest()


def locate_content(messages, content_id):
    """Return a coordinate in a fixed transcript, never a fabricated message ID."""
    from wuji_core.contracts.sessions import MessagePosition

    matches = []
    for index, message in enumerate(messages):
        for offset, content in enumerate(message.get("contents", [])):
            if content.get("id") == content_id:
                matches.append((content.get("type") != "function_call", index, offset))
    if not matches:
        raise ValueError("native content is absent from the fixed history")
    matches.sort()
    preferred = [item for item in matches if item[0] == matches[0][0]]
    if len(preferred) != 1:
        raise ValueError("native content has an ambiguous history coordinate")
    _, index, offset = preferred[0]
    message = messages[index]
    return MessagePosition(
        message_index=index, content_index=offset,
        message_digest=digest(message), content_digest=digest(message["contents"][offset]),
        native_message_id=message.get("message_id"),
    )


class HistoryArchive(InMemoryHistoryProvider):
    """Retain native history and immutable observations of pre-compaction bytes."""

    def __init__(self, *, compatibility, limits):
        from wuji_core.contracts.sessions import SessionCompatibility, SessionLimits

        self.compatibility = SessionCompatibility.model_validate(compatibility)
        self.limits = SessionLimits.model_validate(limits)
        profile = self.compatibility.profile_snapshot["body"]
        super().__init__(source_id=profile["history_source_id"], skip_excluded=False)
        self._scope = None
        self.messages = ()
        self.observations = {}
        self.model_observations = {}
        self.call_bindings = ()
        self.tool_receipts = ()
        self.frontier = None
        self.object_refs = ()
        self.model_identity = None
        self.published = None

    def bind_context(self, *, session_id, session_lineage, assignment, context):
        scope = {
            "session_id": session_id, "session_lineage": session_lineage,
            "work_item_id": assignment.identity.work_item_id,
            "snapshot_id": context.snapshot_id,
            "read_set": tuple(context.read_set),
        }
        if self._scope is not None and self._scope != scope:
            raise ValueError("one history provider owns one fixed Session/input")
        self._scope = scope

    def restore_observations(self, published):
        """Keep the pinned original bytes when a later native run compacts again."""
        self.published = published
        self._retain(published.history.messages)
        for ref in published.history.frontier.archived_history_refs:
            body = ref.model_dump(mode="json")
            data = published.object_bytes[body["id"] + "@" + body["version"]]
            archive = strict_json_loads(data)
            if archive.get("schema_version") != "wuji.session.history-archive.v1":
                raise ValueError("unsupported immutable history archive")
            self._retain(archive["messages"])

    def _retain(self, messages):
        for message in messages:
            self.observations.setdefault(digest(message), message)
        if (
            len(messages) > self.limits.max_messages
            or len(self.observations) > self.limits.max_messages
            or len(canonical_json_bytes(tuple(self.observations.values()))) > self.limits.max_total_bytes
        ):
            raise ValueError("native history exceeds the fixed Session limits")

    async def save_messages(self, session_id, messages, *, state=None, **kwargs):
        await super().save_messages(session_id, messages, state=state, **kwargs)
        saved = native_messages(await super().get_messages(session_id, state=state))
        self._retain(saved)
        if self.model_identity is not None and self.model_identity.attempt_id is not None:
            attempt = self.model_identity.attempt_id
            observed = native_messages(messages)
            prior = self.model_observations.setdefault(attempt, {})
            for message in observed:
                prior[digest(message)] = message

    def observe_messages(self, messages, *, model_attempt_id, call_bindings, tool_receipts):
        self.messages = native_messages(messages)
        self._retain(self.messages)
        self.call_bindings = tuple(call_bindings)
        self.tool_receipts = tuple(tool_receipts)
        # This final observation does not attribute old history to the last call.
        # Per-service-call associations come from the public save_messages hook.
        if model_attempt_id is not None and model_attempt_id not in self.model_observations:
            raise ValueError("final model call was not observed by the history provider")

    def export(self):
        from wuji_core.contracts.sessions import HistoryRoot

        if self._scope is None or self.frontier is None or not self.messages:
            raise ValueError("history lacks a bound, observed operation frontier")
        return HistoryRoot(
            **self._scope, message_end=len(self.messages), messages=self.messages,
            frontier=self.frontier, compatibility=self.compatibility,
            object_refs=self.object_refs,
        )


class VersionedMemoryStore(AgentFileStore):
    """Run-local working copy loaded only from one immutable publication.

    The complete UTF-8 files are exported by NativeSessionAdapter at the next
    boundary. There is no shared directory, home fallback or latest lookup.
    These methods implement storage, not an additional model tool table.
    """

    def __init__(self, *, limits, files=None):
        from wuji_core.contracts.sessions import SessionLimits

        self.limits = SessionLimits.model_validate(limits)
        self._files = {}
        for path, body in (files or {}).items():
            key = self._path(path)
            if not isinstance(body, bytes):
                raise TypeError("published memory must provide complete immutable bytes")
            body.decode("utf-8")
            self._files[key] = bytes(body)
        self._bounded(self._files)

    @staticmethod
    def _path(path, *, directory=False):
        if not isinstance(path, str) or len(path.encode()) > 1024:
            raise ValueError("bounded relative memory key required")
        if directory and path == "":
            return ""
        if (
            not path or path.startswith("/") or "\\" in path
            or any(ord(char) < 32 for char in path)
            or any(part in {"", ".", ".."} for part in path.split("/"))
        ):
            raise ValueError("memory key must stay inside this fixed Session store")
        return path

    def _bounded(self, files):
        if (
            len(files) > self.limits.max_objects
            or any(len(body) > self.limits.max_object_bytes for body in files.values())
            or sum(len(body) for body in files.values()) > self.limits.max_total_bytes
        ):
            raise ValueError("memory snapshot exceeds the fixed Session limits")
        for path in files:
            if any(path.startswith(other + "/") for other in files if other != path):
                raise ValueError("a memory file cannot also be a directory")

    async def write(self, path, content, *, overwrite=True):
        key = self._path(path)
        if not isinstance(content, str) or type(overwrite) is not bool:
            raise TypeError("memory write requires text and an explicit overwrite flag")
        if not overwrite and key in self._files:
            raise FileExistsError(key)
        candidate = {**self._files, key: content.encode("utf-8")}
        self._bounded(candidate)
        self._files = candidate

    async def read(self, path):
        body = self._files.get(self._path(path))
        return None if body is None else body.decode("utf-8")

    async def delete(self, path):
        return self._files.pop(self._path(path), None) is not None

    async def file_exists(self, path):
        return self._path(path) in self._files

    async def create_directory(self, path):
        key = self._path(path, directory=True)
        if key in self._files:
            raise FileExistsError(key)

    async def list_children(self, directory=""):
        key = self._path(directory, directory=True)
        prefix = key + "/" if key else ""
        directories, files = set(), set()
        for path in self._files:
            if path.startswith(prefix):
                head, separator, _tail = path[len(prefix):].partition("/")
                (directories if separator else files).add(head)
        return [FileStoreEntry(name, FileStoreEntry.DIRECTORY) for name in sorted(directories)] + [
            FileStoreEntry(name, FileStoreEntry.FILE) for name in sorted(files)
        ]

    def snapshot_files(self):
        return dict(sorted(self._files.items()))


class PinnedMemoryContextProvider(ContextProvider):
    """Inject complete fixed texts through the public provider interface.

    This explicit Profile option is not Harness FileMemoryProvider: it exposes
    no tools, performs no extraction, and has no model client. Selection and
    changes to persisted memory remain platform responsibilities.
    """

    def __init__(self, *, source_id, store, max_context_bytes):
        super().__init__(source_id)
        if not isinstance(store, VersionedMemoryStore):
            raise TypeError("a fixed versioned AgentFileStore is required")
        self.store = store
        self.max_context_bytes = max_context_bytes

    async def before_run(self, *, agent, session, context, state):
        files = []
        for path in self.store.snapshot_files():
            # Read through the public AgentFileStore API. No cwd/home/latest.
            text = await self.store.read(path)
            files.append({"path": path, "text": text})
        body = {
            "schema_version": "wuji.session.memory-context.v1",
            "session_id": session.session_id, "files": files,
        }
        rendered = canonical_json_bytes(body)
        if len(rendered) > self.max_context_bytes:
            raise ValueError("complete pinned memory does not fit the fixed context limit")
        observed = sha256(rendered).hexdigest()
        if state.get("content_digest", observed) != observed:
            raise ValueError("native memory provider no longer matches its fixed publication")
        state["content_digest"] = observed
        if files:
            context.extend_messages(self, [Message(role="user", contents=rendered.decode("utf-8"))])
