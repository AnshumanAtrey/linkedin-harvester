"""Flow selection: which pieces of the pipeline are allowed to call the LLM.

The pipeline is always extract -> retrieve -> rank. The ONLY thing a flow changes
is whether AI is permitted at the extract step and the rank step - and even when
permitted, AI runs as an *escalation* on the ambiguous tail, never blanket-called
(that is the resource win: good algos do the clear cases for free).

Two user-facing checkboxes map straight to these fields:
    [ ] AI extraction   -> ai_extract
    [ ] AI scoring       -> ai_score
Both unchecked = the pure deterministic (regex) flow.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import CONFIDENCE_THRESHOLD


@dataclass(frozen=True)
class Flow:
    ai_extract: bool = True      # LLM may parse messy signatures / hard local-parts
    ai_score: bool = True        # LLM may re-judge candidates
    escalate_only: bool = True   # ...but only in the gray zone, not on clear cases
    gate: float = CONFIDENCE_THRESHOLD   # >= this = confident (scrape)
    gray_low: float = 0.45               # below this = clear miss; [low, gate) = gray zone

    def ai_helps_score(self, deterministic_score: float) -> bool:
        """Should we spend an LLM call to re-judge this candidate?"""
        if not self.ai_score:
            return False
        if not self.escalate_only:
            return True
        return self.gray_low <= deterministic_score < self.gate


# Presets (the checkbox combinations).
REGEX = Flow(ai_extract=False, ai_score=False)                       # no AI at all
BALANCED = Flow(ai_extract=True, ai_score=True, escalate_only=True)   # AI on the tail only
FULL = Flow(ai_extract=True, ai_score=True, escalate_only=False)      # AI everywhere it's allowed

PRESETS = {"regex": REGEX, "balanced": BALANCED, "full": FULL}


def from_flags(ai_extract: bool, ai_score: bool, escalate_only: bool = True) -> Flow:
    return Flow(ai_extract=ai_extract, ai_score=ai_score, escalate_only=escalate_only)
