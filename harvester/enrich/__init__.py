"""ENRICH: email -> everything we can deterministically gather, before any AI.

Runs the vendored boss-osint email scanners concurrently and normalises their
output into one signal bag. The philosophy: grab the maximum
deterministic signal -- real name, company, handles, linked socials -- and hand
the whole bag to the AI to reason over. We never *guess* the name when a scanner
already *knows* it (a public GitHub commit author, a Gravatar display name, a PGP
UID). The AI's job is judgement, not invention.

Scanners (all free, no key):
  email_github   public commit author -> real name, company, location, blog, twitter
  email_gravatar md5 profile          -> display name, location, linked LinkedIn/socials
  email_pgp      keyserver UID        -> "Real Name <email>"
  email_social   handle pivot         -> confirmed live profiles across platforms
"""
from __future__ import annotations

import re
import asyncio

from . import email_github, email_gravatar, email_pgp, email_social

# Fast, name-yielding scanners always run. email_social does many probes (~slow)
# so it is gated behind deep=True.
_FAST = {"email_github": email_github, "email_gravatar": email_gravatar, "email_pgp": email_pgp}
_DEEP = {"email_social": email_social}

_LINKEDIN_RE = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+", re.I)
_HANDLE_RE = re.compile(r"/@?([A-Za-z0-9._-]+)/?$")


async def _gather(email: str, deep: bool) -> dict:
    mods = {**_FAST, **(_DEEP if deep else {})}
    names = list(mods)
    results = await asyncio.gather(
        *(m._run(email) for m in mods.values()), return_exceptions=True
    )
    return {n: (r if isinstance(r, dict) else {"error": str(r)}) for n, r in zip(names, results)}


def enrich(email: str, deep: bool = True) -> dict:
    """Sync wrapper: run the scanners, return the normalised signal bag.

    Safe whether or not an event loop is already running (the Apify actor runs
    inside one): if a loop is live, the scan is offloaded to a worker thread with
    its own loop rather than nesting.
    """
    coro_args = (email.strip().lower(), deep)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return signal_bag(asyncio.run(_gather(*coro_args)))   # no loop -> simple

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        raw = ex.submit(lambda: asyncio.run(_gather(*coro_args))).result()
    return signal_bag(raw)


def _handle_from_url(url: str) -> str | None:
    m = _HANDLE_RE.search(url.rstrip("/"))
    return m.group(1).lower() if m else None


def signal_bag(raw: dict) -> dict:
    """Collapse raw scanner output into one structured bag the AI can reason over."""
    gh = raw.get("email_github") or {}
    gr = raw.get("email_gravatar") or {}
    pg = raw.get("email_pgp") or {}
    so = raw.get("email_social") or {}

    # --- names (ranked by source authority) ---
    names: list[dict] = []
    if gh.get("name"):
        names.append({"value": gh["name"], "source": "github_commit"})
    if gr.get("display_name"):
        names.append({"value": gr["display_name"], "source": "gravatar"})
    for uid in pg.get("identities", []):
        nm = uid.split("<")[0].strip()
        if nm and not nm.startswith("0x"):
            names.append({"value": nm, "source": "pgp"})

    # --- handles, counted across platforms (cross-platform consistency = signal) ---
    handle_count: dict[str, int] = {}
    if gh.get("username"):
        handle_count[gh["username"].lower()] = handle_count.get(gh["username"].lower(), 0) + 1
    if gr.get("username"):
        handle_count[gr["username"].lower()] = handle_count.get(gr["username"].lower(), 0) + 1
    for line in so.get("confirmed_profiles", []):
        url = line.split(": ", 1)[-1].split(" ")[0]
        h = _handle_from_url(url)
        if h:
            handle_count[h] = handle_count.get(h, 0) + 1
    handles = sorted(handle_count, key=lambda h: -handle_count[h])

    # --- LinkedIn URLs already surfaced by a scanner (Gravatar linked accounts, blog) ---
    linkedin_urls: list[str] = []
    blobs = list(gr.get("linked_accounts", [])) + [gh.get("website", ""), gr.get("profile_url", "")]
    for b in blobs:
        m = _LINKEDIN_RE.search(b or "")
        if m and m.group(0) not in linkedin_urls:
            linkedin_urls.append(m.group(0).rstrip("/"))

    return {
        "best_name": names[0]["value"] if names else None,
        "names": names,
        "company": gh.get("company"),
        "location": gh.get("location") or gr.get("location"),
        "title": gr.get("job_title"),
        "bio": gh.get("bio") or gr.get("about"),
        "twitter": gh.get("twitter"),
        "website": gh.get("website"),
        "handles": handles,                       # ranked by cross-platform confirmation
        "handle_confirmations": handle_count,     # handle -> #platforms it resolves on
        "linkedin_urls": linkedin_urls,           # direct hits (near-certain if present)
        "confirmed_socials": so.get("confirmed_profiles", []),
        "raw": raw,                               # full scanner output for the AI
    }
