"""Gravatar profile lookup by email hash. Free, no API key.

Most emails have no Gravatar, but a hit is high-value: real name, location, job,
bio, and *verified* linked social accounts (twitter/linkedin/github/instagram).
"""
from __future__ import annotations

import hashlib

import httpx

from .base import Scanner

UA = {"User-Agent": "Mozilla/5.0 (boss-osint)"}


async def _run(target: str) -> dict:
    email = target.strip().lower()
    md5 = hashlib.md5(email.encode()).hexdigest()
    out: dict = {"has_gravatar": False, "hash_md5": md5}

    async with httpx.AsyncClient(timeout=12, headers=UA, follow_redirects=True) as c:
        # 1) Public profile JSON (richest source).
        try:
            r = await c.get(f"https://gravatar.com/{md5}.json")
            if r.status_code == 200:
                entry = (r.json().get("entry") or [{}])[0]
                out["has_gravatar"] = True
                for src, dst in (
                    ("profileUrl", "profile_url"),
                    ("displayName", "display_name"),
                    ("preferredUsername", "username"),
                    ("currentLocation", "location"),
                    ("job_title", "job_title"),
                    ("pronouns", "pronouns"),
                ):
                    if entry.get(src):
                        out[dst] = entry[src]
                if entry.get("aboutMe"):
                    out["about"] = entry["aboutMe"][:280]
                photos = entry.get("photos") or []
                if photos:
                    out["avatar"] = photos[0].get("value")

                linked = []
                for a in entry.get("accounts") or []:
                    name = a.get("shortname") or a.get("name") or "link"
                    verified = " (verified)" if a.get("verified") in (True, "true") else ""
                    linked.append(f"{name}: {a.get('url')}{verified}")
                if linked:
                    out["linked_accounts"] = linked
                return out
        except Exception:  # noqa: BLE001 - fall through to avatar-only check
            pass

        # 2) No public profile, but a custom avatar (d=404 -> 200 only if one exists).
        try:
            r = await c.get(f"https://gravatar.com/avatar/{md5}?d=404&s=200")
            if r.status_code == 200:
                out["has_gravatar"] = True
                out["avatar"] = f"https://gravatar.com/avatar/{md5}?s=200"
                out["note"] = "avatar exists, no public profile fields"
        except Exception:  # noqa: BLE001
            pass

    return out


scanner = Scanner(name="email_gravatar", title="Gravatar Profile", run_fn=_run)
