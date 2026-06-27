"""Resolver step 1 (free): the email signature often already contains the URL.
The cheapest possible hit — no search, no spend, near-certain."""
from harvester.models import Person, Candidate
from harvester.resolve.base import Resolver


class SignatureResolver(Resolver):
    name = "signature"
    cost_per_hit = 0.0

    def find(self, person: Person) -> list[Candidate]:
        if person.signature_linkedin:
            return [Candidate(
                linkedin_url=person.signature_linkedin,
                source=self.name,
                evidence="LinkedIn URL was in the email signature",
            )]
        return []
