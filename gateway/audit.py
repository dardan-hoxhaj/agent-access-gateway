"""Structured audit logging. The token is never included."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger("gateway.audit")


def audit(
    decision: str,
    agent_id: str | None,
    tool: str,
    action: str,
    reason: str,
    request_id: str,
    extra: dict[str, Any] | None = None,
) -> None:
    record: dict[str, Any] = {
        "ts": time.time(),
        "decision": decision,
        "agent_id": agent_id,
        "tool": tool,
        "action": action,
        "reason": reason,
        "request_id": request_id,
    }
    if extra:
        for k, v in extra.items():
            if k.lower() in {"token", "authorization", "bearer"}:
                continue
            record[k] = v
    logger.info(json.dumps(record, separators=(",", ":")))
