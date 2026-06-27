"""Validation layer — is a resolved URL actually THIS person's profile?

Runs after any resolver, before the scrape spend. Catches the edge cases:
- a /company/ or /school/ page mistaken for a person,
- a forwarded email carrying someone ELSE's LinkedIn,
- a wrong same-name match.
"""
import re

PERSONAL_RE = re.compile(r"linkedin\.com/in/[A-Za-z0-9\-_%]+", re.I)
COMPANY_RE = re.compile(r"linkedin\.com/(company|school|showcase|pub/dir)/", re.I)


def is_personal_profile(url: str) -> bool:
    return bool(url) and bool(PERSONAL_RE.search(url)) and not COMPANY_RE.search(url)


def is_company_page(url: str) -> bool:
    return bool(url) and bool(COMPANY_RE.search(url))


def name_matches(person_name: str, url: str, context: str = "") -> bool:
    """Does the sender's name show up in the profile slug (or search snippet)?
    Handles concatenated slugs ('satyanadella') and hyphenated ones alike."""
    slug = url.rstrip("/").split("/in/")[-1].lower()
    slug_flat = slug.replace("-", "")
    haystack = f"{slug} {context}".lower()
    tokens = [t for t in person_name.lower().split() if len(t) > 1]
    name_flat = "".join(tokens)
    if name_flat and len(name_flat) > 3 and name_flat in slug_flat:
        return True
    return bool(tokens) and all(t in haystack for t in tokens)


def validate(person, url: str, context: str = "") -> tuple[bool, str]:
    """Returns (ok, reason). Reject before we pay to scrape."""
    if not url:
        return False, "no url"
    if is_company_page(url):
        return False, "company/school page, not a person"
    if not is_personal_profile(url):
        return False, "not a /in/ personal profile"
    if not name_matches(person.name, url, context):
        return False, "profile name does not match sender"
    return True, "ok"
