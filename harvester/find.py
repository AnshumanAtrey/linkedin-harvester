"""BYOK single-email lookup: email (+ optional name/body) -> LinkedIn + confidence.

This is the thin entrypoint the Apify actor and the CLI share. It builds one
Person and runs the same resolver cascade the batch pipeline uses, so the gmail
fix (AI name-split -> name-only convergence dork) lives in ONE place.

Bring your own keys (all optional, read from env / .env):
  GROQ_API_KEY   - AI brain: splits concatenated local-parts, scores ambiguous
  BRAVE_API_KEY  - primary search for the dork (or GOOGLE_CSE_KEY + GOOGLE_CSE_CX)
  FINDYMAIL_API_KEY / BRIGHTDATA_API_KEY - backfill / scrape (off by default)

CLI:
  python -m harvester.find anshumanatrey@gmail.com
  python -m harvester.find someone@company.com --name "Jane Doe"
"""
from __future__ import annotations

import os
import re
import sys
import json
from pathlib import Path

from harvester.models import Person, Email
from harvester import ai
from harvester.enrich import enrich
from harvester.resolve.cascade import resolve
from harvester.extract import (
    extract, _company_from_domain, _personal_linkedin, LINKEDIN_RE,
)
from config import ROLE_LOCALPARTS, CONFIDENCE_THRESHOLD


def load_dotenv(path: str = ".env") -> None:
    """Minimal .env loader so BYOK keys are picked up without extra deps."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def name_from_localpart(local: str, allow_ai: bool = True) -> str:
    """Derive a person name from an email local-part.

    Regex handles first.last / first_last. A single concatenated token
    (anshumanatrey) is where the AI earns its keep - it splits what regex can't,
    but ONLY when the flow permits it (allow_ai). In the regex flow we just take
    the token as-is. Returns "" when the local-part is clearly not a personal name.
    """
    local = local.split("+", 1)[0]
    toks = [re.sub(r"\d+$", "", t) for t in re.split(r"[._\-]+", local) if t and not t.isdigit()]
    toks = [t for t in toks if len(t) >= 2]
    if len(toks) >= 2:
        return " ".join(t.capitalize() for t in toks[:3])

    if allow_ai and ai.available():
        got = ai.ask_json(
            "Split this email local-part into the person's likely full name. "
            f"local-part: {local!r}. Return JSON {{\"full\": \"First Last\"}} or "
            "{\"full\": null} if it is not a personal name (e.g. a handle or role)."
        )
        if got and got.get("full"):
            return str(got["full"]).strip()

    return toks[0].capitalize() if toks else ""


def build_person(email: str, name: str | None = None, body: str | None = None,
                 do_enrich: bool = True, flow=None) -> Person:
    if flow is None:
        from harvester.flow import BALANCED
        flow = BALANCED
    email = email.strip().lower()
    local, _, domain = email.partition("@")

    # Role mailboxes are never a person — don't fabricate a name or spend a query.
    base = re.split(r"[._+\-]", local)[0]
    if local in ROLE_LOCALPARTS or base in ROLE_LOCALPARTS:
        return Person(name="", email=email, domain=domain, company=None)

    # ENRICH first: gather every deterministic signal (real name, company,
    # handles, linked socials) before we resort to guessing anything.
    bag = enrich(email) if do_enrich else {}

    # If we got a body, the existing extractor mines name/company/title/signature.
    person = extract(Email("byok", name or "", email, "", body, "")) if body else None
    if person is None:
        person = Person(
            name="", email=email, domain=domain,
            company=_company_from_domain(domain),
            signature_linkedin=_personal_linkedin(body) if body else None,
        )

    # Name precedence: explicit arg > enrichment (KNOWN, e.g. GitHub commit author)
    # > body signature > local-part split (the AI guess, gated by the flow).
    person.name = (name or bag.get("best_name") or person.name
                   or name_from_localpart(local, allow_ai=flow.ai_extract))
    person.company = person.company or bag.get("company")
    person.enrichment = bag
    return person


def find_linkedin(email: str, name: str | None = None, body: str | None = None,
                  mode: str = "incremental", do_enrich: bool = True, flow=None) -> dict:
    """Resolve one email to a LinkedIn URL + confidence. Pure data out."""
    if flow is None:
        from harvester.flow import BALANCED
        flow = BALANCED
    person = build_person(email, name, body, do_enrich=do_enrich, flow=flow)
    res = resolve(person, mode=mode, flow=flow)
    passed = res.confidence >= flow.gate
    bag = person.enrichment or {}
    return {
        "email": email,
        "flow": {"ai_extract": flow.ai_extract, "ai_score": flow.ai_score,
                 "escalate_only": flow.escalate_only},
        "derived_name": person.name or None,
        "name_source": (bag.get("names") or [{}])[0].get("source") if bag.get("best_name") else "regex/guess",
        "company": person.company,
        "linkedin_url": res.linkedin_url,
        "confidence": res.confidence,
        "source": res.source,
        "evidence": res.evidence,
        "gate_threshold": flow.gate,
        "passes_gate": passed,            # True = confident enough to scrape
        "found": res.linkedin_url is not None,
        "cost_usd": res.cost_usd,
        # the deterministic bag the AI gets to reason over
        "signals": {
            "names": bag.get("names"),
            "company": bag.get("company"),
            "location": bag.get("location"),
            "twitter": bag.get("twitter"),
            "website": bag.get("website"),
            "handles": bag.get("handles"),
            "linkedin_urls": bag.get("linkedin_urls"),
            "confirmed_socials": bag.get("confirmed_socials"),
        },
    }


def _cli() -> None:
    load_dotenv()
    from harvester.flow import PRESETS, BALANCED
    args = sys.argv[1:]
    if not args:
        print("usage: python -m harvester.find <email> [--name 'Full Name'] "
              "[--mode incremental|backfill] [--flow regex|balanced|full]")
        sys.exit(1)
    email = args[0]
    name = args[args.index("--name") + 1] if "--name" in args else None
    mode = args[args.index("--mode") + 1] if "--mode" in args else os.environ.get("RUN_MODE", "incremental")
    flow = PRESETS.get(args[args.index("--flow") + 1], BALANCED) if "--flow" in args else BALANCED

    brain = ai.provider_label() if (flow.ai_extract or flow.ai_score) else "none (regex flow)"
    print(f"flow: extract_ai={flow.ai_extract} score_ai={flow.ai_score} | brain: {brain}")
    result = find_linkedin(email, name=name, mode=mode, flow=flow)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _cli()
