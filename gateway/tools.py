"""Mock downstream tools. In a real system these would be real APIs."""

from __future__ import annotations

from typing import Any

TICKETS = [{"id": "T-1", "title": "Printer is out of toner", "status": "open"}]
BILLING = [{"id": "INV-9", "amount": 42.0, "currency": "USD"}]


def tickets_read() -> dict[str, Any]:
    return {"tool": "tickets", "action": "read", "items": TICKETS}


def tickets_write(body: dict[str, Any]) -> dict[str, Any]:
    new = {"id": f"T-{len(TICKETS) + 1}", "title": body.get("title", "untitled"), "status": "open"}
    TICKETS.append(new)
    return {"tool": "tickets", "action": "write", "created": new}


def billing_read() -> dict[str, Any]:
    return {"tool": "billing", "action": "read", "items": BILLING}
