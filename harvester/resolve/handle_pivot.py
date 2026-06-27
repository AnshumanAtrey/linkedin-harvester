"""Resolver step 0.5 (free, no search): pivot a confirmed handle to LinkedIn.

The ENRICH bag often hands us a username that resolves on several platforms
(github + youtube + telegram + ...). A handle that consistent is a strong
predictor of the LinkedIn slug: linkedin.com/in/<handle>. We can't verify the
guess (LinkedIn login-walls the page), so confidence scales with how many
platforms confirmed the handle -- the scorer then corroborates it against the
name-dork. Cross-platform consistency is the signal, not a single 200.
"""
from harvester.models import Person, Candidate
from harvester.resolve.base import Resolver


class HandlePivotResolver(Resolver):
    name = "handle_pivot"
    cost_per_hit = 0.0

    def find(self, person: Person) -> list[Candidate]:
        bag = person.enrichment or {}
        out = []

        # A scanner already surfaced a LinkedIn /in/ URL tied to this email
        # (e.g. a verified Gravatar linked account) -> near-certain.
        for url in bag.get("linkedin_urls") or []:
            out.append(Candidate(
                url, "enrichment_linkedin",
                "LinkedIn linked directly from an enrichment source (Gravatar/site)",
                prior=0.9,
            ))

        confirmations = bag.get("handle_confirmations") or {}
        for handle in (bag.get("handles") or [])[:3]:
            n = confirmations.get(handle, 1)
            # prior scales with cross-platform confirmation but stays just under
            # the scrape gate: a slug guess must be corroborated by the name dork
            # before we greenlight a paid scrape (verify before spending).
            prior = 0.78 if n >= 3 else 0.66 if n == 2 else 0.5
            out.append(Candidate(
                f"https://www.linkedin.com/in/{handle}",
                "handle_pivot",
                f"handle '{handle}' confirmed on {n} platform(s) -> likely LinkedIn slug",
                context=" ".join(bag.get("confirmed_socials") or []),
                prior=prior,
            ))
        return out
