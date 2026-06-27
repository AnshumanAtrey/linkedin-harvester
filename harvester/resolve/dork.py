"""Resolver step 2 (near-free): dork a search engine for the profile.

Query shape:  site:linkedin.com/in "Name" "Company"
- With BRAVE_API_KEY -> real Brave search (clean /in/ URLs, verified working).
- With GOOGLE_CSE_KEY+CX -> Google Custom Search (needs the API enabled in GCP).
- Without a key -> a simulated SERP so `python run.py` works offline.

Cost discipline: a search needs a COMPANY anchor to disambiguate a name, so
free-mail/no-company senders are parked here and never burn a query — the same
~50-70% corporate vs ~10-25% free-mail split the research found.

The resolver only proposes candidates. It never decides — score.py does.
"""
import os
import re
import json
import time
from collections import Counter
from pathlib import Path
from harvester.models import Person, Candidate
from harvester.resolve.base import Resolver
from config import FREE_MAIL_DOMAINS

_HANDLE_RE = re.compile(r"linkedin\.com/(in|posts)/([A-Za-z0-9\-_%]+)", re.I)
_LAST_BRAVE = [0.0]


def _throttle_brave(min_gap: float = 1.1) -> None:
    """Brave's free tier allows ~1 request/second. A single email can fire two
    Brave calls (company dork, then name-only fallback); without spacing the 2nd
    silently 429s and the match is lost. This keeps calls >= min_gap apart."""
    gap = time.monotonic() - _LAST_BRAVE[0]
    if 0 < gap < min_gap:
        time.sleep(min_gap - gap)
    _LAST_BRAVE[0] = time.monotonic()


def _alnum(s: str) -> str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def _handle(url: str) -> str | None:
    """The LinkedIn handle from a /in/ or /posts/ URL.
    /posts/<handle>_<activity-id...> collapses to <handle> so a person's posts
    corroborate their profile instead of looking like distinct results."""
    m = _HANDLE_RE.search(url)
    if not m:
        return None
    slug = m.group(2).lower().rstrip("/")
    if m.group(1).lower() == "posts":
        slug = slug.split("_", 1)[0]
    return slug


class DorkResolver(Resolver):
    name = "dork"
    cost_per_hit = 0.0          # free on Brave/CSE free tier; SearXNG for backfill burst

    def __init__(self, dummy_path: str = "data/dummy_emails.json"):
        self._index = None
        self._dummy_path = dummy_path

    def find(self, person: Person) -> list[Candidate]:
        if not person.name:
            return []                       # no name -> nothing to search
        if person.company:
            # company anchor present -> precise dork (highest precision)
            query = f'site:linkedin.com/in "{person.name}" "{person.company}"'
            if os.environ.get("BRAVE_API_KEY"):
                cands = self._brave(query, person)
            elif os.environ.get("GOOGLE_CSE_KEY") and os.environ.get("GOOGLE_CSE_CX"):
                cands = self._cse(query, person)
            else:
                return self._mock(person)
            if cands:
                return cands
            # company query whiffed (LinkedIn rarely echoes the company) -> fall
            # back to name-only convergence so we still get recall.
        # no/aborted company anchor: name-only convergence dork.
        # Distinctive names resolve; common names stay ambiguous and park.
        return self._nameonly(person)

    # --- real search backends -------------------------------------------------
    def _brave(self, query: str, person: Person) -> list[Candidate]:
        import requests
        _throttle_brave()
        try:
            r = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 5},
                headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"],
                         "Accept": "application/json"},
                timeout=8,
            )
            if r.status_code != 200:
                return []
            results = r.json().get("web", {}).get("results", [])
        except Exception:
            return []
        cands = []
        for res in results:
            url = res.get("url", "")
            if "linkedin.com/in/" in url:
                # title + description + extra_snippets = the public profile preview
                # LinkedIn serves Googlebot. We keep all of it so the snippet itself
                # can stand in for a scrape (SnippetScraper) at zero cost.
                extra = " · ".join(res.get("extra_snippets") or [])
                snippet = " · ".join(p for p in (res.get("title", ""),
                                                 res.get("description", ""), extra) if p)
                cands.append(Candidate(url, "dork:brave",
                             f"Brave result for {person.name} @ {person.company}",
                             context=snippet))
        return cands[:3]

    def _cse(self, query: str, person: Person) -> list[Candidate]:
        import requests
        try:
            r = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": os.environ["GOOGLE_CSE_KEY"],
                        "cx": os.environ["GOOGLE_CSE_CX"], "q": query, "num": 5},
                timeout=8,
            )
            if r.status_code != 200:
                return []
            items = r.json().get("items", [])
        except Exception:
            return []
        return [Candidate(it["link"], "dork:cse", f"CSE result for {person.name}",
                          context=f"{it.get('title', '')} {it.get('snippet', '')}")
                for it in items if "linkedin.com/in/" in it.get("link", "")][:3]

    # --- name-only convergence (free-mail / no company anchor) ----------------
    def _search_results(self, query: str, n: int = 10) -> list[tuple]:
        """Raw (url, title, snippet) from whichever real engine has a key."""
        import requests
        try:
            if os.environ.get("BRAVE_API_KEY"):
                _throttle_brave()
                r = requests.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": n},
                    headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"],
                             "Accept": "application/json"}, timeout=10)
                if r.status_code != 200:
                    return []
                return [(x.get("url", ""), x.get("title", ""),
                         " · ".join(p for p in [x.get("description", ""),
                                    *(x.get("extra_snippets") or [])] if p))
                        for x in r.json().get("web", {}).get("results", [])]
            if os.environ.get("GOOGLE_CSE_KEY") and os.environ.get("GOOGLE_CSE_CX"):
                r = requests.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={"key": os.environ["GOOGLE_CSE_KEY"],
                            "cx": os.environ["GOOGLE_CSE_CX"], "q": query, "num": n}, timeout=10)
                if r.status_code != 200:
                    return []
                return [(it.get("link", ""), it.get("title", ""), it.get("snippet", ""))
                        for it in r.json().get("items", [])]
        except Exception:
            return []
        return []                            # no real key -> name-only needs live search

    def _nameonly(self, person: Person) -> list[Candidate]:
        """No company to anchor on. Search the bare name, then measure whether a
        single LinkedIn handle (whose slug == the de-spaced name) dominates the
        results. Dominance = confidence; a scattered SERP = an ambiguous name."""
        results = self._search_results(f'"{person.name}" linkedin', n=10)
        if not results:
            return []
        flat = _alnum(person.name)
        handles, snippet_of = [], {}
        for url, title, desc in results:
            h = _handle(url)
            if not h:
                continue
            handles.append(h)
            snippet_of.setdefault(h, f"{title} {desc}".strip())
        if not handles:
            return []
        counts = Counter(handles)
        canonical = next((h for h in handles if _alnum(h) == flat), None)
        canonical_hits = counts.get(canonical, 0) if canonical else 0
        rank1_is_canonical = _alnum(handles[0]) == flat
        chosen = canonical or handles[0]

        # Corroboration: does an independent ENRICH signal back this slug? A
        # confirmed cross-platform handle that matches, or the company showing up
        # in the result snippet. Without it, a convergent SERP only proves we
        # found the most prominent namesake - not necessarily THIS person - so it
        # stays under the scrape gate.
        bag = person.enrichment or {}
        bag_handles = {_alnum(h) for h in (bag.get("handles") or [])}
        snippet = snippet_of.get(chosen, "").lower()
        company_anchor = (person.company or "").lower().split(".")[0].split()[0] if person.company else ""
        corroborated = (_alnum(chosen) in bag_handles
                        or (len(company_anchor) > 2 and company_anchor in snippet))

        if canonical and (rank1_is_canonical or canonical_hits >= 2):
            prior = 0.85 if corroborated else 0.75   # owns SERP; needs a 2nd signal to scrape
        elif canonical:
            prior = 0.70                     # present but not dominant -> parks at 0.80 gate
        else:
            prior = 0.45                     # no exact-name handle -> ambiguous, parks
        ev = (f"name-only SERP: handle '{chosen}' x{counts[chosen]}, "
              f"canonical_hits={canonical_hits}, rank1_canonical={rank1_is_canonical}, "
              f"corroborated={corroborated}")
        return [Candidate(f"https://www.linkedin.com/in/{chosen}", "dork:nameonly",
                          ev, context=snippet_of.get(chosen, ""), prior=prior)]

    # --- offline simulation ---------------------------------------------------
    def _mock(self, person: Person) -> list[Candidate]:
        if self._index is None:
            self._index = self._build_index()
        out = []
        for prof in self._index:
            if _name_overlap(person.name, prof["name"]) and (
                _name_overlap(person.company, prof["company"]) or person.company in prof["company"]
            ):
                out.append(Candidate(prof["url"], "dork:mock",
                                     f'matched "{prof["name"]}" at "{prof["company"]}"',
                                     context=f'{prof["name"]} {prof["company"]}'))
        return out[:3]

    def _build_index(self) -> list[dict]:
        try:
            rows = json.loads(Path(self._dummy_path).read_text())
        except (FileNotFoundError, ValueError):
            return []                       # no offline fixture -> no mock results
        index, seen = [], set()
        for r in rows:
            url = r.get("true_linkedin")
            if not url or url in seen:
                continue
            dom = r["from_email"].split("@")[1]
            company = r.get("company")          # explicit ground-truth company if given
            if not company and dom not in FREE_MAIL_DOMAINS:
                company = dom.split(".")[0].replace("-", " ").title()
            if company:                          # gmail w/o a body-company clue won't be findable
                index.append({"name": r["from_name"], "company": company, "url": url})
                seen.add(url)
        index.append({"name": "Aditya Rao", "company": "Tcs",
                      "url": "https://www.linkedin.com/in/aditya-rao-tcs-9281"})
        return index


def _name_overlap(a: str, b: str) -> bool:
    ta, tb = set((a or "").lower().split()), set((b or "").lower().split())
    return len(ta & tb) >= 2 or (bool(ta) and ta <= tb) or (bool(tb) and tb <= ta)
