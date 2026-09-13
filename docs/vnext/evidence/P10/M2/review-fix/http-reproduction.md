# P10 M2 complete HTTP and PostgreSQL packets

Every file named m2-controller-http.jsonl, m2-node-http.jsonl, m2-platform-gates-http.jsonl or m2-model-upstream-http.jsonl contains one JSON object per actual exchange:

- request.method and request.url;
- all recorded non-secret request headers;
- the complete request body in request.body_base64;
- response.status_code and all response headers;
- the complete response body in response.body_base64;
- response.error only when no HTTP response existed.

Bodies are base64 so native SSE and arbitrary bytes remain exact. Decode a body with a standard RFC 4648 base64 decoder. PostgreSQL files are losslessly compressed as postgres-events.jsonl.gz; decompression yields the complete ordered SQL/parameter/result stream.

The publishable derivative changes only generated bootstrap run_credential values and marks each changed response with a redactions entry. Authorization headers use explicit redaction placeholders. Reproduction creates fresh test credentials through the P09 fixture issuer.

Key final packets:

- [r7 current controller](raw/r7/evidence/b5cdd39aebb1/m2-controller-http.jsonl)
- [r7 current Node](raw/r7/evidence/b5cdd39aebb1/m2-node-http.jsonl)
- [r7 current Gate](raw/r7/evidence/b5cdd39aebb1/m2-platform-gates-http.jsonl)
- [r7 current native SSE](raw/r7/evidence/b5cdd39aebb1/m2-model-upstream-http.jsonl)
- [r7 current SQL](raw/r7/evidence/b5cdd39aebb1/postgres-events.jsonl.gz)
- [r6 Worker write-race controller](raw/r6/evidence/283331635b77/m2-controller-http.jsonl)
- [r6 revoked controller](raw/r6/evidence/3094c7d71e0c/m2-controller-http.jsonl)
- [r3 Pod Node transport](raw/r3/evidence/2cabb5414cf6/m2-node-http.jsonl)
- [r2 profile controller](raw/r2/evidence/68b76ae26bcc/m2-controller-http.jsonl)

The r2 wrong-profile pass predates passive SupervisorHttpTransport audit, so its Node GET/PUT packet is absent. Its controller HTTP, complete SQL, fingerprint and pytest result are retained. No packet was reconstructed.

All r1–r7 packets, including failed cases, are under [raw](raw/). The machine index lists every file, size and SHA-256.
