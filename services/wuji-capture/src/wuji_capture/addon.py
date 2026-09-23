"""mitmproxy addon enforcing durable request/response barriers."""

from __future__ import annotations

import base64
import asyncio
import os
import signal
import threading
from pathlib import Path
from typing import Any

from mitmproxy import ctx, http

from wuji_capture.protocol import WriterUnavailable, request as writer_request
from wuji_capture.storage import utc_now, write_fault


SUPPORTED_HTTP = frozenset({"HTTP/1.0", "HTTP/1.1"})


def _headers(fields: tuple[tuple[bytes, bytes], ...] | list[tuple[bytes, bytes]]):
    return [
        [name.decode("latin-1"), value.decode("latin-1")]
        for name, value in fields
    ]


class CaptureAddon:
    def __init__(self) -> None:
        self.socket_path = Path(os.environ.get("WUJI_CAPTURE_WRITER_SOCKET", "/run/wuji-capture/writer.sock"))
        self.fault_path = Path(os.environ.get("WUJI_CAPTURE_FAULT_FILE", "/run/wuji-capture/fault.json"))
        self.timeout = float(os.environ.get("WUJI_CAPTURE_WRITER_TIMEOUT_SECONDS", "5"))
        legacy_limit = os.environ.get("WUJI_CAPTURE_MAX_BODY_BYTES", str(8 * 1024 * 1024))
        self.maximum_request_body_bytes = int(
            os.environ.get("WUJI_CAPTURE_MAX_REQUEST_BODY_BYTES", legacy_limit)
        )
        self.maximum_response_body_bytes = int(
            os.environ.get("WUJI_CAPTURE_MAX_RESPONSE_BODY_BYTES", legacy_limit)
        )
        self.drain_file = Path(
            os.environ.get("WUJI_CAPTURE_DRAIN_FILE", "/run/wuji-capture/draining")
        )

    @staticmethod
    def _has_trailers(message: http.Request | http.Response) -> bool:
        trailers = getattr(message, "trailers", None)
        return trailers is not None and bool(trailers.fields)

    async def _write(self, flow: http.HTTPFlow, stage: str, metadata: dict[str, Any], body: bytes = b"") -> None:
        await asyncio.to_thread(
            writer_request,
            self.socket_path,
            {
                "op": "record",
                "exchange_id": flow.id,
                "stage": stage,
                "metadata": metadata,
                **({} if stage == "gap" else {"body_base64": base64.b64encode(body).decode("ascii")}),
            },
            timeout=self.timeout,
        )

    @staticmethod
    def _request_metadata(flow: http.HTTPFlow) -> dict[str, Any]:
        request = flow.request
        address = flow.server_conn.address
        return {
            "method": request.method,
            "url": request.url,
            "scheme": request.scheme,
            "target_host": request.host,
            "target_port": request.port,
            "server_address": None if address is None else list(address),
            "http_version": request.http_version,
            "headers": _headers(request.headers.fields),
            "content_encoding": request.headers.get_all("content-encoding"),
            "timestamp_start": request.timestamp_start,
            "timestamp_end": request.timestamp_end,
        }

    @staticmethod
    def _response_metadata(flow: http.HTTPFlow) -> dict[str, Any]:
        response = flow.response
        assert response is not None
        return {
            "status_code": response.status_code,
            "reason": response.reason,
            "http_version": response.http_version,
            "headers": _headers(response.headers.fields),
            "content_encoding": response.headers.get_all("content-encoding"),
            "timestamp_start": response.timestamp_start,
            "timestamp_end": response.timestamp_end,
        }

    async def _gap(self, flow: http.HTTPFlow, reason: str, *, detail: str | None = None) -> bool:
        try:
            await self._write(flow, "gap", {
                "reason": reason,
                "detail": None if detail is None else detail[:1024],
                "http_version": flow.request.http_version if flow.request else None,
                "observed_at": utc_now(),
                "completeness": "partial",
            })
            flow.metadata["wuji.capture.gap_recorded"] = True
            return True
        except WriterUnavailable as error:
            self._fatal(flow, error)
            return False

    def _fatal(self, flow: http.HTTPFlow, error: Exception) -> None:
        try:
            try:
                flow.kill()
            finally:
                write_fault(self.fault_path, component="proxy-writer", reason=str(error))
        finally:
            try:
                ctx.master.shutdown()
            except Exception:
                # Mitmproxy contains addon exceptions. A signal guarantees that
                # even a failed fault-marker write takes the proxy down.
                threading.Timer(0.01, os.kill, args=(os.getpid(), signal.SIGTERM)).start()

    async def _transport_gap(self, connection, reason: str) -> None:
        peer = connection.peername
        detail = connection.error
        try:
            await asyncio.to_thread(
                writer_request,
                self.socket_path,
                {
                    "op": "record",
                    "exchange_id": "transport-" + connection.id,
                    "stage": "gap",
                    "metadata": {
                        "reason": reason,
                        "detail": None if detail is None else str(detail)[:1024],
                        "connection_id": connection.id,
                        "peer": None if peer is None else list(peer),
                        "transport_protocol": connection.transport_protocol,
                        "tls": bool(connection.tls),
                        "observed_at": utc_now(),
                        "completeness": "partial",
                    },
                },
                timeout=self.timeout,
            )
        except WriterUnavailable as error:
            try:
                write_fault(self.fault_path, component="proxy-writer", reason=str(error))
            finally:
                try:
                    ctx.master.shutdown()
                except Exception:
                    threading.Timer(
                        0.01, os.kill, args=(os.getpid(), signal.SIGTERM)
                    ).start()

    async def client_disconnected(self, client) -> None:
        if client.tls and not client.tls_established:
            await self._transport_gap(client, "client_tls_handshake_failed")

    async def server_connect_error(self, data) -> None:
        await self._transport_gap(data.server, "server_connect_error")

    async def requestheaders(self, flow: http.HTTPFlow) -> None:
        if flow.request.http_version not in SUPPORTED_HTTP:
            if await self._gap(flow, "http_version_unsupported", detail=flow.request.http_version):
                flow.metadata["wuji.capture.local_rejection"] = True
                flow.response = http.Response.make(505, b"HTTP version is not supported by this capture profile\n")
            return
        if self.drain_file.exists():
            if await self._gap(flow, "capture_draining"):
                flow.metadata["wuji.capture.local_rejection"] = True
                flow.response = http.Response.make(503, b"Capture is draining\n")
            return
        if flow.request.headers.get_all("expect"):
            if await self._gap(flow, "expect_unsupported"):
                flow.metadata["wuji.capture.local_rejection"] = True
                # Mitmproxy's HTTP/1 state machine may still emit 100 Continue
                # after requestheaders. Closing now is the only unambiguous
                # refusal that cannot deadlock waiting for a body we rejected.
                flow.kill()
            return
        if flow.request.headers.get_all("trailer"):
            flow.metadata["wuji.capture.local_rejection"] = True
            flow.kill()
            await self._gap(flow, "request_trailers_unsupported")
            return
        if flow.request.headers.get_all("upgrade"):
            if await self._gap(flow, "upgrade_unsupported"):
                flow.metadata["wuji.capture.local_rejection"] = True
                flow.response = http.Response.make(426, b"Protocol upgrade is not supported by this capture profile\n")

    async def request(self, flow: http.HTTPFlow) -> None:
        if flow.metadata.get("wuji.capture.local_rejection"):
            return
        if self.drain_file.exists():
            if await self._gap(flow, "capture_draining"):
                flow.metadata["wuji.capture.local_rejection"] = True
                flow.kill()
            return
        if self._has_trailers(flow.request):
            if await self._gap(flow, "request_trailers_unsupported"):
                flow.metadata["wuji.capture.local_rejection"] = True
                flow.kill()
            return
        body = flow.request.raw_content or b""
        if len(body) > self.maximum_request_body_bytes:
            if await self._gap(flow, "request_body_limit_exceeded"):
                flow.metadata["wuji.capture.local_rejection"] = True
                flow.response = http.Response.make(413, b"Request body exceeds the finite capture limit\n")
            return
        try:
            # With streaming disabled, request() runs with the complete entity.
            # The writer ACK is returned only after body, metadata, and index fsync.
            await self._write(flow, "request", self._request_metadata(flow), body)
            flow.metadata["wuji.capture.request_durable"] = True
        except WriterUnavailable as error:
            self._fatal(flow, error)

    async def responseheaders(self, flow: http.HTTPFlow) -> None:
        response = flow.response
        if response is not None and response.http_version not in SUPPORTED_HTTP:
            if await self._gap(
                flow, "response_http_version_unsupported", detail=response.http_version
            ):
                flow.metadata["wuji.capture.unsupported_response"] = True
                flow.kill()
            return
        if response is not None and 100 <= response.status_code < 200:
            if await self._gap(flow, "interim_response_unsupported", detail=str(response.status_code)):
                flow.metadata["wuji.capture.unsupported_response"] = True
                flow.kill()
            return
        if response is not None and response.headers.get_all("trailer"):
            flow.metadata["wuji.capture.unsupported_response"] = True
            flow.kill()
            await self._gap(flow, "response_trailers_unsupported")
            return

    async def response(self, flow: http.HTTPFlow) -> None:
        if (
            flow.metadata.get("wuji.capture.local_rejection")
            or flow.metadata.get("wuji.capture.unsupported_response")
        ):
            return
        if not flow.metadata.get("wuji.capture.request_durable"):
            self._fatal(flow, WriterUnavailable("response arrived without a durable request"))
            return
        assert flow.response is not None
        if self._has_trailers(flow.response):
            if await self._gap(flow, "response_trailers_unsupported"):
                flow.metadata["wuji.capture.unsupported_response"] = True
                flow.kill()
            return
        body = flow.response.raw_content or b""
        if len(body) > self.maximum_response_body_bytes:
            if await self._gap(flow, "response_body_limit_exceeded"):
                flow.kill()
            return
        try:
            # With streaming disabled, response() is the final delivery barrier.
            await self._write(flow, "response", self._response_metadata(flow), body)
        except WriterUnavailable as error:
            self._fatal(flow, error)

    async def error(self, flow: http.HTTPFlow) -> None:
        if flow.metadata.get("wuji.capture.local_rejection") or flow.metadata.get("wuji.capture.gap_recorded"):
            return
        detail = None if flow.error is None else str(flow.error)
        await self._gap(flow, "flow_error", detail=detail)


addons = [CaptureAddon()]
