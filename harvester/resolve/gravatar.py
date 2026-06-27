"""Resolver step 0 (free): hash the email -> Gravatar -> verified social links.
Some people publish their LinkedIn on their Gravatar; that's a free, high-trust
hit. Pattern lifted from boss-osint's email_gravatar scanner.

Network-optional: if requests is missing or offline, it simply returns []."""
import hashlib
from harvester.models import Person, Candidate
from harvester.resolve.base import Resolver


class GravatarResolver(Resolver):
    name = "gravatar"
    cost_per_hit = 0.0

    def find(self, person: Person) -> list[Candidate]:
        try:
            import requests
        except ImportError:
            return []
        h = hashlib.sha256(person.email.strip().lower().encode()).hexdigest()
        try:
            r = requests.get(f"https://en.gravatar.com/{h}.json", timeout=4,
                             headers={"User-Agent": "linkedin-harvester"})
            if r.status_code != 200:
                return []
            data = r.json()["entry"][0]
        except Exception:
            return []
        for acc in data.get("accounts", []):
            url = acc.get("url", "")
            if "linkedin.com/in/" in url:
                return [Candidate(url, self.name, "verified LinkedIn on Gravatar")]
        return []
