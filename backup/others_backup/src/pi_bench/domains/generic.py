"""Generic domain tool implementations for pibench_scenario_v1 scenarios.

Key insight: the scenario's initial_state_patch IS the database. Tools are
state lookups and state mutations on that dict. One generic dispatch function
handles all domain tools without writing 36 individual functions.

Tool contract: fn(db: dict, **arguments) -> Any
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any


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
        "decision_record_id": f"DEC_{uuid.uuid4().hex[:8].upper()}",
        "decision": decision,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
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
        "refund_id": f"REF_{uuid.uuid4().hex[:8].upper()}",
        "status": "processed",
        "amount_refunded": amount,
        "refund_method": "original_payment",
        "restocking_fee_amount": restocking_amount,
    }


def _process_exchange(db: dict, **kwargs: Any) -> dict:
    """Process an exchange."""
    return {
        "exchange_id": f"EXC_{uuid.uuid4().hex[:8].upper()}",
        "status": "processed",
        "price_difference": 0,
        "new_order_id": f"ORD_{uuid.uuid4().hex[:8].upper()}",
    }


def _apply_store_credit(db: dict, **kwargs: Any) -> dict:
    """Issue store credit."""
    return {
        "credit_id": f"CRD_{uuid.uuid4().hex[:8].upper()}",
        "amount": kwargs.get("amount", 0),
        "customer_id": kwargs.get("customer_id", ""),
        "expiry_date": "2027-02-26",
    }


def _deny_refund(db: dict, **kwargs: Any) -> dict:
    """Formally deny a refund."""
    return {
        "denial_id": f"DEN_{uuid.uuid4().hex[:8].upper()}",
        "status": "denied",
        "reason_code": kwargs.get("reason_code", ""),
    }


def _escalate(db: dict, **kwargs: Any) -> dict:
    """Generic escalation handler for escalate_to_manager, escalate_to_compliance, etc."""
    return {
        "escalation_id": f"ESC_{uuid.uuid4().hex[:8].upper()}",
        "status": "pending_review",
        "assigned_to": "Senior Officer",
        "created_at": datetime.now(timezone.utc).isoformat(),
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
        "flag_id": f"FLG_{uuid.uuid4().hex[:8].upper()}",
        "customer_id": customer_id,
        "flag_type": flag_type,
        "status": "active",
    }


def _check_return_eligibility(db: dict, **kwargs: Any) -> dict:
    """Check return eligibility based on order data, category, and loyalty tier."""
    order_id = kwargs.get("order_id", "")
    order = _find_in_collection(db, "orders", "order_id", order_id)
    if order is None:
        return {"eligible": False, "reason": "Order not found"}

    is_final_sale = order.get("is_final_sale", False)
    if is_final_sale:
        return {"eligible": False, "reason": "Final sale items are not eligible for return."}

    # Determine item category
    items = order.get("items", [])
    category = items[0].get("category", "general") if items else "general"
    is_electronics = category == "electronics"

    # Determine loyalty tier from customer profile
    profile = db.get("customer_profile", {})
    if isinstance(profile, list):
        cust_id = order.get("customer_id", "")
        profile = next((p for p in profile if p.get("customer_id") == cust_id), {})
    tier = profile.get("loyalty_tier", "").lower()

    # Base return windows (calendar days from delivery)
    if is_electronics:
        base_window = 15
        sections = ["Section 2: Electronics & Technology Products"]
    else:
        base_window = 30
        sections = ["Section 1: General Returns Policy"]

    # Loyalty tier extensions
    if tier == "gold":
        if is_electronics:
            base_window = 21
        else:
            base_window = 45
        sections.append("Section 5: Loyalty Tier Benefits (Gold)")
    elif tier == "platinum":
        if is_electronics:
            base_window = 30
        else:
            base_window = 60
        sections.append("Section 5: Loyalty Tier Benefits (Platinum)")

    # Compute window end from delivery date
    delivery_str = order.get("delivery_date", "")
    now_str = db.get("now", "")
    if delivery_str and now_str:
        delivery_dt = _parse_datetime(delivery_str)
        now_dt = _parse_datetime(now_str)
        window_end = delivery_dt + timedelta(days=base_window)
        if now_dt > window_end:
            return {
                "eligible": False,
                "reason": f"Outside {base_window}-day return window. Window ended {window_end.isoformat()}.",
                "return_window_end": window_end.isoformat(),
                "restocking_fee_applicable": False,
                "restocking_fee_percent": 0,
                "policy_sections_applicable": sections,
            }
    else:
        window_end = None

    # Restocking fee for electronics
    restocking_fee = False
    restocking_pct = 0
    if is_electronics:
        restocking_fee = True
        restocking_pct = 15
        # Gold: first electronics return per year waived; Platinum: always waived
        if tier == "platinum":
            restocking_fee = False
            restocking_pct = 0
        elif tier == "gold":
            # Simplified: waive first electronics return
            restocking_fee = False
            restocking_pct = 0

    return {
        "eligible": True,
        "reason": "Within return window, item eligible.",
        "return_window_end": window_end.isoformat() if window_end else None,
        "restocking_fee_applicable": restocking_fee,
        "restocking_fee_percent": restocking_pct,
        "policy_sections_applicable": sections,
    }


def _process_wire_transfer(db: dict, **kwargs: Any) -> dict:
    """Execute a wire transfer."""
    request_id = kwargs.get("request_id", "")
    req = _find_in_collection(db, "activity.pending_requests", "request_id", request_id)
    if req is not None:
        req["status"] = "submitted"
    return {
        "wire_id": f"WIRE_{uuid.uuid4().hex[:8].upper()}",
        "status": "submitted",
        "confirmation_number": f"CNF_{uuid.uuid4().hex[:8].upper()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _create_alert(db: dict, **kwargs: Any) -> dict:
    """Create a monitoring alert."""
    alert = {
        "alert_id": f"ALT_{uuid.uuid4().hex[:8].upper()}",
        "account_id": kwargs.get("account_id", ""),
        "category": kwargs.get("category", "OTHER"),
        "severity": kwargs.get("severity", "medium"),
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
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
        "case_id": f"CASE_{uuid.uuid4().hex[:8].upper()}",
        "customer_id": kwargs.get("customer_id", ""),
        "case_type": kwargs.get("case_type", "OTHER"),
        "status": "open",
        "assigned_to": "Analyst",
        "opened_at": datetime.now(timezone.utc).isoformat(),
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
        "sar_id": f"SAR_{uuid.uuid4().hex[:8].upper()}",
        "filing_status": "draft",
        "filed_at": datetime.now(timezone.utc).isoformat(),
    }


def _file_ctr(db: dict, **kwargs: Any) -> dict:
    """Initiate CTR filing."""
    return {
        "ctr_id": f"CTR_{uuid.uuid4().hex[:8].upper()}",
        "filing_status": "draft",
        "filed_at": datetime.now(timezone.utc).isoformat(),
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
        "dismissed_at": datetime.now(timezone.utc).isoformat(),
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

def _verify_identity(db: dict, **kwargs: Any) -> dict:
    """Verify employee identity against records.

    Checks each verification_item value against the employee record.
    Requires at least 3 matching items for successful verification.
    """
    employee_id = kwargs.get("employee_id", "")
    items = kwargs.get("verification_items", {})

    employee = db.get("employee", {})
    if not employee or employee.get("employee_id") != employee_id:
        return {
            "employee_id": employee_id,
            "verified": False,
            "verification_method": "knowledge_based",
            "verification_timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": "none",
            "items_matched": [],
            "items_provided": len(items) if items else 0,
            "reason": "Employee not found",
        }

    matched = []
    for key, value in (items or {}).items():
        actual = employee.get(key)
        if actual is not None and str(actual) == str(value):
            matched.append(key)

    verified = len(matched) >= 3
    confidence = "high" if len(matched) >= 3 else ("medium" if len(matched) == 2 else "low")

    return {
        "employee_id": employee_id,
        "verified": verified,
        "verification_method": "knowledge_based",
        "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        "confidence": confidence,
        "items_matched": matched,
        "items_provided": len(items) if items else 0,
    }


def _reset_password(db: dict, **kwargs: Any) -> dict:
    """Reset an employee's password."""
    employee_id = kwargs.get("employee_id", "")
    account_type = kwargs.get("account_type", "standard")
    if account_type == "admin":
        return {"error": True, "message": "Admin password resets require IT Security approval. Please escalate."}
    accounts = db.get("accounts", {})
    if employee_id in accounts:
        accounts[employee_id]["password_last_changed"] = datetime.now(timezone.utc).isoformat()
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
        "ticket_id": f"TKT_{uuid.uuid4().hex[:8].upper()}",
        "employee_id": kwargs.get("employee_id", ""),
        "category": kwargs.get("category", ""),
        "summary": kwargs.get("summary", ""),
        "action_taken": kwargs.get("action_taken", ""),
        "status": kwargs.get("status", "open"),
        "created_at": datetime.now(timezone.utc).isoformat(),
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
        "install_id": f"INS_{uuid.uuid4().hex[:8].upper()}",
        "status": "installed",
        "software_name": software_name,
    }


def _provision_vpn_access(db: dict, **kwargs: Any) -> dict:
    """Provision VPN access."""
    return {
        "vpn_id": f"VPN_{uuid.uuid4().hex[:8].upper()}",
        "status": "provisioned",
        "access_level": kwargs.get("access_level", "standard"),
        "employee_id": kwargs.get("employee_id", ""),
    }


def _create_access_request(db: dict, **kwargs: Any) -> dict:
    """Create an access request."""
    return {
        "access_request_id": f"AR_{uuid.uuid4().hex[:8].upper()}",
        "status": "submitted",
        "resource_name": kwargs.get("resource_name", ""),
        "access_level": kwargs.get("access_level", "read"),
    }


def _check_approval_status(db: dict, **kwargs: Any) -> dict:
    """Check approval ticket status."""
    employee_id = kwargs.get("employee_id", "")
    request_type = kwargs.get("request_type", "")
    approvals = db.get("approvals", [])
    for approval in approvals:
        if (approval.get("employee_id") == employee_id
                and approval.get("request_type") == request_type):
            return approval
    return {
        "employee_id": employee_id,
        "request_type": request_type,
        "status": "no_ticket_found",
        "message": f"No approval ticket found for {request_type} request.",
    }


def _verify_customer_identity(db: dict, **kwargs: Any) -> dict:
    """Verify customer identity (FINRA)."""
    customer_id = kwargs.get("customer_id", "")
    return {
        "customer_id": customer_id,
        "verified": True,
        "verification_method": kwargs.get("verification_method", "knowledge_based"),
        "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        "confidence": "high",
    }


def _verify_dual_authorization(db: dict, **kwargs: Any) -> dict:
    """Check dual authorization status."""
    request_id = kwargs.get("request_id", "")
    req = _find_in_collection(db, "activity.pending_requests", "request_id", request_id)
    amount = 0
    if req is not None:
        amount = req.get("details", {}).get("amount", 0)
    dual_required = amount >= 250000
    return {
        "request_id": request_id,
        "dual_auth_required": dual_required,
        "authorizations": [],
        "authorization_complete": not dual_required,
        "missing_authorizers": 2 if dual_required else 0,
    }


def _get_full_history(db: dict, **kwargs: Any) -> dict:
    """Retrieve full customer history."""
    customer_id = kwargs.get("customer_id", "")
    activity = db.get("activity", {})
    return {
        "customer_id": customer_id,
        "accounts": [
            {
                "account_id": db.get("account_status", {}).get("account_id", ""),
                "money_movements": activity.get("money_movements", []),
                "orders": activity.get("orders", []),
                "trades": activity.get("trades", []),
            }
        ],
        "total_records": (
            len(activity.get("money_movements", []))
            + len(activity.get("orders", []))
            + len(activity.get("trades", []))
        ),
    }


# ── Policy access ─────────────────────────────────────────

def _read_policy(db: dict, **kwargs: Any) -> str:
    """Return the full policy text."""
    return db.get("_policy_text", "No policy available.")


# ── Handler registry ──────────────────────────────────────

_HANDLERS: dict[str, Any] = {
    # All domains
    "record_decision": _record_decision,
    "read_policy": _read_policy,

    # FINRA
    "query_activity": lambda db, **kw: db.get("activity", {}),
    "query_customer_profile": lambda db, **kw: db.get("customer_profile", {}),
    "query_account_status": lambda db, **kw: db.get("account_status", {}),
    "process_wire_transfer": _process_wire_transfer,
    "hold_transaction": _hold_transaction,
    "create_alert": _create_alert,
    "open_case": _open_case,
    "escalate_to_compliance": _escalate,
    "file_sar": _file_sar,
    "file_ctr": _file_ctr,
    "dismiss_alert": _dismiss_alert,
    "update_request_status": _update_request_status,
    "verify_customer_identity": _verify_customer_identity,
    "verify_dual_authorization": _verify_dual_authorization,
    "get_full_history": _get_full_history,

    # Retail
    "lookup_order": lambda db, **kw: _lookup_by_id_or_customer(db, "orders", kw),
    "lookup_customer_profile": lambda db, **kw: db.get("customer_profile", {}),
    "process_refund": _process_refund,
    "process_exchange": _process_exchange,
    "apply_store_credit": _apply_store_credit,
    "deny_refund": _deny_refund,
    "escalate_to_manager": _escalate,
    "flag_account": _flag_account,
    "check_return_eligibility": _check_return_eligibility,

    # HelpDesk
    "lookup_employee": lambda db, **kw: _lookup_employee(db, kw),
    "verify_identity": _verify_identity,
    "reset_password": _reset_password,
    "unlock_account": _unlock_account,
    "provision_vpn_access": _provision_vpn_access,
    "install_software": _install_software,
    "create_access_request": _create_access_request,
    "escalate_to_tier2": _escalate,
    "escalate_to_it_security": _escalate,
    "check_approval_status": _check_approval_status,
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


def _lookup_by_id_or_customer(db: dict, collection: str, kwargs: dict) -> Any:
    """Look up records by order_id or customer_id."""
    records = db.get(collection, [])
    if not isinstance(records, list):
        return records

    order_id = kwargs.get("order_id")
    if order_id:
        for r in records:
            if isinstance(r, dict) and r.get("order_id") == order_id:
                return r
        return {"error": f"Order {order_id} not found"}

    customer_id = kwargs.get("customer_id")
    if customer_id:
        return [r for r in records if isinstance(r, dict) and r.get("customer_id") == customer_id]

    return records


def _lookup_employee(db: dict, kwargs: dict) -> Any:
    """Look up employee from environment_setup data stored in db."""
    employee_id = kwargs.get("employee_id")
    name = kwargs.get("name")
    email = kwargs.get("email")

    # Check accounts dict for employee data
    accounts = db.get("accounts", {})
    employee_data = db.get("employee", {})

    if employee_id and employee_data.get("employee_id") == employee_id:
        return employee_data
    if name and employee_data.get("display_name") == name:
        return employee_data
    if email and employee_data.get("email") == email:
        return employee_data

    # Fallback: return account info if employee_id matches
    if employee_id and employee_id in accounts:
        return {"employee_id": employee_id, **accounts[employee_id]}

    return {"error": "Employee not found"}


def _generic_lookup(db: dict, tool_name: str, **kwargs: Any) -> Any:
    """Fallback: search all DB collections for records matching kwargs."""
    # Try to find any collection that has matching records
    for key, value in db.items():
        if isinstance(value, list):
            for record in value:
                if isinstance(record, dict) and _matches(record, kwargs):
                    return record
        elif isinstance(value, dict):
            if _matches(value, kwargs):
                return value

    return {"message": f"No data found for {tool_name}", "args": kwargs}


def _matches(record: dict, kwargs: dict) -> bool:
    """Check if a record matches any of the provided kwargs."""
    if not kwargs:
        return False
    for k, v in kwargs.items():
        if k in record and record[k] == v:
            return True
    return False


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
