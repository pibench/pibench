"""Generic domain tool implementations for pibench_scenario_v1 scenarios.

Key insight: the scenario's initial_state_patch IS the database. Tools are
state lookups and state mutations on that dict. One generic dispatch function
handles all domain tools without writing 36 individual functions.

Tool contract: fn(db: dict, **arguments) -> Any

Determinism: all IDs and timestamps MUST be derived from db state, not from
uuid4() or datetime.now(). Use _next_id(db, prefix) for IDs and _now(db) for
timestamps. This ensures identical scenario + seed produces identical outputs.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any


def _next_id(db: dict, prefix: str) -> str:
    """Generate a deterministic ID from a monotonic counter in db.

    Each call increments db["_id_counter"] and produces a hex suffix
    derived from the counter value. This replaces uuid.uuid4() calls.
    """
    counter = db.get("_id_counter", 0)
    db["_id_counter"] = counter + 1
    # Produce a stable 8-char hex from counter + prefix (for uniqueness across prefixes)
    raw = f"{prefix}:{counter}".encode()
    suffix = hashlib.sha256(raw).hexdigest()[:8].upper()
    return f"{prefix}_{suffix}"


def _now(db: dict) -> str:
    """Return the deterministic 'now' timestamp from db.

    Falls back to a fixed epoch if db["now"] is not set (should not happen
    in well-formed scenarios, but avoids calling datetime.now()).
    """
    return db.get("now", "2026-01-01T00:00:00+00:00")


def generic_tool(db: dict, tool_name: str, **kwargs: Any) -> Any:
    """Single dispatch function for all scenario tools.

    Strategy:
    1. Try domain-specific handlers first (record_decision, hold, process, etc.)
    2. Fall back to generic DB lookup by matching kwargs against DB collections.
    """
    handler = _HANDLERS.get(tool_name)
    if handler is not None:
        return handler(db, **kwargs)

    # Generic fallback: search DB for matching records
    return _generic_lookup(db, tool_name, **kwargs)


# ── Record decision (all domains) ────────────────────────

def _record_decision(db: dict, **kwargs: Any) -> dict:
    """Record canonical decision. Always succeeds."""
    decision = kwargs.get("decision", "")
    record = {
        "decision_record_id": _next_id(db, "DEC"),
        "decision": decision,
        "recorded_at": _now(db),
        **{k: v for k, v in kwargs.items() if k != "decision"},
    }
    db.setdefault("decisions", []).append(record)
    return record


# ── State mutation handlers ───────────────────────────────

def _hold_transaction(db: dict, **kwargs: Any) -> dict:
    """Place a hold on a pending request."""
    request_id = kwargs.get("request_id", "")
    reason = kwargs.get("reason", "compliance_review")
    req = _find_in_collection(db, "activity.pending_requests", "request_id", request_id)
    if req is None:
        req = _find_in_collection(db, "pending_requests", "request_id", request_id)
    if req is not None:
        req["status"] = "held"
        req["hold_reason"] = reason
    return {
        "request_id": request_id,
        "status": "held",
        "hold_reason": reason,
        "hold_expiry": "2026-03-01T10:00:00-05:00",
    }


def _process_refund(db: dict, **kwargs: Any) -> dict:
    """Process a refund for an order, applying restocking fee if specified."""
    order_id = kwargs.get("order_id", "")
    order = _find_in_collection(db, "orders", "order_id", order_id)
    amount = kwargs.get("amount")
    if amount is None and order is not None:
        amount = order.get("total_amount", 0)

    # Apply restocking fee if provided
    restocking_pct = kwargs.get("restocking_fee_percent", 0)
    restocking_amount = 0
    if restocking_pct and amount:
        restocking_amount = round(amount * restocking_pct / 100, 2)
        amount = round(amount - restocking_amount, 2)

    if order is not None:
        order["status"] = "refunded"
    return {
        "refund_id": _next_id(db, "REF"),
        "status": "processed",
        "amount_refunded": amount,
        "refund_method": "original_payment",
        "restocking_fee_amount": restocking_amount,
    }


def _process_exchange(db: dict, **kwargs: Any) -> dict:
    """Process an exchange."""
    return {
        "exchange_id": _next_id(db, "EXC"),
        "status": "processed",
        "price_difference": 0,
        "new_order_id": _next_id(db, "ORD"),
    }


def _apply_store_credit(db: dict, **kwargs: Any) -> dict:
    """Issue store credit."""
    return {
        "credit_id": _next_id(db, "CRD"),
        "amount": kwargs.get("amount", 0),
        "customer_id": kwargs.get("customer_id", ""),
        "expiry_date": "2027-02-26",
    }


def _deny_refund(db: dict, **kwargs: Any) -> dict:
    """Formally deny a refund."""
    return {
        "denial_id": _next_id(db, "DEN"),
        "status": "denied",
        "reason_code": kwargs.get("reason_code", ""),
    }


def _escalate(db: dict, **kwargs: Any) -> dict:
    """Generic escalation handler for escalate_to_manager, escalate_to_compliance, etc."""
    return {
        "escalation_id": _next_id(db, "ESC"),
        "status": "pending_review",
        "assigned_to": "Senior Officer",
        "created_at": _now(db),
        **{k: v for k, v in kwargs.items() if k not in ("reason", "summary")},
    }


def _flag_account(db: dict, **kwargs: Any) -> dict:
    """Flag a customer account."""
    customer_id = kwargs.get("customer_id", "")
    flag_type = kwargs.get("flag_type", "other")
    profile = _find_in_collection(db, "customer_profile", "customer_id", customer_id)
    if profile is None:
        # customer_profile might be a single dict, not a list
        cp = db.get("customer_profile", {})
        if isinstance(cp, dict) and cp.get("customer_id") == customer_id:
            profile = cp
    if profile is not None:
        profile.setdefault("account_flags", []).append(flag_type)
    return {
        "flag_id": _next_id(db, "FLG"),
        "customer_id": customer_id,
        "flag_type": flag_type,
        "status": "active",
    }


def _process_wire_transfer(db: dict, **kwargs: Any) -> dict:
    """Execute a wire transfer."""
    request_id = kwargs.get("request_id", "")
    req = _find_in_collection(db, "activity.pending_requests", "request_id", request_id)
    if req is not None:
        req["status"] = "submitted"
    return {
        "wire_id": _next_id(db, "WIRE"),
        "status": "submitted",
        "confirmation_number": _next_id(db, "CNF"),
        "timestamp": _now(db),
    }


def _create_alert(db: dict, **kwargs: Any) -> dict:
    """Create a monitoring alert."""
    alert = {
        "alert_id": _next_id(db, "ALT"),
        "account_id": kwargs.get("account_id", ""),
        "category": kwargs.get("category", "OTHER"),
        "severity": kwargs.get("severity", "medium"),
        "status": "open",
        "created_at": _now(db),
        "description": kwargs.get("description", ""),
    }
    monitoring = db.get("monitoring", {})
    if isinstance(monitoring, dict):
        monitoring.setdefault("alerts", []).append(alert)
    return {
        "alert_id": alert["alert_id"],
        "status": "open",
        "created_at": alert["created_at"],
    }


def _open_case(db: dict, **kwargs: Any) -> dict:
    """Open an investigation case."""
    case = {
        "case_id": _next_id(db, "CASE"),
        "customer_id": kwargs.get("customer_id", ""),
        "case_type": kwargs.get("case_type", "OTHER"),
        "status": "open",
        "assigned_to": "Analyst",
        "opened_at": _now(db),
        "summary": kwargs.get("summary", ""),
    }
    investigations = db.get("investigations", {})
    if isinstance(investigations, dict):
        investigations.setdefault("cases", []).append(case)
    return {
        "case_id": case["case_id"],
        "status": "open",
        "assigned_to": case["assigned_to"],
        "created_at": case["opened_at"],
    }


def _file_sar(db: dict, **kwargs: Any) -> dict:
    """Initiate SAR filing."""
    return {
        "sar_id": _next_id(db, "SAR"),
        "filing_status": "draft",
        "filed_at": _now(db),
    }


def _file_ctr(db: dict, **kwargs: Any) -> dict:
    """Initiate CTR filing."""
    return {
        "ctr_id": _next_id(db, "CTR"),
        "filing_status": "draft",
        "filed_at": _now(db),
    }


def _dismiss_alert(db: dict, **kwargs: Any) -> dict:
    """Dismiss a monitoring alert."""
    alert_id = kwargs.get("alert_id", "")
    monitoring = db.get("monitoring", {})
    if isinstance(monitoring, dict):
        for alert in monitoring.get("alerts", []):
            if alert.get("alert_id") == alert_id:
                alert["status"] = "dismissed"
    return {
        "alert_id": alert_id,
        "status": "dismissed",
        "dismissed_at": _now(db),
    }


def _update_request_status(db: dict, **kwargs: Any) -> dict:
    """Update a pending request's status."""
    request_id = kwargs.get("request_id", "")
    status = kwargs.get("status", "")
    req = _find_in_collection(db, "activity.pending_requests", "request_id", request_id)
    if req is not None:
        req["status"] = status
    return {"request_id": request_id, "status": status}


# ── HelpDesk-specific handlers ───────────────────────────

def _reset_password(db: dict, **kwargs: Any) -> dict:
    """Reset an employee's password."""
    employee_id = kwargs.get("employee_id", "")
    account_type = kwargs.get("account_type", "standard")
    if account_type == "admin":
        return {"error": True, "message": "Admin password resets require IT Security approval. Please escalate."}
    accounts = db.get("accounts", {})
    if employee_id in accounts:
        accounts[employee_id]["password_last_changed"] = _now(db)
    return {
        "employee_id": employee_id,
        "status": "reset_complete",
        "temporary_password": "TmpP@ss_2026!",
        "expires_in_hours": 24,
    }


def _unlock_account(db: dict, **kwargs: Any) -> dict:
    """Unlock an employee account. Security-flagged accounts require escalation."""
    employee_id = kwargs.get("employee_id", "")
    accounts = db.get("accounts", {})
    account = accounts.get(employee_id, {}) if employee_id else {}
    lockout_reason = account.get("lockout_reason", "failed_login_attempts")

    # Security-flagged accounts cannot be unlocked without IT Security approval
    if lockout_reason == "security_flag":
        return {
            "employee_id": employee_id,
            "status": "locked",
            "requires_escalation": True,
            "previous_lockout_reason": lockout_reason,
            "message": "Security-flagged lockout requires IT Security approval.",
        }

    if employee_id in accounts:
        accounts[employee_id]["lockout_status"] = "none"
    return {
        "employee_id": employee_id,
        "status": "unlocked",
        "previous_lockout_reason": lockout_reason,
    }


def _log_ticket(db: dict, **kwargs: Any) -> dict:
    """Log a ticket in the ticketing system."""
    ticket = {
        "ticket_id": _next_id(db, "TKT"),
        "employee_id": kwargs.get("employee_id", ""),
        "category": kwargs.get("category", ""),
        "summary": kwargs.get("summary", ""),
        "action_taken": kwargs.get("action_taken", ""),
        "status": kwargs.get("status", "open"),
        "created_at": _now(db),
    }
    db.setdefault("tickets", []).append(ticket)
    return {"ticket_id": ticket["ticket_id"], "status": ticket["status"]}


def _install_software(db: dict, **kwargs: Any) -> dict:
    """Install software on an employee's workstation."""
    software_name = kwargs.get("software_name", "")
    prohibited = db.get("prohibited_software", [])
    if software_name.lower() in [s.lower() for s in prohibited]:
        return {"error": True, "message": f"'{software_name}' is on the prohibited software list."}
    return {
        "install_id": _next_id(db, "INS"),
        "status": "installed",
        "software_name": software_name,
    }


def _provision_vpn_access(db: dict, **kwargs: Any) -> dict:
    """Provision VPN access."""
    return {
        "vpn_id": _next_id(db, "VPN"),
        "status": "provisioned",
        "access_level": kwargs.get("access_level", "standard"),
        "employee_id": kwargs.get("employee_id", ""),
    }


def _create_access_request(db: dict, **kwargs: Any) -> dict:
    """Create an access request."""
    return {
        "access_request_id": _next_id(db, "AR"),
        "status": "submitted",
        "resource_name": kwargs.get("resource_name", ""),
        "access_level": kwargs.get("access_level", "read"),
    }


# ── Policy access ─────────────────────────────────────────

# ── Handler registry ──────────────────────────────────────

_HANDLERS: dict[str, Any] = {
    # All domains
    "record_decision": _record_decision,

    # FINRA
    "process_wire_transfer": _process_wire_transfer,
    "hold_transaction": _hold_transaction,
    "create_alert": _create_alert,
    "open_case": _open_case,
    "escalate_to_compliance": _escalate,
    "file_sar": _file_sar,
    "file_ctr": _file_ctr,
    "dismiss_alert": _dismiss_alert,
    "update_request_status": _update_request_status,

    # Retail
    "process_refund": _process_refund,
    "process_exchange": _process_exchange,
    "apply_store_credit": _apply_store_credit,
    "deny_refund": _deny_refund,
    "escalate_to_manager": _escalate,
    "flag_account": _flag_account,

    # HelpDesk
    "reset_password": _reset_password,
    "unlock_account": _unlock_account,
    "provision_vpn_access": _provision_vpn_access,
    "install_software": _install_software,
    "create_access_request": _create_access_request,
    "escalate_to_tier2": _escalate,
    "escalate_to_it_security": _escalate,
    "log_ticket": _log_ticket,
}


# ── Helpers ───────────────────────────────────────────────

def _parse_datetime(s: str) -> datetime:
    """Parse an ISO-8601 datetime string, handling timezone offsets."""
    # Python 3.11+ fromisoformat handles offsets; strip for compat
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        # Fallback: strip tz and parse naive
        if "+" in s[10:]:
            s = s[:s.rindex("+")]
        elif s[10:].count("-") >= 1:
            s = s[:s.rindex("-")]
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def _find_in_collection(
    db: dict, path: str, id_field: str, id_value: str
) -> dict | None:
    """Navigate a dotted path in db to find a record by ID field."""
    obj = db
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
        if obj is None:
            return None

    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict) and item.get(id_field) == id_value:
                return item
    return None


def build_tool_map(tool_schemas: list[dict]) -> dict[str, Any]:
    """Build a tool function map from tool schemas.

    Each tool name maps to a closure: fn(db, **kwargs) -> Any
    that delegates to generic_tool.
    """
    tool_map = {}
    for schema in tool_schemas:
        name = schema["name"]

        def _make_fn(tool_name: str) -> Any:
            def fn(db: dict, **kwargs: Any) -> Any:
                return generic_tool(db, tool_name, **kwargs)
            return fn

        tool_map[name] = _make_fn(name)
    return tool_map
