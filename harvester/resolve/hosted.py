"""Resolver step 3 (paid, BACKFILL ONLY): a hosted email->LinkedIn vendor.

Default adapter = Findymail (email -> LinkedIn URL, pay-on-success ~$0.0198/hit).
Swappable for Reverse Contact / Prospeo / Datagma — same Resolver contract.

Stubbed until FINDYMAIL_API_KEY is set, so it never spends during the demo and
never runs on the free incremental path (backfill_only = True)."""
import os
from harvester.models import Person, Candidate
from harvester.resolve.base import Resolver


class HostedResolver(Resolver):
    name = "hosted:findymail"
    cost_per_hit = 0.0198
    backfill_only = True

    def find(self, person: Person) -> list[Candidate]:
        key = os.environ.get("FINDYMAIL_API_KEY")
        if not key:
            return []                       # stubbed — no key, no spend
        import requests
        try:
            r = requests.post(
                "https://app.findymail.com/api/search/linkedin",
                headers={"Authorization": f"Bearer {key}"},
                json={"email": person.email}, timeout=10,
            )
            url = (r.json() or {}).get("contact", {}).get("linkedin_url")
        except Exception:
            return []
        if url:
            return [Candidate(url, self.name, "Findymail reverse-email match")]
        return []
