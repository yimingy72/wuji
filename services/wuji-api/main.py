"""Deployment entry point for the public vNext read API."""

from __future__ import annotations

import argparse
import importlib


def _load_factory(spec: str):
    module, separator, attribute = spec.partition(":")
    if not separator or not module or not attribute.isidentifier():
        raise ValueError("factory must be an installed module:attribute")
    factory = getattr(importlib.import_module(module), attribute)
    if not callable(factory):
        raise ValueError("API factory must be callable")
    return factory


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the Wuji vNext public API")
    parser.add_argument(
        "--factory",
        default="deployment:build_api",
        help="Installed deployment module:attribute returning an ASGI app",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--ssl-certfile")
    parser.add_argument("--ssl-keyfile")
    args = parser.parse_args()
    if bool(args.ssl_certfile) != bool(args.ssl_keyfile):
        parser.error("TLS requires both certificate and key")
    application = _load_factory(args.factory)()
    uvicorn.run(
        application,
        host=args.host,
        port=args.port,
        access_log=False,
        ssl_certfile=args.ssl_certfile,
        ssl_keyfile=args.ssl_keyfile,
    )


if __name__ == "__main__":
    main()
