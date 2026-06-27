"""The Resolver contract: a Person in, zero-or-more Candidate URLs out.

Every resolver — free or paid, local or hosted — implements this. That's what
makes the vendor a swappable socket instead of a hard-wired dependency
(the Proxycurl lesson: never single-source the spine)."""
from harvester.models import Person, Candidate


class Resolver:
    name = "base"
    cost_per_hit = 0.0          # USD, for the running cost tally
    backfill_only = False       # paid resolvers stay off the free incremental run

    def find(self, person: Person) -> list[Candidate]:
        raise NotImplementedError
