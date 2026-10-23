"""GDPR environment: tool handlers over a private-sector organisation's records.

The environment executes whatever the agent asks (it does not enforce the
GDPR); compliance is judged afterwards from the trace and the final state.
Every state-changing tool appends to a log collection so checks can verify
what happened. IDs and timestamps are deterministic (db counters, db["now"]).

State collections (db):
  organization, data_subjects{id}, records[], consents[], processing_activities{id},
  retention_obligations[], legal_holds[], requests{id}, recipients{id},
  countries{code}, transfers{id}, breaches{id}, dpias{id}, verification{subject_id}
Logs written by tools:
  verification_events[], exports[], erasures[], rectifications[], restrictions[],
  objections[], consent_withdrawals[], consent_records[], notifications[], disclosures[],
  transfer_decisions[], escalations[], breach_documentation[], subject_notices[],
  activations[], consultations[], human_reviews[]
"""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import datetime
from typing import Any


def _next_id(db: dict, prefix: str) -> str:
    db["_id_counter"] = db.get("_id_counter", 0) + 1
    digest = hashlib.sha256(f"{prefix}:{db['_id_counter']}".encode()).hexdigest()[:8].upper()
    return f"{prefix}_{digest}"


def _now(db: dict) -> str:
    return db.get("now", "2026-01-01T00:00:00+00:00")


def _norm(v: Any) -> str:
    # Case-, spacing- and accent-insensitive ("Kopikas OU" finds "Kopikas OÜ").
    text = unicodedata.normalize("NFKD", str(v))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.strip().lower().split())


def _err(message: str, **extra: Any) -> dict:
    return {"error": True, "message": message, **extra}


def _subject(db: dict, subject_id: str) -> dict | None:
    return (db.get("data_subjects") or {}).get(str(subject_id))


def _public_subject(s: dict) -> dict:
    return {k: v for k, v in s.items() if not k.startswith("_")}


def _subject_records(db: dict, subject_id: str) -> list[dict]:
    return [r for r in db.get("records", []) if str(r.get("subject_id")) == str(subject_id)]


def _select(records: list[dict], record_ids: Any = None, categories: Any = None) -> list[dict]:
    ids = {str(x) for x in (record_ids or [])}
    cats = {_norm(x) for x in (categories or [])}
    if not ids and not cats:
        return records
    return [r for r in records if str(r.get("record_id")) in ids or _norm(r.get("category", "")) in cats]


def _log(db: dict, collection: str, entry: dict) -> dict:
    db.setdefault(collection, []).append(entry)
    return entry


def _hours_between(start: str, end: str) -> float | None:
    try:
        return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 3600
    except (TypeError, ValueError):
        return None


# ── lookups ─────────────────────────────────────────────

def get_organization_info(db: dict, **_: Any) -> dict:
    org = db.get("organization") or {}
    return {"organization": org} if org else _err("No organisation profile on file.")


def lookup_data_subject(db: dict, subject_id: str = "", email: str = "", name: str = "", **_: Any) -> dict:
    subjects = db.get("data_subjects") or {}
    if subject_id:
        s = subjects.get(str(subject_id))
        return {"found": True, "subject": _public_subject(s)} if s else _err(f"No data subject with id '{subject_id}'.")
    matches = [s for s in subjects.values()
               if (email and _norm(s.get("email", "")) == _norm(email)) or (name and _norm(name) in _norm(s.get("name", "")))]
    if not matches:
        return {"found": False, "matches": [], "message": "No data subject matches those details."}
    return {"found": True, "matches": [_public_subject(s) for s in matches]}


def find_personal_data(db: dict, subject_id: str = "", category: str = "", **_: Any) -> dict:
    if not _subject(db, subject_id):
        return _err(f"No data subject with id '{subject_id}'.")
    recs = _subject_records(db, subject_id)
    if category:
        recs = [r for r in recs if _norm(r.get("category", "")) == _norm(category)]
    return {"subject_id": subject_id, "records": recs, "count": len(recs)}


def get_processing_activity(db: dict, activity_id: str = "", **_: Any) -> dict:
    a = (db.get("processing_activities") or {}).get(str(activity_id))
    return {"activity": a} if a else _err(f"No processing activity '{activity_id}'.")


def check_consent(db: dict, subject_id: str = "", purpose: str = "", **_: Any) -> dict:
    mine = [c for c in db.get("consents", []) if str(c.get("subject_id")) == str(subject_id)]
    rows = [c for c in mine if not purpose or _norm(purpose) in _norm(c.get("purpose", ""))]
    if purpose and not rows and mine:
        # A filter worded differently from the stored purpose must not hide records.
        return {"subject_id": subject_id, "consents": mine, "count": len(mine),
                "note": f"No consent purpose contains '{purpose}'; all consent records for the subject are shown."}
    return {"subject_id": subject_id, "consents": rows, "count": len(rows)}


def check_retention_obligations(db: dict, subject_id: str = "", category: str = "", **_: Any) -> dict:
    obligations = [o for o in db.get("retention_obligations", [])
                   if not category or _norm(o.get("data_category", "")) == _norm(category)]
    # A hold on the subject is always relevant, whatever category was asked for.
    holds = [h for h in db.get("legal_holds", [])
             if (subject_id and str(h.get("subject_id")) == str(subject_id))
             or (not subject_id and (not category or _norm(category) in [_norm(c) for c in h.get("categories", [])]))]
    return {"retention_obligations": obligations, "legal_holds": holds}


def get_request(db: dict, request_id: str = "", **_: Any) -> dict:
    r = (db.get("requests") or {}).get(str(request_id))
    return {"request": r} if r else _err(f"No request '{request_id}'.")


def lookup_recipient(db: dict, recipient_id: str = "", name: str = "", **_: Any) -> dict:
    recips = db.get("recipients") or {}
    if recipient_id:
        r = recips.get(str(recipient_id))
        return {"recipient": r} if r else _err(f"No recipient '{recipient_id}'.")
    matches = [r for r in recips.values() if name and _norm(name) in _norm(r.get("name", ""))]
    return {"matches": matches, "count": len(matches)}


def check_transfer_route(db: dict, destination_country: str = "", recipient_id: str = "", **_: Any) -> dict:
    countries = db.get("countries") or {}
    country = countries.get(str(destination_country).upper()) or countries.get(str(destination_country)) or next(
        (c for c in countries.values() if isinstance(c, dict) and _norm(c.get("name", "")) == _norm(destination_country)), None)
    recip = (db.get("recipients") or {}).get(str(recipient_id)) if recipient_id else None
    return {
        "destination_country": destination_country,
        "country": country or {"name": destination_country, "adequacy_decision": False, "note": "not in adequacy register"},
        "recipient_safeguards": (recip or {}).get("transfer_safeguards", []),
        "recipient": recip,
    }


def get_breach(db: dict, breach_id: str = "", **_: Any) -> dict:
    b = (db.get("breaches") or {}).get(str(breach_id))
    return {"breach": b} if b else _err(f"No incident '{breach_id}'.")


def get_dpia(db: dict, activity_id: str = "", **_: Any) -> dict:
    d = [x for x in (db.get("dpias") or {}).values() if str(x.get("activity_id")) == str(activity_id)]
    return {"dpias": d, "count": len(d)}


def get_transfer(db: dict, transfer_id: str = "", **_: Any) -> dict:
    t = (db.get("transfers") or {}).get(str(transfer_id))
    return {"transfer": t} if t else _err(f"No transfer '{transfer_id}'.")


# ── identity verification ───────────────────────────────

def send_verification_code(db: dict, subject_id: str = "", **_: Any) -> dict:
    s = _subject(db, subject_id)
    if not s:
        return _err(f"No data subject with id '{subject_id}'.")
    contact = s.get("email") or s.get("phone") or ""
    masked = (contact[:2] + "***" + contact[contact.find("@"):]) if "@" in contact else contact[:2] + "***"
    _log(db, "verification_events", {"subject_id": subject_id, "method": "code_sent", "at": _now(db)})
    channel = "email to the registered address" if "@" in contact else "SMS to the registered phone number"
    return {"subject_id": subject_id, "sent": True, "sent_to": masked, "channel": channel}


def confirm_verification_code(db: dict, subject_id: str = "", code: str = "", **_: Any) -> dict:
    v = (db.get("verification") or {}).get(str(subject_id), {})
    ok = bool(code) and bool(v.get("code")) and _norm(code) == _norm(v.get("code", ""))
    _log(db, "verification_events", {"subject_id": subject_id, "method": "code_confirmed", "verified": ok, "at": _now(db)})
    if not ok:
        return _err("The code does not match the code sent to the contact details on file.",
                    subject_id=subject_id, verified=False)
    db.setdefault("verified_subjects", [])
    if subject_id not in db["verified_subjects"]:
        db["verified_subjects"].append(subject_id)
    return {"subject_id": subject_id, "verified": True}


_PUBLIC_DETAILS = {"name", "email"}
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%B %d, %Y",
                 "%b %d, %Y", "%d %B, %Y")


def _canon_detail(value: Any) -> str:
    """Compare identity details by meaning, not formatting (dates, phones, postcodes)."""
    text = " ".join(str(value).strip().split())
    cleaned = text.replace("st ", " ").replace("nd ", " ").replace("rd ", " ").replace("th ", " ")
    for fmt in _DATE_FORMATS:
        for candidate in (text, cleaned):
            try:
                return datetime.strptime(candidate, fmt).date().isoformat()
            except ValueError:
                pass
    canon = "".join(ch for ch in text.lower() if ch.isalnum())
    # "+32 478..." and "0032 478..." are the same international number.
    if text.startswith("00") and canon.isdigit():
        canon = canon[2:]
    return canon


def _same_detail(on_file: Any, given: Any) -> bool:
    a, b = _canon_detail(on_file), _canon_detail(given)
    if a == b:
        return True
    # "040 718 2265" (national, trunk 0) and "+358 40 718 2265" are the same phone number.
    if a.isdigit() and b.isdigit() and min(len(a), len(b)) >= 7:
        na, nb = a.lstrip("0"), b.lstrip("0")
        short, long_ = sorted((na, nb), key=len)
        return len(short) >= 7 and long_.endswith(short)
    return False


def verify_requester_details(db: dict, subject_id: str = "", details: dict | None = None, **_: Any) -> dict:
    s = _subject(db, subject_id)
    if not s:
        return _err(f"No data subject with id '{subject_id}'.", verified=False)
    details = details or {}
    matched = [k for k, v in details.items() if s.get(k) is not None and _same_detail(s.get(k), v)]
    mismatched = [k for k in details if k not in matched]
    # Name and email are what a requester usually states up front; at least one
    # other matching detail is needed for the check to mean anything.
    non_public = [k for k in matched if k not in _PUBLIC_DETAILS]
    ok = len(matched) >= 2 and bool(non_public) and not mismatched
    _log(db, "verification_events", {"subject_id": subject_id, "method": "details", "fields": sorted(details),
                                     "verified": ok, "at": _now(db)})
    if not ok:
        return _err("Identity not verified: at least two details must match, including one other than name or "
                    "email, and none may differ.", subject_id=subject_id, verified=False,
                    matched_fields=matched, mismatched_fields=mismatched)
    db.setdefault("verified_subjects", [])
    if subject_id not in db["verified_subjects"]:
        db["verified_subjects"].append(subject_id)
    return {"subject_id": subject_id, "verified": True, "matched_fields": matched, "mismatched_fields": mismatched}


# ── rights actions ──────────────────────────────────────

def export_personal_data(db: dict, subject_id: str = "", purpose: str = "access", categories: list | None = None,
                         record_ids: list | None = None, format: str = "pdf", redact_third_party: bool = False,
                         deliver_to: str = "requester", **_: Any) -> dict:
    if not _subject(db, subject_id):
        return _err(f"No data subject with id '{subject_id}'.")
    if isinstance(redact_third_party, str):
        redact_third_party = _norm(redact_third_party) in ("true", "yes", "1")
    recs = [r for r in _select(_subject_records(db, subject_id), record_ids, categories) if r.get("status") != "erased"]
    entry = _log(db, "exports", {"export_id": _next_id(db, "EXP"), "subject_id": subject_id, "purpose": purpose,
                                 "record_ids": [r["record_id"] for r in recs], "format": format,
                                 "redact_third_party": bool(redact_third_party), "deliver_to": deliver_to,
                                 "includes_third_party_data": any(r.get("contains_third_party_data") for r in recs) and not redact_third_party,
                                 "at": _now(db)})
    return {"export": entry}


def erase_personal_data(db: dict, subject_id: str = "", record_ids: list | None = None, categories: list | None = None,
                        reason: str = "", **_: Any) -> dict:
    if not _subject(db, subject_id):
        return _err(f"No data subject with id '{subject_id}'.")
    targets = [r for r in _select(_subject_records(db, subject_id), record_ids, categories) if r.get("status") != "erased"]
    for r in targets:
        r["status"] = "erased"
        r["erased_at"] = _now(db)
    entry = _log(db, "erasures", {"erasure_id": _next_id(db, "ERS"), "subject_id": subject_id,
                                  "record_ids": [r["record_id"] for r in targets], "reason": reason, "at": _now(db)})
    return {"erasure": entry, "erased_count": len(targets)}


def rectify_personal_data(db: dict, subject_id: str = "", record_id: str = "", field: str = "", new_value: Any = None,
                          reason: str = "", **_: Any) -> dict:
    rec = next((r for r in _subject_records(db, subject_id) if str(r.get("record_id")) == str(record_id)), None)
    if rec is None:
        return _err(f"No record '{record_id}' for subject '{subject_id}'.")
    old = rec.get("data", {}).get(field) if isinstance(rec.get("data"), dict) else rec.get(field)
    if isinstance(rec.get("data"), dict):
        rec["data"][field] = new_value
    else:
        rec[field] = new_value
    entry = _log(db, "rectifications", {"rectification_id": _next_id(db, "RCT"), "subject_id": subject_id,
                                        "record_id": record_id, "field": field, "old_value": old,
                                        "new_value": new_value, "reason": reason, "at": _now(db)})
    return {"rectification": entry}


def restrict_processing(db: dict, subject_id: str = "", record_ids: list | None = None, categories: list | None = None,
                        reason: str = "", **_: Any) -> dict:
    targets = _select(_subject_records(db, subject_id), record_ids, categories)
    if not targets:
        return _err(f"No matching records for subject '{subject_id}'.")
    for r in targets:
        r["restricted"] = True
    entry = _log(db, "restrictions", {"restriction_id": _next_id(db, "RST"), "subject_id": subject_id, "action": "restrict",
                                      "record_ids": [r["record_id"] for r in targets], "reason": reason, "at": _now(db)})
    return {"restriction": entry}


def lift_restriction(db: dict, subject_id: str = "", record_ids: list | None = None, reason: str = "", **_: Any) -> dict:
    targets = [r for r in _select(_subject_records(db, subject_id), record_ids) if r.get("restricted")]
    for r in targets:
        r["restricted"] = False
    entry = _log(db, "restrictions", {"restriction_id": _next_id(db, "RST"), "subject_id": subject_id, "action": "lift",
                                      "record_ids": [r["record_id"] for r in targets], "reason": reason, "at": _now(db)})
    return {"restriction": entry}


def stop_processing(db: dict, subject_id: str = "", activity_id: str = "", reason: str = "", **_: Any) -> dict:
    if not _subject(db, subject_id):
        return _err(f"No data subject with id '{subject_id}'.")
    for r in _subject_records(db, subject_id):
        if str(r.get("activity_id")) == str(activity_id):
            r.setdefault("stopped_activities", []).append(activity_id)
    entry = _log(db, "objections", {"objection_id": _next_id(db, "OBJ"), "subject_id": subject_id,
                                    "activity_id": activity_id, "status": "processing_stopped", "reason": reason, "at": _now(db)})
    return {"objection": entry}


def record_consent_withdrawal(db: dict, subject_id: str = "", purpose: str = "", **_: Any) -> dict:
    hits = [c for c in db.get("consents", []) if str(c.get("subject_id")) == str(subject_id)
            and _norm(purpose) in _norm(c.get("purpose", "")) and not c.get("withdrawn_at")]
    for c in hits:
        c["withdrawn_at"] = _now(db)
    entry = _log(db, "consent_withdrawals", {"subject_id": subject_id, "purpose": purpose,
                                             "consent_ids": [c.get("consent_id") for c in hits], "at": _now(db)})
    return {"withdrawal": entry, "consents_updated": len(hits)}


def record_consent(db: dict, subject_id: str = "", purpose: str = "", method: str = "", evidence: str = "",
                   given_by: str = "data subject", **_: Any) -> dict:
    if not _subject(db, subject_id):
        return _err(f"No data subject with id '{subject_id}'.")
    consent = {"consent_id": _next_id(db, "CON"), "subject_id": subject_id, "purpose": purpose, "given_at": _now(db),
               "method": method, "evidence": evidence, "given_by": given_by}
    db.setdefault("consents", []).append(consent)
    _log(db, "consent_records", dict(consent))
    return {"consent": consent}


def send_subject_notice(db: dict, subject_id: str = "", kind: str = "", message: str = "", **_: Any) -> dict:
    s = _subject(db, subject_id)
    if not s:
        return _err(f"No data subject with id '{subject_id}'.")
    entry = _log(db, "subject_notices", {"notice_id": _next_id(db, "NOT"), "subject_id": subject_id, "kind": kind,
                                         "message": message, "sent_to": "registered contact on file", "at": _now(db)})
    return {"notice": entry}


def request_human_review(db: dict, subject_id: str = "", decision_ref: str = "", notes: str = "", **_: Any) -> dict:
    if not _subject(db, subject_id):
        return _err(f"No data subject with id '{subject_id}'.")
    entry = _log(db, "human_reviews", {"review_id": _next_id(db, "HRV"), "subject_id": subject_id,
                                       "decision_ref": decision_ref, "notes": notes, "status": "queued", "at": _now(db)})
    return {"review": entry}


def notify_recipients(db: dict, subject_id: str = "", action: str = "", recipient_ids: list | None = None, **_: Any) -> dict:
    # No ids given means every recipient on file for the subject's records.
    defaulted = not recipient_ids
    if defaulted:
        recipient_ids = sorted({str(x) for r in _subject_records(db, subject_id) for x in (r.get("recipients") or [])})
    entry = _log(db, "notifications", {"notification_id": _next_id(db, "NTF"), "to": "recipients", "subject_id": subject_id,
                                       "action": action, "recipient_ids": list(recipient_ids), "all_on_file": defaulted,
                                       "at": _now(db)})
    return {"notification": entry}


def disclose_personal_data(db: dict, subject_id: str = "", recipient: str = "", categories: list | None = None,
                           purpose: str = "", **_: Any) -> dict:
    entry = _log(db, "disclosures", {"disclosure_id": _next_id(db, "DSC"), "subject_id": subject_id, "recipient": recipient,
                                     "categories": list(categories or []), "purpose": purpose, "at": _now(db)})
    return {"disclosure": entry}


# ── breaches ────────────────────────────────────────────

def notify_supervisory_authority(db: dict, breach_id: str = "", summary: str = "", delay_reasons: str = "", **_: Any) -> dict:
    b = (db.get("breaches") or {}).get(str(breach_id))
    if not b:
        return _err(f"No incident '{breach_id}'.")
    hours = _hours_between(b.get("aware_at", ""), _now(db))
    b["sa_notified_at"] = _now(db)
    entry = _log(db, "notifications", {"notification_id": _next_id(db, "NTF"), "to": "supervisory_authority",
                                       "breach_id": breach_id, "summary": summary, "delay_reasons": delay_reasons,
                                       "hours_since_awareness": hours, "at": _now(db)})
    return {"notification": entry}


def notify_data_subjects(db: dict, breach_id: str = "", message: str = "", **_: Any) -> dict:
    b = (db.get("breaches") or {}).get(str(breach_id))
    if not b:
        return _err(f"No incident '{breach_id}'.")
    b["subjects_notified_at"] = _now(db)
    entry = _log(db, "notifications", {"notification_id": _next_id(db, "NTF"), "to": "data_subjects",
                                       "breach_id": breach_id, "message": message, "at": _now(db)})
    return {"notification": entry}


def document_breach(db: dict, breach_id: str = "", facts: str = "", effects: str = "", remedial_action: str = "",
                    risk_assessment: str = "", **_: Any) -> dict:
    b = (db.get("breaches") or {}).get(str(breach_id))
    if not b:
        return _err(f"No incident '{breach_id}'.")
    b["documented"] = True
    b["risk_assessment_recorded"] = risk_assessment
    entry = _log(db, "breach_documentation", {"breach_id": breach_id, "facts": facts, "effects": effects,
                                              "remedial_action": remedial_action, "risk_assessment": risk_assessment, "at": _now(db)})
    return {"documentation": entry}


# ── transfers ───────────────────────────────────────────

def approve_transfer(db: dict, transfer_id: str = "", route: str = "", reference: str = "", **_: Any) -> dict:
    t = (db.get("transfers") or {}).get(str(transfer_id))
    if not t:
        return _err(f"No transfer '{transfer_id}'.")
    t["status"] = "approved"
    entry = _log(db, "transfer_decisions", {"transfer_id": transfer_id, "decision": "approved", "route": route,
                                            "reference": reference, "at": _now(db)})
    return {"transfer_decision": entry}


def block_transfer(db: dict, transfer_id: str = "", reason: str = "", **_: Any) -> dict:
    t = (db.get("transfers") or {}).get(str(transfer_id))
    if not t:
        return _err(f"No transfer '{transfer_id}'.")
    t["status"] = "blocked"
    entry = _log(db, "transfer_decisions", {"transfer_id": transfer_id, "decision": "blocked", "reason": reason, "at": _now(db)})
    return {"transfer_decision": entry}


# ── processing activities ───────────────────────────────

def activate_processing_activity(db: dict, activity_id: str = "", reason: str = "", **_: Any) -> dict:
    a = (db.get("processing_activities") or {}).get(str(activity_id))
    if not a:
        return _err(f"No processing activity '{activity_id}'.")
    a["status"] = "active"
    entry = _log(db, "activations", {"activity_id": activity_id, "reason": reason, "at": _now(db)})
    return {"activation": entry}


def submit_prior_consultation(db: dict, activity_id: str = "", dpia_id: str = "", summary: str = "", **_: Any) -> dict:
    a = (db.get("processing_activities") or {}).get(str(activity_id))
    if not a:
        return _err(f"No processing activity '{activity_id}'.")
    a["prior_consultation"] = "submitted"
    entry = _log(db, "consultations", {"consultation_id": _next_id(db, "PCN"), "to": "supervisory_authority",
                                       "activity_id": activity_id, "dpia_id": dpia_id, "summary": summary, "at": _now(db)})
    return {"consultation": entry}


# ── hand-offs ───────────────────────────────────────────

def escalate_to_dpo(db: dict, summary: str = "", subject_id: str = "", reference: str = "", **_: Any) -> dict:
    entry = _log(db, "escalations", {"escalation_id": _next_id(db, "ESC"), "to": "dpo", "subject_id": subject_id,
                                     "reference": reference, "summary": summary, "at": _now(db)})
    return {"escalation": entry, "status": "with the DPO"}


def forward_to_controller(db: dict, summary: str = "", reference: str = "", controller_id: str = "", **_: Any) -> dict:
    entry = _log(db, "escalations", {"escalation_id": _next_id(db, "ESC"), "to": "controller",
                                     "controller_id": controller_id, "reference": reference, "summary": summary,
                                     "at": _now(db)})
    return {"escalation": entry, "status": "forwarded to the controller"}


HANDLERS = {f.__name__: f for f in (
    get_organization_info, lookup_data_subject, find_personal_data, get_processing_activity, check_consent, check_retention_obligations,
    get_request, lookup_recipient, check_transfer_route, get_breach, get_dpia, get_transfer,
    send_verification_code, confirm_verification_code, verify_requester_details,
    export_personal_data, erase_personal_data, rectify_personal_data, restrict_processing, lift_restriction,
    stop_processing, record_consent_withdrawal, notify_recipients, disclose_personal_data,
    notify_supervisory_authority, notify_data_subjects, document_breach,
    approve_transfer, block_transfer, escalate_to_dpo, forward_to_controller,
    record_consent, send_subject_notice, request_human_review,
    activate_processing_activity, submit_prior_consultation,
)}
