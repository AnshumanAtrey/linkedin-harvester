"""Email -> Person. Regex + a small AI assist for messy signatures.

Basics first (the interview feedback): we drop role/automated mailboxes here,
BEFORE any spend. You pay per real person, never per email.
"""
import re
from typing import Optional
from harvester.models import Email, Person
from harvester import ai
from harvester.validate import PERSONAL_RE, COMPANY_RE
from config import (ROLE_LOCALPARTS, FREE_MAIL_DOMAINS, ESP_DOMAINS, NEWSLETTER_MARKERS)

ADDR_RE = re.compile(r"<([^>]+@[^>]+)>")          # the email inside "Name <email>"

LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+", re.I
)
COMPANY_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/company/[A-Za-z0-9\-_%]+", re.I
)
TITLE_HINTS = re.compile(
    r"\b(founder|co-?founder|ceo|cto|coo|cfo|cmo|president|partner|"
    r"director|head|vp|vice president|principal|manager|lead|analyst)\b", re.I
)


def _parse_addr(raw: str) -> tuple[str, str]:
    """'Manvendra from Hackculture <manvendra@hackculture.in>' -> (name, email)."""
    if not raw:
        return "", ""
    m = ADDR_RE.search(raw)
    if m:
        return raw[:m.start()].strip().strip('"'), m.group(1).strip().lower()
    if "@" in raw:
        return "", raw.strip().lower()
    return raw.strip().strip('"'), ""


def _clean_name(name: str) -> str:
    """'Manvendra from Hackculture' -> 'Manvendra'; drops via/at/from suffixes."""
    name = re.split(r"\s+(?:from|via|at|@)\s+", name or "", maxsplit=1, flags=re.I)[0]
    return name.strip().strip('"').strip()


def _is_esp(domain: str) -> bool:
    return any(domain == e or domain.endswith("." + e) for e in ESP_DOMAINS)


def _is_role(local: str) -> bool:
    base = re.split(r"[._+\-]", local)[0]
    return local in ROLE_LOCALPARTS or base in ROLE_LOCALPARTS


def _looks_bulk(body: str) -> bool:
    b = (body or "").lower()
    return any(m in b for m in NEWSLETTER_MARKERS)


def effective_sender(email: Email) -> tuple[str, str, Optional[str]]:
    """Who is the REAL person behind this email? Returns (name, email, drop_reason).

    - ESP (beehiiv/mailchimp/...) -> the real person+company is in Reply-To.
    - role address (no-reply@, support@) -> drop.
    - bulk body + role contact -> newsletter, drop. (A real person in From/Reply-To
      rescues it: that's outreach, i.e. a lead worth enriching.)
    """
    from_dom = email.from_email.split("@")[1].lower()
    name, addr = email.from_name, email.from_email.lower()

    if _is_esp(from_dom) and email.reply_to:
        rt_name, rt_addr = _parse_addr(email.reply_to)
        if rt_addr:
            name, addr = (rt_name or name), rt_addr

    name = _clean_name(name)
    local = addr.split("@")[0]

    if _is_role(local) or email.from_name.strip().lower() in {"no-reply", "noreply", "team"}:
        return name, addr, "role/automated address"

    rt_local = _parse_addr(email.reply_to)[1].split("@")[0] if "@" in (email.reply_to or "") else ""
    if _looks_bulk(email.body) and (_is_role(rt_local) or (_is_esp(from_dom) and not email.reply_to)):
        return name, addr, "bulk newsletter"

    return name, addr, None


def is_person(email: Email) -> bool:
    """False for no-reply@, info@, newsletters — never a human to enrich."""
    return effective_sender(email)[2] is None


def _company_from_domain(domain: str) -> Optional[str]:
    if domain in FREE_MAIL_DOMAINS:
        return None                       # gmail tells us nothing about company
    name = domain.split(".")[0]
    return name.replace("-", " ").title()


def _title_from_signature(body: str) -> Optional[str]:
    for line in body.splitlines():
        line = line.strip()
        if 0 < len(line) < 80 and TITLE_HINTS.search(line):
            return line.strip(" |,-")
    return None


def _norm_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if not url.startswith("http"):
        url = "https://" + url
    return url.replace("http://", "https://")


def _personal_linkedin(body: str) -> Optional[str]:
    m = LINKEDIN_RE.search(body)
    return _norm_url(m.group(0)) if m else None


def _company_linkedin(body: str) -> Optional[str]:
    m = COMPANY_URL_RE.search(body)
    return _norm_url(m.group(0)) if m else None


def extract(email: Email) -> Optional[Person]:
    """Pull a structured Person from one email. Returns None for non-people."""
    name, addr, drop = effective_sender(email)
    if drop:
        return None

    domain = addr.split("@")[1].lower()        # real domain (reply-to wins over ESP from)
    company = _company_from_domain(domain)
    title = _title_from_signature(email.body)
    personal_li = _personal_linkedin(email.body)
    company_li = _company_linkedin(email.body)

    # AI assist (optional, conditional): when the domain gives no company (gmail/
    # free-mail) or the signature is messy, mine the BODY for company/title. This
    # is what lets a "rahul@gmail.com — I'm founder of NeuralPay" email resolve.
    if ai.available() and (not company or not title):
        got = ai.ask_json(
            "Extract the SENDER's details from this email (signature + body) as JSON "
            "with keys name, company, title (use null if truly absent). Infer company "
            "from phrases like 'founder of X' or 'we at X'. Do not invent.\n\n"
            f"FROM: {email.from_name} <{email.from_email}>\n\n{email.body[:1800]}"
        )
        if got:
            name = got.get("name") or name
            company = company or got.get("company")
            title = title or got.get("title")

    return Person(
        name=name,
        email=addr,
        domain=domain,
        company=company,
        title=title,
        signature_linkedin=personal_li,
        company_linkedin=company_li,
        emails=[email],
        inboxes={email.inbox},
        true_linkedin=email.true_linkedin,
    )
