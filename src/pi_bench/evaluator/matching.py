"""Shared value matcher for argument filters and state comparisons.

An expected value that is a non-empty dict whose keys ALL start with "$" is
an operator spec; several operators in one spec are combined with AND.
Any other expected value keeps exact-equality semantics (the historical
behavior of ``arguments`` / ``args_match`` / ``equals``).

Operators:
    $eq, $ne        equality / inequality (missing key compares as None)
    $in, $nin       membership in / absence from a list
    $contains       strings: case-insensitive substring;
                    lists: membership (strings compared case-insensitively);
                    a list operand requires every element to be contained
    $regex          re.search with IGNORECASE on str(value)
    $exists         bool: key present (True) or absent (False)
    $ieq            string equality ignoring case and whitespace runs
    $num            numeric equality after parsing ("8,000.00" == 8000)
    $gt $gte $lt $lte   numeric comparisons (same parsing as $num)
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping

OPERATORS = frozenset({
    "$eq", "$ne", "$in", "$nin", "$contains", "$regex", "$exists",
    "$ieq", "$num", "$gt", "$gte", "$lt", "$lte",
})

_NUMERIC_OPS = frozenset({"$num", "$gt", "$gte", "$lt", "$lte"})
_LIST_OPS = frozenset({"$in", "$nin"})

# Sentinel for "key/path not present".
MISSING = object()


class OperatorError(ValueError):
    """Raised for an unknown operator or an invalid operand."""


def is_operator_spec(value: Any) -> bool:
    """True when value is a non-empty dict whose keys all start with '$'."""
    return (
        isinstance(value, dict)
        and len(value) > 0
        and all(isinstance(k, str) and k.startswith("$") for k in value)
    )


def spec_errors(spec: Any) -> list[str]:
    """Return authoring errors for one operator spec (empty if valid)."""
    if not is_operator_spec(spec):
        return []
    errors: list[str] = []
    for op, operand in spec.items():
        if op not in OPERATORS:
            errors.append(
                f"unknown operator '{op}' (allowed: {', '.join(sorted(OPERATORS))})"
            )
            continue
        if op in _LIST_OPS and not isinstance(operand, list):
            errors.append(f"operator '{op}' requires a list operand")
        elif op == "$exists" and not isinstance(operand, bool):
            errors.append("operator '$exists' requires a boolean operand")
        elif op == "$regex":
            if not isinstance(operand, str):
                errors.append("operator '$regex' requires a string pattern")
            else:
                try:
                    re.compile(operand)
                except re.error as exc:
                    errors.append(f"operator '$regex' has invalid pattern: {exc}")
        elif op == "$ieq" and not isinstance(operand, str):
            errors.append("operator '$ieq' requires a string operand")
        elif op in _NUMERIC_OPS and _to_number(operand) is None:
            errors.append(f"operator '{op}' requires a numeric operand, got {operand!r}")
    return errors


def mapping_spec_errors(expected: Any) -> list[str]:
    """Validate every operator spec inside a {field: value-or-spec} mapping."""
    if not isinstance(expected, dict):
        return []
    errors: list[str] = []
    for key, value in expected.items():
        for err in spec_errors(value):
            errors.append(f"{key}: {err}")
    return errors


def match_value(actual: Any, expected: Any, present: bool = True) -> bool:
    """Match one value against a literal or an operator spec.

    ``present`` says whether the key/path existed at all; when it did not,
    ``actual`` should be None. Raises OperatorError on an invalid spec.
    """
    if not is_operator_spec(expected):
        return actual == expected

    errors = spec_errors(expected)
    if errors:
        raise OperatorError("; ".join(errors))

    return all(_apply(op, operand, actual, present) for op, operand in expected.items())


def match_mapping(
    record: Any,
    expected: Mapping[str, Any],
    getter: Callable[[Any, str], Any] | None = None,
) -> bool:
    """Match every {field: value-or-spec} pair against a record (AND).

    ``getter(record, field)`` returns the field value or MISSING; by default
    it is a plain dict lookup. Literal values keep exact equality with a
    missing field compared as None (historical ``tool_called_with``
    semantics).
    """
    get = getter or _dict_get
    for key, exp in expected.items():
        raw = get(record, key)
        present = raw is not MISSING
        actual = raw if present else None
        if not match_value(actual, exp, present=present):
            return False
    return True


# ── internals ────────────────────────────────────────────


def _dict_get(record: Any, key: str) -> Any:
    if isinstance(record, dict) and key in record:
        return record[key]
    return MISSING


def _apply(op: str, operand: Any, actual: Any, present: bool) -> bool:
    if op == "$exists":
        return present == bool(operand)
    if op == "$eq":
        return actual == operand
    if op == "$ne":
        return actual != operand
    if op == "$in":
        return actual in operand
    if op == "$nin":
        return actual not in operand
    if not present or actual is None:
        return False
    if op == "$contains":
        needles = operand if isinstance(operand, list) else [operand]
        return all(_contains(actual, n) for n in needles)
    if op == "$regex":
        if isinstance(actual, (list, tuple)):
            return any(re.search(operand, str(item), re.IGNORECASE) for item in actual)
        return re.search(operand, str(actual), re.IGNORECASE) is not None
    if op == "$ieq":
        return _norm_ws(actual) == _norm_ws(operand)
    # numeric operators
    left = _to_number(actual)
    right = _to_number(operand)
    if left is None or right is None:
        return False
    if op == "$num":
        return left == right
    if op == "$gt":
        return left > right
    if op == "$gte":
        return left >= right
    if op == "$lt":
        return left < right
    if op == "$lte":
        return left <= right
    raise OperatorError(f"unknown operator '{op}'")  # pragma: no cover


def _contains(actual: Any, needle: Any) -> bool:
    if isinstance(actual, str):
        return str(needle).lower() in actual.lower()
    if isinstance(actual, (list, tuple, set)):
        for item in actual:
            if item == needle:
                return True
            if isinstance(item, str) and isinstance(needle, str) and item.lower() == needle.lower():
                return True
        return False
    return False


def _norm_ws(value: Any) -> str:
    return " ".join(str(value).split()).lower()


_NUM_STRIP_RE = re.compile(r"[,\s_]")


def _to_number(value: Any) -> Decimal | None:
    """Parse int/float/numeric string ("8,000.00", "$1,200") into a Decimal."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return Decimal(str(value))
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        text = _NUM_STRIP_RE.sub("", value.strip())
        if text[:1] in ("$", "€", "£"):
            text = text[1:]
        if not text:
            return None
        try:
            number = Decimal(text)
        except InvalidOperation:
            return None
        if not number.is_finite():
            return None
        return number
    return None
