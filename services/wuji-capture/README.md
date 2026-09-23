# Wuji capture process

This image is the fail-closed capture process for the Core CTF runtime. It has
its own Python lock and image. It does not contain the MAF worker, a model key,
or a platform write credential.

The first supported matrix is deliberately finite:

| Traffic | Status |
| --- | --- |
| HTTP/1.0 and HTTP/1.1 through the explicit proxy | supported |
| TLS 1.2/1.3 carrying HTTP/1.1 through the generated proxy CA | supported |
| `Expect: 100-continue`, upstream 1xx, protocol upgrade, WebSocket | rejected and recorded as a gap |
| HTTP/2, HTTP/3/QUIC, raw TCP tunnelling, streamed or unbounded bodies | unsupported |

For a supported request, the addon waits for the dedicated writer to fsync the
raw request body, metadata, and recoverable index before mitmproxy may contact
the upstream. It applies the same barrier to the final response before delivery
to the client. Ordered duplicate headers and the actual request URL, target
host/port, hashes, lengths, encoding, status, and timestamps are retained.

The supervisor starts the writer, the fixed tcpdump 4.99.5/libpcap 1.10.5
capture, and mitmproxy 12.2.3 in that order. tcpdump uses `-C` without `-W`, so
segments are never overwritten. `SIGUSR1` reads statistics from the same live
capture handle; `SIGUSR2` flushes it before shutdown. A missing stats response,
kernel drop, writer error, storage fault, or child exit closes the proxy and
capture failure domain. The manifest remains incomplete unless the actual
capture handle reports zero drops.

The proxy and health server both bind to loopback by default because Task
containers share a network namespace. A Kubernetes HTTP probe aimed at the Pod
IP will therefore not work; the later Task template must use an exec probe for
the loopback health URL or add a separately authenticated read-only endpoint.

`GET /health/live` reports the PID 1 failure state. `GET /health/ready` also
performs a durable writer probe. Normal
`SIGTERM` stops the proxy, seals and stops the writer, flushes and stops tcpdump,
fsyncs segments, then writes `manifest.json`. Runtime integration, network owner
rules, capture ingestion, and Task-scoped database identity are separate later
steps; this directory does not invent those contracts.

The standalone defaults are 8 MiB per finite HTTP entity and 64 MB per PCAP
segment. M2c must freeze these in the RuntimeProfile and align ArtifactStore and
gateway transfer limits before the UI offers complete downloads; this module
does not claim that the existing 8 MiB store or 2 MiB gateway can serve every
default segment.
