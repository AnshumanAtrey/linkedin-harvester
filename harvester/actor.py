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


def _usd(amount) -> str:
    """A limit or a price as people read it: $0.025, $0.5, $5."""
    return "$" + (f"{float(amount):.4f}".rstrip("0").rstrip(".") or "0")


class _Budget:
    """The run's spending limit, which Apify says a run must stop at.

    An email is looked up only while the limit can pay its worst case, the email
    fee plus a confident match. Before this, a confident match past the limit was
    delivered free (2026-10-29, run KzQzfHUahiQH5VpMt: limit $0.03, match
    delivered, profile_found charged 0).
    """

    def __init__(self) -> None:
        self.cm = Actor.get_charging_manager()
        info = self.cm.get_pricing_info()
        self.ppe = info.is_pay_per_event
        self.limit = info.max_total_charge_usd
        self.prices = info.per_event_prices

    def cost(self, *events: str):
        return sum(self.prices.get(event, 0) for event in events)

    def can_pay(self, *events: str) -> bool:
        return not self.ppe or self.limit - self.cm.calculate_total_charged_amount() >= self.cost(*events)


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

        budget = _Budget()
        if not budget.can_pay("actor_start", "email_processed", "profile_found"):
            msg = (f"Nothing was looked up and nothing was charged: this run's spending limit of "
                   f"{_usd(budget.limit)} cannot pay for one email "
                   f"({_usd(budget.cost('actor_start', 'email_processed', 'profile_found'))} with the run start "
                   "and a confident match). Raise the run's maximum cost in the run options, or add credit, "
                   "then run it again.")
            Actor.log.warning(msg)
            await _set_status(msg)
            return

        await _charge("actor_start")
        Actor.log.info(f"flow={inp.get('aiMode', 'balanced')} gate={gate} "
                       f"deep_enrich={deep} emails={len(emails)}")

        found = confident = failed = checked = 0
        stopped = False
        for email in emails:
            if not budget.can_pay("email_processed", "profile_found"):
                stopped = True
                break
            checked += 1
            await _charge("email_processed")
            try:
                result = find_linkedin(email, mode=mode, do_enrich=deep, flow=flow)
            except Exception as exc:  # noqa: BLE001 - one bad address must not kill the batch
                Actor.log.warning(f"{email} -> lookup failed: {exc}")
                failed += 1
                result = {"email": email, "found": False, "linkedin_url": None,
                          "confidence": 0.0, "passes_gate": False, "error": str(exc)}
            if result.get("found"):
                found += 1
            if result.get("passes_gate"):
                # Charged after the row is saved; the limit check above keeps room for it.
                await Actor.push_data(result, charged_event_name="profile_found")
                confident += 1
            else:
                await Actor.push_data(result)
            Actor.log.info(
                f"{email} -> {result.get('linkedin_url')} "
                f"(conf {result.get('confidence')}, {result.get('source')})"
            )

        # Say plainly what happened so an empty or weak result never looks like a broken run.
        total = checked
        if found == 0:
            msg = (f"Checked {total} email(s); no LinkedIn profile found. Work emails "
                   f"(first.last@company.com) resolve best; add a Brave Search key for wider coverage.")
        else:
            msg = (f"Checked {total} email(s): {found} profile(s) found, "
                   f"{confident} above the {int(gate * 100)}% confidence gate.")
        if failed:
            msg += f" {failed} lookup(s) errored and were returned with found=false."
        if stopped:
            msg += (f" Stopped early after {checked} of {len(emails)} email(s): this run's spending limit of "
                    f"{_usd(budget.limit)} was reached. Raise the run's maximum cost to check the rest.")
        await _set_status(msg)
        Actor.log.info(msg)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
