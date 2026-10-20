"""Pure, dependency-free parsing of the actor's input fields.

Kept out of actor.py (which imports the Apify SDK) so address and gate parsing
can be unit-tested without the runtime, and so no mis-shaped input can crash a
run before any work is done.

Every function tolerates whatever shape the form, the API, or the AI assistant
sends: a plain string, a delimited string (comma / space / newline / semicolon),
a list with junk items in it, a wrapped dict like {"email": "a@b.com"}, or the
wrong type entirely. The contract is simple: give back clean data, never raise.
"""
from __future__ import annotations

import re

# Pull real-looking addresses out of any text. This turns "a@b.com, c@d.com",
# "Jane Doe <jane@x.io>" and a messy paste into the same clean list, and makes a
# stray int or "notanemail" yield nothing instead of crashing.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _texts(value) -> list[str]:
    """Flatten any shape the email/emails fields arrive in into raw strings.

    A string stays as-is; a list/tuple/set is flattened item by item; a dict is
    flattened over its values (the API or AI may wrap each address); anything
    else is stringified so a stray int or nested list can never reach .strip()."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for v in value.values():
            out += _texts(v)
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for v in value:
            out += _texts(v)
        return out
    return [str(value)]


def collect_emails(inp: dict) -> list[str]:
    """Every address in the input, however it was shaped, lower-cased and deduped.

    Reads both the single 'email' field and the bulk 'emails' field, accepts a
    delimited string or a list (even one holding non-strings or wrapper dicts),
    and extracts only well-formed addresses. Returns [] when there are none;
    it never raises, so the caller can fail cleanly instead of crashing."""
    seen: set[str] = set()
    clean: list[str] = []
    for text in _texts(inp.get("email")) + _texts(inp.get("emails")):
        for match in _EMAIL_RE.findall(text):
            e = match.lower()
            if e not in seen:
                seen.add(e)
                clean.append(e)
    return clean


def confidence_gate(value, default: int = 80) -> float:
    """minConfidencePct (0..100) -> a 0..1 gate, tolerant of a string or junk.

    Apify's form sends an int, but the API and the AI assistant can send "90" or
    omit it; a non-number falls back to the default instead of crashing the run.
    The result is clamped to [0, 1]."""
    try:
        pct = float(value)
    except (TypeError, ValueError):
        pct = float(default)
    return max(0.0, min(1.0, pct / 100.0))
