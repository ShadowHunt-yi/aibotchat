from __future__ import annotations

import contextvars
import logging

from app.core.config import Settings

trace_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_context.get()
        return True


def set_trace_id(trace_id: str) -> contextvars.Token[str]:
    return trace_id_context.set(trace_id)


def reset_trace_id(token: contextvars.Token[str]) -> None:
    trace_id_context.reset(token)


def get_trace_id() -> str:
    return trace_id_context.get()


def configure_logging(settings: Settings) -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_aibotchat_configured", False):
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] [trace_id=%(trace_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(TraceIdFilter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    root_logger._aibotchat_configured = True  # type: ignore[attr-defined]
