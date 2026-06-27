"""Email -> GitHub account. Free, no token.

Two paths:
  1. noreply form  ID+username@users.noreply.github.com  ->  /user/{ID} (60/hr, reliable)
     Devs who enable email privacy commit under exactly this address, so a single
     commit leak hands you the user id and login. The id is authoritative.
  2. best-effort commit search (author-email:) -> login. Unauthenticated search is
     tightly rate-limited, so this is a bonus, not relied upon; it degrades silently.
"""
from __future__ import annotations

import re

import httpx

from .base import Scanner

UA = {"User-Agent": "boss-osint", "Accept": "application/vnd.github+json"}
NOREPLY = re.compile(r"^(?:(\d+)\+)?([a-zA-Z0-9-]+)@users\.noreply\.github\.com$")


async def _profile(c: httpx.AsyncClient, url: str) -> dict | None:
    try:
        r = await c.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:  # noqa: BLE001
        pass
    return None


def _shape(u: dict) -> dict:
    out: dict = {
        "found": True,
        "username": u.get("login"),
        "profile": u.get("html_url"),
        "user_id": u.get("id"),
        "avatar": u.get("avatar_url"),
    }
    for src, dst in (
        ("name", "name"), ("company", "company"), ("blog", "website"),
        ("location", "location"), ("bio", "bio"), ("twitter_username", "twitter"),
        ("public_repos", "public_repos"), ("followers", "followers"),
        ("created_at", "account_created"),
    ):
        if u.get(src):
            out[dst] = u[src]
    return out


async def _run(target: str) -> dict:
    email = target.strip().lower()

    async with httpx.AsyncClient(headers=UA, follow_redirects=True) as c:
        # Path 1 — noreply address decodes directly to the account (most reliable).
        m = NOREPLY.match(email)
        if m:
            uid, login = m.group(1), m.group(2)
            u = None
            if uid:
                u = await _profile(c, f"https://api.github.com/user/{uid}")
            if not u:
                u = await _profile(c, f"https://api.github.com/users/{login}")
            if u:
                out = _shape(u)
                out["match_via"] = "noreply address (authoritative)"
                return out
            # Even without the API, the username is in the address itself.
            return {
                "found": True,
                "username": login,
                "profile": f"https://github.com/{login}",
                "match_via": "noreply address (username parsed; profile unverified)",
            }

        # Path 2 — best-effort commit search. Swallows rate limits / misses.
        try:
            r = await c.get(
                "https://api.github.com/search/commits",
                params={"q": f"author-email:{email}", "per_page": 1},
                headers={**UA, "Accept": "application/vnd.github.cloak-preview+json"},
                timeout=10,
            )
            if r.status_code == 200:
                items = r.json().get("items") or []
                if items and items[0].get("author"):
                    a = items[0]["author"]
                    u = await _profile(c, a.get("url", ""))
                    out = _shape(u) if u else {
                        "found": True, "username": a.get("login"),
                        "profile": a.get("html_url"), "avatar": a.get("avatar_url"),
                    }
                    out["match_via"] = "public commit authored by this email"
                    return out
        except Exception:  # noqa: BLE001
            pass

    return {"found": False, "note": "no GitHub account tied to this email (or search rate-limited)"}


scanner = Scanner(name="email_github", title="GitHub Account", run_fn=_run)
