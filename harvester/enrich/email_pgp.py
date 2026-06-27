"""Published PGP key lookup via keys.openpgp.org. Free, no key.

Low hit-rate, but a match is high-signal: the target publishes a PGP key, and the
key's UIDs often tie the email to a real name and other addresses.
"""
from __future__ import annotations

import datetime
from urllib.parse import unquote

import httpx

from .base import Scanner

UA = {"User-Agent": "Mozilla/5.0 (boss-osint)"}
INDEX = "https://keys.openpgp.org/pks/lookup"


async def _run(target: str) -> dict:
    email = target.strip().lower()
    out: dict = {"has_pgp_key": False, "keyserver": "keys.openpgp.org"}

    async with httpx.AsyncClient(timeout=12, headers=UA) as c:
        try:
            r = await c.get(INDEX, params={"op": "index", "options": "mr", "search": email})
            text = r.text if r.status_code == 200 else ""
        except Exception:  # noqa: BLE001
            text = ""

    fingerprints: list[str] = []
    uids: list[str] = []
    created: str | None = None
    for line in text.splitlines():
        if line.startswith("pub:"):
            parts = line.split(":")
            if len(parts) > 1 and parts[1]:
                fingerprints.append(parts[1])
            if len(parts) > 4 and parts[4] and not created:
                created = parts[4]
        elif line.startswith("uid:"):
            parts = line.split(":")
            if len(parts) > 1 and parts[1]:
                uids.append(unquote(parts[1]))

    if fingerprints:
        out["has_pgp_key"] = True
        out["fingerprint"] = fingerprints[0]
        if len(fingerprints) > 1:
            out["all_fingerprints"] = fingerprints
        if uids:
            out["identities"] = uids
        if created and created.isdigit():
            out["key_created"] = datetime.datetime.utcfromtimestamp(int(created)).date().isoformat()
        out["key_url"] = f"https://keys.openpgp.org/vks/v1/by-email/{email}"

    return out


scanner = Scanner(name="email_pgp", title="PGP Key (keys.openpgp.org)", run_fn=_run)
