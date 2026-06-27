"""Run resolvers cheapest-first; stop the moment one clears the bar.

This is the cost optimiser: a free signature hit means we never pay a vendor.
In incremental mode the paid resolver is skipped entirely (backfill_only)."""
from harvester.models import Person, Resolution
from harvester.score import score
from harvester.resolve.gravatar import GravatarResolver
from harvester.resolve.signature import SignatureResolver
from harvester.resolve.handle_pivot import HandlePivotResolver
from harvester.resolve.dork import DorkResolver
from harvester.resolve.website import WebsiteResolver
from harvester.resolve.hosted import HostedResolver


def default_cascade() -> list:
    # cheapest -> priciest. handle_pivot + dork both read the ENRICH bag off
    # the Person; dork corroborates the pivot's guess with a real SERP.
    return [SignatureResolver(), GravatarResolver(), HandlePivotResolver(),
            DorkResolver(), WebsiteResolver(), HostedResolver()]


def resolve(person: Person, mode: str = "incremental", resolvers=None, flow=None) -> Resolution:
    if flow is None:
        from harvester.flow import BALANCED
        flow = BALANCED
    resolvers = resolvers or default_cascade()
    best = Resolution(person.email, None, 0.0, "none", "no candidate found")

    for r in resolvers:
        if r.backfill_only and mode != "backfill":
            continue                      # keep the daily run free
        for cand in r.find(person):
            conf = score(person, cand, flow)
            if conf > best.confidence:
                best = Resolution(person.email, cand.linkedin_url, conf,
                                  cand.source, cand.evidence, r.cost_per_hit,
                                  snippet=cand.context)
        if best.confidence >= flow.gate:
            break                         # good enough — stop, don't pay further
    return best
