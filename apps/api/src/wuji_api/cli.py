"""Local API process entry point with query-safe access logging."""

import os
import logging

import uvicorn


def main() -> None:
    for logger_name in ("wuji.access", "wuji.security"):
        access_logger = logging.getLogger(logger_name)
        access_logger.setLevel(logging.INFO)
        access_logger.propagate = False
        if access_logger.handlers:
            continue
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        access_logger.addHandler(handler)
    uvicorn.run(
        "wuji_api.main:app",
        host="127.0.0.1",
        port=int(os.environ.get("WUJI_API_PORT", "8000")),
        reload=False,
        access_log=False,
    )
