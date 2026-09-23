"""Signed workspace file export/import over the Task's executor boundary."""

import base64
import binascii
from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile

from wuji_core.admission.common import digest
from wuji_core.admission.remote_workspace import (
    ExecutorActionSigner,
    RemoteExecutorTransportError,
    _HttpsJsonEndpoint,
)
from wuji_core.admission.tools import ToolPermit
from wuji_core.contracts import generated as wire
from wuji_core.persistence.uow import DomainError


def _relative(value):
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 256
        or PurePosixPath(value).is_absolute()
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise DomainError("INVALID_SCHEMA", 422)
    return value


def _component(value):
    value = _relative(value)
    if "/" in value:
        raise DomainError("INVALID_SCHEMA", 422)
    return value


def _decode(item, maximum):
    try:
        value = base64.b64decode(item.data_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise DomainError("INVALID_REFERENCE", 422) from error
    if (
        len(value) > maximum
        or len(value) != item.byte_length
        or sha256(value).hexdigest() != item.sha256.root
        or base64.b64encode(value).decode("ascii") != item.data_base64
    ):
        raise DomainError("INVALID_REFERENCE", 422)
    return value


class WorkspaceTransferExecutor(_HttpsJsonEndpoint):
    """Platform-side remote port; the image digest is deployment configuration."""

    def __init__(
        self,
        *,
        signer,
        image_digest,
        max_file_bytes=8 * 1024 * 1024,
        max_total_bytes=32 * 1024 * 1024,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if (
            not isinstance(signer, ExecutorActionSigner)
            or not isinstance(image_digest, str)
            or len(image_digest) != 64
            or any(char not in "0123456789abcdef" for char in image_digest)
            or type(max_file_bytes) is not int
            or type(max_total_bytes) is not int
            or not 1 <= max_file_bytes <= max_total_bytes <= 64 * 1024 * 1024
        ):
            raise ValueError("fixed workspace transfer deployment limits required")
        self.signer, self.image_digest = signer, image_digest
        self.max_file_bytes, self.max_total_bytes = max_file_bytes, max_total_bytes

    async def export(self, permit, request):
        self.binding.require_permit(permit)
        request = wire.WorkspaceExportRequestV1.model_validate(request)
        payload = request.model_dump(mode="json")
        token, _action = self.signer.issue(
            permit,
            action="workspace_export",
            arguments_digest=digest(payload),
        )
        result = wire.WorkspaceExportReplyV1.model_validate(
            await self.apost(
                "/internal/v2/workspace/export",
                {"request": payload},
                bearer_token=token,
            )
        )
        if (
            result.environment_ref != self.binding.environment_ref
            or result.image_digest.root != self.image_digest
            or [item.relative_path for item in result.files]
            != [item.relative_path for item in request.files]
        ):
            raise RemoteExecutorTransportError(
                "workspace export reply failed its deployment binding"
            )
        total = 0
        for item in result.files:
            total += len(_decode(item, self.max_file_bytes))
            if total > self.max_total_bytes:
                raise DomainError("LIMIT_BLOCKED", 429)
        return result

    async def import_publication(self, permit, request):
        self.binding.require_permit(permit)
        request = wire.WorkspaceImportRequestV1.model_validate(request)
        total = 0
        for item in request.files:
            total += len(_decode(item, self.max_file_bytes))
            if total > self.max_total_bytes:
                raise DomainError("LIMIT_BLOCKED", 429)
        payload = request.model_dump(mode="json")
        token, _action = self.signer.issue(
            permit,
            action="workspace_import",
            arguments_digest=digest(payload),
        )
        result = wire.WorkspaceImportReplyV1.model_validate(
            await self.apost(
                "/internal/v2/workspace/import",
                {"request": payload},
                bearer_token=token,
            )
        )
        expected = {
            item.relative_path: (item.sha256.root, item.byte_length)
            for item in request.files
        }
        actual = {
            item.relative_path: (item.sha256.root, item.byte_length)
            for item in result.files
        }
        expected_root = (
            "/workspace/work/"
            + permit.identity.work_item_id
            + "/imports/"
            + request.publication_id
            + "-"
            + request.manifest_digest.root[:16]
        )
        if (
            actual != expected
            or result.imports_root != expected_root
            or any(
                item.destination_path
                != expected_root + "/" + item.relative_path
                for item in result.files
            )
        ):
            raise RemoteExecutorTransportError(
                "workspace import reply differs from sealed source bytes"
            )
        return result


class WorkspaceTransferHandler:
    """Kali-side confined copy implementation; paths never establish authority."""

    def __init__(
        self,
        *,
        root,
        environment_ref,
        image_digest,
        max_file_bytes=8 * 1024 * 1024,
        max_total_bytes=32 * 1024 * 1024,
    ):
        self.root = Path(root)
        if (
            not self.root.is_absolute()
            or self.root.is_symlink()
            or not self.root.is_dir()
            or (self.root / "work").is_symlink()
            or not isinstance(environment_ref, str)
            or not environment_ref
            or not isinstance(image_digest, str)
            or len(image_digest) != 64
            or any(char not in "0123456789abcdef" for char in image_digest)
            or type(max_file_bytes) is not int
            or type(max_total_bytes) is not int
            or not 1 <= max_file_bytes <= max_total_bytes <= 64 * 1024 * 1024
        ):
            raise ValueError("fixed Kali workspace transfer binding required")
        self.environment_ref, self.image_digest = environment_ref, image_digest
        self.max_file_bytes, self.max_total_bytes = max_file_bytes, max_total_bytes

    def _work_root(self, permit):
        work = _relative(permit.work_item_id)
        root = self.root / "work" / work
        if root.is_symlink() or not root.is_dir():
            raise DomainError("INVALID_REFERENCE", 422)
        return root

    @staticmethod
    def _read_at(directory, name, maximum):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
                raise DomainError("INVALID_REFERENCE", 422)
            data = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        identity = lambda value: (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )
        if len(data) > maximum:
            raise DomainError("LIMIT_BLOCKED", 429)
        if identity(before) != identity(after) or len(data) != before.st_size:
            raise DomainError("SOURCE_CHANGED", 409)
        return data

    @classmethod
    def _read(cls, root, relative, maximum):
        parts = _relative(relative).split("/")
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in parts[:-1]:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=directory,
                )
                os.close(directory)
                directory = child
            return cls._read_at(directory, parts[-1], maximum)
        finally:
            os.close(directory)

    def export(self, permit, request):
        request = wire.WorkspaceExportRequestV1.model_validate(request)
        root = self._work_root(permit)
        files, total = [], 0
        for source in request.files:
            data = self._read(root, source.relative_path, self.max_file_bytes)
            total += len(data)
            if total > self.max_total_bytes:
                raise DomainError("LIMIT_BLOCKED", 429)
            files.append(
                {
                    "relative_path": source.relative_path,
                    "data_base64": base64.b64encode(data).decode("ascii"),
                    "byte_length": len(data),
                    "sha256": sha256(data).hexdigest(),
                }
            )
        return wire.WorkspaceExportReplyV1.model_validate(
            {
                "schema_version": "wuji.workspace-export.v1",
                "environment_ref": self.environment_ref,
                "image_digest": self.image_digest,
                "files": files,
            }
        )

    @staticmethod
    def _directory(parent, name):
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
        child = os.open(
            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
        )
        if not stat.S_ISDIR(os.fstat(child).st_mode):
            os.close(child)
            raise DomainError("INVALID_REFERENCE", 422)
        return child

    def import_publication(self, permit, request):
        request = wire.WorkspaceImportRequestV1.model_validate(request)
        work_root = self._work_root(permit)
        root_fd = os.open(
            work_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        open_fds = [root_fd]
        try:
            imports_fd = self._directory(root_fd, "imports")
            open_fds.append(imports_fd)
            bundle_name = (
                _component(request.publication_id)
                + "-"
                + request.manifest_digest.root[:16]
            )
            bundle_fd = self._directory(imports_fd, bundle_name)
            open_fds.append(bundle_fd)
            files, total = [], 0
            for item in request.files:
                data = _decode(item, self.max_file_bytes)
                total += len(data)
                if total > self.max_total_bytes:
                    raise DomainError("LIMIT_BLOCKED", 429)
                parts = _relative(item.relative_path).split("/")
                directory = bundle_fd
                transient = []
                try:
                    for part in parts[:-1]:
                        directory = self._directory(directory, part)
                        transient.append(directory)
                    target = parts[-1]
                    try:
                        existing = self._read_at(
                            directory, target, self.max_file_bytes
                        )
                    except FileNotFoundError:
                        existing = None
                    if existing is not None:
                        if existing != data:
                            raise DomainError("INPUT_DIGEST_CONFLICT", 409)
                    else:
                        fd, temporary = tempfile.mkstemp(prefix=".workspace-", dir=work_root)
                        temporary_name = Path(temporary).name
                        try:
                            with os.fdopen(fd, "wb") as stream:
                                stream.write(data)
                                stream.flush()
                                os.fsync(stream.fileno())
                            try:
                                os.link(
                                    temporary_name,
                                    target,
                                    src_dir_fd=root_fd,
                                    dst_dir_fd=directory,
                                    follow_symlinks=False,
                                )
                            except FileExistsError:
                                if self._read_at(
                                    directory, target, self.max_file_bytes
                                ) != data:
                                    raise DomainError(
                                        "INPUT_DIGEST_CONFLICT", 409
                                    ) from None
                            os.fsync(directory)
                        finally:
                            try:
                                os.unlink(temporary_name, dir_fd=root_fd)
                            except FileNotFoundError:
                                pass
                    destination = str(
                        work_root / "imports" / bundle_name / item.relative_path
                    )
                    files.append(
                        {
                            "relative_path": item.relative_path,
                            "destination_path": destination,
                            "byte_length": len(data),
                            "sha256": item.sha256,
                        }
                    )
                finally:
                    for fd in reversed(transient):
                        os.close(fd)
            return wire.WorkspaceImportReplyV1.model_validate(
                {
                    "schema_version": "wuji.workspace-import.v1",
                    "assurance": "executor_reported",
                    "imports_root": str(work_root / "imports" / bundle_name),
                    "files": files,
                }
            )
        finally:
            for fd in reversed(open_fds):
                os.close(fd)
