"""Apify Actor entrypoint.

Thin glue: read the input form, map the simple "AI assistance" dropdown to a
Flow, push the bring-your-own keys into the environment, then run the shared
single-email pipeline (harvester.find) over every email. All the real logic
lives in the package; this only adapts Apify I/O.
"""
from __future__ import annotations

import os

from apify import Actor

from harvester.inputs import collect_emails, confidence_gate

# Input field -> environment variable the resolvers/AI read at call time.
_KEY_MAP = {
    "groqApiKey": "GROQ_API_KEY",
    "braveApiKey": "BRAVE_API_KEY",
    "googleCseKey": "GOOGLE_CSE_KEY",
    "googleCseCx": "GOOGLE_CSE_CX",
    "brightdataApiKey": "BRIGHTDATA_API_KEY",
    "findymailApiKey": "FINDYMAIL_API_KEY",
}


async def _charge(event: str) -> None:
    """Charge a pay-per-event, but never crash a run if pricing isn't set."""
    try:
        await Actor.charge(event)
    except Exception:  # noqa: BLE001
        pass


async def _set_status(message: str) -> None:
    """Set the run's status message without ever failing a finished run.

    The API stores the message BEFORE the SDK parses its response, and the SDK then
    validates the run object against an origin enum that does not include Apify's
    newer run origins (APIFY_AI — the platform's AI-assistant channel). That parse
    raises, and it used to turn every assistant-started run into FAILED after all its
    work was already done and pushed. Catching it keeps the message set and the run
    green, and covers any future origin the bundled enum has not caught up with.
    """
    try:
        await Actor.set_status_message(message)
    except Exception as exc:  # noqa: BLE001
        Actor.log.debug(f"status message stored but not confirmed by the SDK: {exc}")


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
        gate = confidence_gate(inp.get("minConfidencePct"))
        flow = Flow(ai_extract=preset.ai_extract, ai_score=preset.ai_score,
                    escalate_only=preset.escalate_only, gate=gate)

        mode = inp.get("runMode", "incremental")
        # Public-profile enrichment (GitHub, Gravatar, PGP, handle probes) is the
        # only resolver that works without a search key, so it is on by default.
        # It was off, which silently disabled every key-less lookup on the platform.
        deep = bool(inp.get("deepEnrich", True))

        emails = collect_emails(inp)
        if not emails:
            # A clean, explained failure instead of a stack trace. The Console form
            # validates the address shape before the run (INPUT_SCHEMA patterns), so
            # this mainly guards API/MCP callers; the message shows the right format.
            await Actor.fail(status_message=(
                "No valid email found in the input. Enter one email per row in "
                "'Emails (bulk)', or several separated by commas, e.g. "
                "jane.doe@stripe.com, john@acme.com."))
            return

        await _charge("actor_start")
        Actor.log.info(f"flow={inp.get('aiMode', 'balanced')} gate={gate} "
                       f"deep_enrich={deep} emails={len(emails)}")

        found = confident = failed = 0
        for email in emails:
            await _charge("email_processed")
            try:
                result = find_linkedin(email, mode=mode, do_enrich=deep, flow=flow)
            except Exception as exc:  # noqa: BLE001 - one bad address must not kill the batch
                Actor.log.warning(f"{email} -> lookup failed: {exc}")
                failed += 1
                result = {"email": email, "found": False, "linkedin_url": None,
                          "confidence": 0.0, "passes_gate": False, "error": str(exc)}
            if result.get("passes_gate"):
                await _charge("profile_found")
                confident += 1
            if result.get("found"):
                found += 1
            await Actor.push_data(result)
            Actor.log.info(
                f"{email} -> {result.get('linkedin_url')} "
                f"(conf {result.get('confidence')}, {result.get('source')})"
            )

        # Say plainly what happened so an empty or weak result never looks like a broken run.
        total = len(emails)
        if found == 0:
            msg = (f"Checked {total} email(s); no LinkedIn profile found. Work emails "
                   f"(first.last@company.com) resolve best; add a Brave Search key for wider coverage.")
        else:
            msg = (f"Checked {total} email(s): {found} profile(s) found, "
                   f"{confident} above the {int(gate * 100)}% confidence gate.")
        if failed:
            msg += f" {failed} lookup(s) errored and were returned with found=false."
        await _set_status(msg)
        Actor.log.info(msg)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
