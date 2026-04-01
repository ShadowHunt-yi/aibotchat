from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_hex


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")


def generate_trace_id() -> str:
    return f"trace_{_timestamp()}_{token_hex(4)}"


def generate_session_code() -> str:
    return f"s_{_timestamp()}"


def generate_message_code() -> str:
    return f"m_{_timestamp()}"
