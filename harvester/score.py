"""Confidence scoring - how sure are we this is the right person?

Two layers, deterministic-first:
  1. A classical scorecard (Jaro-Winkler name match + nickname gazetteer + company
     corroboration + source authority + SERP-convergence prior). Free, instant,
     explainable. This alone resolves the clear cases.
  2. An OPTIONAL AI judge, escalated ONLY on the gray zone (a candidate that scored
     between "clear miss" and "clear hit") and ONLY for company-anchored matches the
     algos find genuinely ambiguous. Reserving the LLM for the tail is the resource
     win - we never pay an LLM to confirm what Jaro-Winkler already nailed.

AI judges; it never searches. The flow object decides whether AI is allowed.
"""
from harvester.models import Person, Candidate
from harvester import ai
from harvester.match import name_similarity

# Sources whose confidence is self-asserted or already calibrated by the resolver
# (convergence / pivot prior). The company-centric AI judge miscalibrates these
# (it penalises a missing company), so they never escalate to AI.
_SELF_ASSERTED = {"signature", "gravatar"}
_PRIOR_CALIBRATED = {"dork:nameonly", "handle_pivot", "enrichment_linkedin"}


def _scorecard(person: Person, cand: Candidate) -> float:
    """Deterministic confidence 0..1. The whole no-AI flow rides on this."""
    slug = cand.linkedin_url.rstrip("/").split("/in/")[-1]
    score = name_similarity(person.name, slug) * 0.72

    # company corroboration: anchor appears in the slug or the search snippet
    haystack = f"{slug} {cand.context}".lower()
    anchors = set()
    if person.company:
        anchors.add(person.company.lower().split(".")[0].split()[0])
    if person.domain:
        anchors.add(person.domain.split(".")[0])
    if any(len(a) > 2 and a in haystack for a in anchors):
        score += 0.25

    # source authority floors
    if cand.source == "signature":
        score = max(score, 0.97)          # came straight from them
    elif cand.source == "gravatar":
        score = max(score, 0.9)

    # resolver-supplied prior (SERP convergence, handle pivot, enrichment link)
    if cand.prior:
        score = max(score, cand.prior)

    if "mismatch" in cand.evidence.lower():
        score *= 0.4
    return round(min(score, 1.0), 2)


def _ai_judge(person: Person, cand: Candidate) -> float | None:
    got = ai.ask_json(
        "You are matching an email sender to a candidate LinkedIn profile. "
        "Return JSON {confidence: 0..1, reason: str}. Be skeptical; only score "
        "high when name AND company/title clearly align.\n\n"
        f"SENDER: name={person.name}, company={person.company}, "
        f"title={person.title}, email={person.email}\n"
        f"CANDIDATE URL: {cand.linkedin_url}\nEVIDENCE: {cand.evidence}\n"
        f"SNIPPET: {cand.context}"
    )
    if got and "confidence" in got:
        try:
            return round(min(max(float(got["confidence"]), 0.0), 1.0), 2)
        except (TypeError, ValueError):
            return None
    return None


def score(person: Person, cand: Candidate, flow=None) -> float:
    if flow is None:
        from harvester.flow import BALANCED
        flow = BALANCED

    base = _scorecard(person, cand)

    # Self-asserted and prior-calibrated sources: trust the deterministic score.
    if cand.source in _SELF_ASSERTED or cand.source in _PRIOR_CALIBRATED:
        return base

    # Company-anchored dork / website match: escalate to the AI judge only when
    # the flow allows it AND the score is in the gray zone (otherwise the LLM call
    # is wasted - it won't rescue a 0.3 or improve on a 0.95).
    if flow.ai_helps_score(base) and ai.available():
        ai_s = _ai_judge(person, cand)
        if ai_s is not None:
            return ai_s
    return base
