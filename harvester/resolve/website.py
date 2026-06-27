"""Resolver step 5 (near-free): the domain's own website often links the team's
LinkedIn right on it. Fetch the homepage + a few common pages, pull every
/in/ and /company/ link, return the /in/ ones as candidates.

Correct use of Firecrawl: scrape the WEBSITE, never LinkedIn (Firecrawl blocks
linkedin.com). Plain requests handles static sites for free; Firecrawl is the
optional upgrade for JS-heavy ones (set FIRECRAWL_API_KEY).

Only fires for custom domains — gmail/free-mail have no company website to read.
"""
import os
import re
from harvester.models import Person, Candidate
from harvester.resolve.base import Resolver
from harvester.validate import PERSONAL_RE
from config import FREE_MAIL_DOMAINS

PATHS = ["", "/about", "/team", "/about-us", "/company", "/people"]


class WebsiteResolver(Resolver):
    name = "website"
    cost_per_hit = 0.0          # plain fetch is free; Firecrawl ~$0.001/page if used

    def find(self, person: Person) -> list[Candidate]:
        if person.domain in FREE_MAIL_DOMAINS:
            return []                       # no company site to read
        urls = self._collect_linkedin_urls(person.domain)
        out = []
        for u in urls:
            if "linkedin.com/in/" in u.lower():
                out.append(Candidate(u, "website",
                           f"linked on {person.domain}", context=f"{person.company} {person.domain}"))
        return out[:3]

    def _collect_linkedin_urls(self, domain: str) -> list[str]:
        html = self._fetch(f"https://{domain}")
        found = set(PERSONAL_RE.findall(html)) if html else set()
        # one extra hop into a likely team/about page if the homepage was thin
        if len(found) < 1:
            for p in PATHS[1:3]:
                more = self._fetch(f"https://{domain}{p}")
                if more:
                    found |= set(PERSONAL_RE.findall(more))
                if found:
                    break
        return [u if u.startswith("http") else "https://" + u for u in found]

    def _fetch(self, url: str) -> str:
        # Firecrawl for JS sites, if configured
        if os.environ.get("FIRECRAWL_API_KEY"):
            try:
                import requests
                r = requests.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    headers={"Authorization": f"Bearer {os.environ['FIRECRAWL_API_KEY']}"},
                    json={"url": url, "formats": ["html"]}, timeout=20,
                )
                if r.ok:
                    return str(r.json().get("data", {}).get("html", ""))
            except Exception:
                pass
        # plain fetch (free) — good enough for static sites
        try:
            import requests
            r = requests.get(url, timeout=6,
                             headers={"User-Agent": "Mozilla/5.0 linkedin-harvester"})
            return r.text if r.status_code == 200 else ""
        except Exception:
            return ""
