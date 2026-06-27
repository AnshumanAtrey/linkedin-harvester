"""Apify Actor entrypoint.

Thin glue: read the input form, map the simple "AI assistance" dropdown to a
Flow, push the bring-your-own keys into the environment, then run the shared
single-email pipeline (harvester.find) over every email. All the real logic
lives in the package; this only adapts Apify I/O.
"""
from __future__ import annotations

import os

from apify import Actor

# Input field -> environment variable the resolvers/AI read at call time.
_KEY_MAP = {
    "groqApiKey": "GROQ_API_KEY",
    "braveApiKey": "BRAVE_API_KEY",
    "googleCseKey": "GOOGLE_CSE_KEY",
    "googleCseCx": "GOOGLE_CSE_CX",
    "brightdataApiKey": "BRIGHTDATA_API_KEY",
    "findymailApiKey": "FINDYMAIL_API_KEY",
}


def _collect_emails(inp: dict) -> list[str]:
    raw = []
    if inp.get("email"):
        raw.append(inp["email"])
    raw += inp.get("emails") or []
    seen, clean = set(), []
    for e in raw:
        e = (e or "").strip().lower()
        if e and "@" in e and e not in seen:
            seen.add(e)
            clean.append(e)
    return clean


async def _charge(event: str) -> None:
    """Charge a pay-per-event, but never crash a run if pricing isn't set."""
    try:
        await Actor.charge(event)
    except Exception:  # noqa: BLE001
        pass


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}

        for field, env in _KEY_MAP.items():
            if inp.get(field):
                os.environ[env] = str(inp[field]).strip()

        # Imported after keys are in the environment.
        from harvester.find import find_linkedin
        from harvester.flow import PRESETS, BALANCED, Flow

        preset = PRESETS.get(inp.get("aiMode", "balanced"), BALANCED)
        gate = max(0.0, min(1.0, (inp.get("minConfidencePct") or 80) / 100.0))
        flow = Flow(ai_extract=preset.ai_extract, ai_score=preset.ai_score,
                    escalate_only=preset.escalate_only, gate=gate)

        mode = inp.get("runMode", "incremental")
        deep = bool(inp.get("deepEnrich", False))

        emails = _collect_emails(inp)
        if not emails:
            raise ValueError("Provide at least one email (field 'email' or 'emails').")

        await _charge("actor_start")
        Actor.log.info(f"flow={inp.get('aiMode', 'balanced')} gate={gate} "
                       f"deep_enrich={deep} emails={len(emails)}")

        for email in emails:
            await _charge("email_processed")
            result = find_linkedin(email, mode=mode, do_enrich=deep, flow=flow)
            if result.get("passes_gate"):
                await _charge("profile_found")
            await Actor.push_data(result)
            Actor.log.info(
                f"{email} -> {result.get('linkedin_url')} "
                f"(conf {result.get('confidence')}, {result.get('source')})"
            )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
