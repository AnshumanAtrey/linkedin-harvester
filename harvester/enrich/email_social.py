"""Email -> social media PROFILE URLs (not just exists/not). Free, no key.

holehe/ignorant answer "does an account exist"; this returns the actual links.
Platforms deliberately block reverse-email lookup, so there are two honest bridges:

  1. Username pivot: email local-part -> candidate handles -> probe each platform's
     profile URL for a live account -> return the resolving URLs (Sherlock/WhatsMyName
     approach). Only platforms with a clean exists/not signal are probed; SPA/CF sites
     that 200 on everything are NOT probed (false positives are worse than misses).
  2. Keybase: one username lookup returns a person's CRYPTOGRAPHICALLY-PROVEN Twitter,
     GitHub, Reddit, HackerNews and website URLs at once.

For login-walled high-value sites (X, Instagram, TikTok, Reddit, Facebook) a verified
probe is impossible unauthenticated, so the URL is CONSTRUCTED and flagged "unverified".
X/Twitter also gets an existence signal from its email_available endpoint (no handle).

Honesty: a resolving URL means that handle is live, not that it belongs to the email
owner. Treat probe hits as strong leads to verify, not proof.
"""
from __future__ import annotations

import asyncio

import httpx

from .base import Scanner

UA = {"User-Agent": "Mozilla/5.0 (boss-osint OSINT)"}
TIMEOUT = 10  # per-probe; generous so transient loop pressure on slow hosts doesn't drop hits

# Generic local-parts that would match thousands of unrelated profiles -> don't pivot.
_GENERIC = {
    "info", "admin", "contact", "support", "hello", "hi", "hey", "team", "mail",
    "email", "noreply", "no-reply", "sales", "office", "help", "service", "billing",
    "account", "accounts", "marketing", "press", "media", "careers", "jobs", "hr",
    "ceo", "founder", "me", "user", "test", "demo", "root", "webmaster",
}

# Probe-verified platforms: status==200 (no redirect-follow) means a live profile.
# (name, check_url, profile_url) — {u} is the candidate username.
_STATUS_PROBES = [
    ("GitHub", "https://api.github.com/users/{u}", "https://github.com/{u}"),
    ("GitLab", "https://gitlab.com/{u}", "https://gitlab.com/{u}"),
    ("dev.to", "https://dev.to/api/users/by_username?url={u}", "https://dev.to/{u}"),
    ("npm", "https://registry.npmjs.org/-/user/org.couchdb.user:{u}", "https://www.npmjs.com/~{u}"),
    ("Gravatar", "https://gravatar.com/{u}.json", "https://gravatar.com/{u}"),
    ("Linktree", "https://linktr.ee/{u}", "https://linktr.ee/{u}"),
    ("About.me", "https://about.me/{u}", "https://about.me/{u}"),
    ("YouTube", "https://www.youtube.com/@{u}", "https://www.youtube.com/@{u}"),
]

# Login-walled / SPA sites: can't verify unauthenticated -> construct + flag unverified.
_CONSTRUCT = [
    ("X / Twitter", "https://x.com/{u}"),
    ("Instagram", "https://instagram.com/{u}"),
    ("TikTok", "https://www.tiktok.com/@{u}"),
    ("Reddit", "https://www.reddit.com/user/{u}"),
    ("Facebook", "https://www.facebook.com/{u}"),
]


def _usernames(local: str) -> list[str]:
    base = local.split("+")[0]
    cands: list[str] = []
    for u in (local, base, base.replace(".", ""), base.replace(".", "_"), base.replace(".", "-")):
        u = u.strip().lower()
        if u and u not in cands and len(u) >= 4 and base not in _GENERIC:
            cands.append(u)
    return cands


async def _status_hit(c: httpx.AsyncClient, name: str, check: str, profile: str, u: str) -> str | None:
    try:
        r = await c.get(check.format(u=u), timeout=TIMEOUT)
        if r.status_code == 200:
            return f"{name}: {profile.format(u=u)}"
    except Exception:  # noqa: BLE001
        pass
    return None


async def _telegram_hit(c: httpx.AsyncClient, u: str) -> str | None:
    try:
        r = await c.get(f"https://t.me/{u}", timeout=TIMEOUT)
        if r.status_code == 200 and "tgme_page_title" in r.text:
            return f"Telegram: https://t.me/{u}"
    except Exception:  # noqa: BLE001
        pass
    return None


async def _keybase(c: httpx.AsyncClient, u: str) -> list[str]:
    try:
        r = await c.get(
            "https://keybase.io/_/api/1.0/user/lookup.json",
            params={"usernames": u, "fields": "proofs_summary"}, timeout=TIMEOUT,
        )
        them = r.json().get("them") or []
        out: list[str] = []
        for t in them:
            for p in (t.get("proofs_summary") or {}).get("all") or []:
                url = p.get("service_url") or p.get("proof_url")
                if url:
                    out.append(f"{p.get('proof_type', 'link')} (Keybase-proven): {url}")
        return out
    except Exception:  # noqa: BLE001
        return []


async def _twitter_exists(c: httpx.AsyncClient, email: str) -> bool:
    try:
        r = await c.get(
            "https://api.twitter.com/i/users/email_available.json",
            params={"email": email}, timeout=TIMEOUT,
        )
        return bool(r.json().get("taken"))
    except Exception:  # noqa: BLE001
        return False


async def _run(target: str) -> dict:
    email = target.strip().lower()
    local = email.split("@")[0]
    cands = _usernames(local)

    out: dict = {}
    confirmed: list[str] = []

    async with httpx.AsyncClient(headers=UA, follow_redirects=False) as c:
        # X/Twitter existence works off the email directly (no handle, but a real signal).
        if await _twitter_exists(c, email):
            out["existence_signal"] = "X/Twitter: an account is registered to this email (handle not exposed by X)"

        if not cands:
            out["note"] = "local-part is generic or too short to pivot into usernames"
            return out

        out["checked_usernames"] = cands

        tasks = []
        for u in cands:
            for name, check, profile in _STATUS_PROBES:
                tasks.append(_status_hit(c, name, check, profile, u))
            tasks.append(_telegram_hit(c, u))
            tasks.append(_keybase(c, u))
        results = await asyncio.gather(*tasks)

    for r in results:
        if isinstance(r, list):
            confirmed.extend(r)
        elif r:
            confirmed.append(r)

    # Dedupe, keep order.
    seen: set[str] = set()
    confirmed = [x for x in confirmed if not (x in seen or seen.add(x))]
    if confirmed:
        out["confirmed_profiles"] = confirmed

    # Constructed URLs for the sites we can't verify, from the primary candidate.
    primary = cands[0]
    out["candidate_profiles_unverified"] = [
        f"{name}: {tmpl.format(u=primary)}" for name, tmpl in _CONSTRUCT
    ]
    out["note"] = (
        "Confirmed = handle resolves to a live profile (verify it's the same person). "
        "Unverified = login-walled, constructed from the email's username."
    )
    return out


scanner = Scanner(name="email_social", title="Social Profiles (URLs)", run_fn=_run)
