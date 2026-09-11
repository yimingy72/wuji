"""Development PVC evidence bytes, addressed only by task/artifact UUIDs."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
from uuid import UUID, uuid4

MAX_BYTES = 1_048_576


class ArtifactError(RuntimeError): pass
class ArtifactMissing(ArtifactError): pass
class ArtifactIncomplete(ArtifactError): pass
class ArtifactUnsafe(ArtifactError): pass
class ArtifactConflict(ArtifactError): pass


def _uuid(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ArtifactUnsafe("UUID artifact identity required") from None


class ArtifactFileStore:
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try: os.fchmod(descriptor, 0o700)
            finally: os.close(descriptor)
        except OSError:
            raise ArtifactUnsafe("artifact root is unavailable") from None

    def _directory(self, task, *, create=False):
        try:
            root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            raise ArtifactUnsafe("artifact root is unavailable") from None
        try:
            if create:
                try: os.mkdir(task, mode=0o700, dir_fd=root_fd)
                except FileExistsError: pass
            descriptor = os.open(task, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
            if create: os.fchmod(descriptor, 0o700)
            return descriptor
        except FileNotFoundError:
            raise ArtifactMissing("artifact not found") from None
        except OSError:
            raise ArtifactUnsafe("artifact directory is unavailable") from None
        finally:
            os.close(root_fd)

    def write(self, task_id, artifact_id, data, mime):
        task, artifact = _uuid(task_id), _uuid(artifact_id)
        if not isinstance(data, bytes) or len(data) > MAX_BYTES:
            raise ArtifactError("artifact must contain at most 1 MiB of bytes")
        if not isinstance(mime, str) or re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:;[ -~]{1,128})?", mime) is None:
            raise ArtifactError("invalid artifact media type")
        directory = self._directory(task, create=True)
        final, pending = artifact + ".blob", artifact + ".pending-" + str(uuid4())
        key = task + "/" + final
        try:
            descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(pending, final, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            except FileExistsError:
                if self.read(key) != data:
                    raise ArtifactConflict("artifact identity already contains different bytes")
            os.fsync(directory)
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactIncomplete("artifact publication not confirmed") from None
        finally:
            try: os.unlink(pending, dir_fd=directory)
            except FileNotFoundError: pass
            os.close(directory)
        return {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "storage_key": key}

    def read(self, storage_key):
        if not isinstance(storage_key, str): raise ArtifactUnsafe("invalid storage key")
        parts = storage_key.split("/")
        if len(parts) != 2 or not parts[1].endswith(".blob"):
            raise ArtifactUnsafe("invalid storage key")
        task, artifact = _uuid(parts[0]), _uuid(parts[1][:-5])
        if storage_key != task + "/" + artifact + ".blob":
            raise ArtifactUnsafe("noncanonical storage key")
        directory = self._directory(task)
        try:
            try:
                descriptor = os.open(artifact + ".blob", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            except FileNotFoundError:
                if any(name.startswith(artifact + ".pending-") for name in os.listdir(directory)):
                    raise ArtifactIncomplete("artifact publication is incomplete") from None
                raise ArtifactMissing("artifact not found") from None
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                    raise ArtifactUnsafe("invalid artifact file")
                data = stream.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES: raise ArtifactUnsafe("artifact exceeds size limit")
                return data
        except ArtifactError:
            raise
        except OSError:
            raise ArtifactUnsafe("artifact file is unavailable") from None
        finally:
            os.close(directory)
