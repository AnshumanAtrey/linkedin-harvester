"""The data that flows through the pipeline. One dataclass per stage's output."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Email:
    """One raw inbound message from one of the 25 inboxes."""
    inbox: str                       # which account received it
    from_name: str
    from_email: str
    subject: str
    body: str
    received_at: str                 # ISO date
    reply_to: str = ""               # "Name <email>" — the real person when From is an ESP
    true_linkedin: Optional[str] = None   # DEMO-ONLY ground truth (None in real data)


@dataclass
class Person:
    """A unique human, merged across every inbox that ever heard from them."""
    name: str
    email: str
    domain: str
    company: Optional[str] = None
    title: Optional[str] = None
    signature_linkedin: Optional[str] = None      # personal /in/ URL found in the mail
    company_linkedin: Optional[str] = None         # /company/ page — a signal, NOT the person
    emails: list = field(default_factory=list)    # all their Email objects
    inboxes: set = field(default_factory=set)      # which of the 25 saw them
    enrichment: dict = field(default_factory=dict)  # ENRICH signal bag (names, handles, socials)
    true_linkedin: Optional[str] = None            # DEMO-ONLY ground truth


@dataclass
class Candidate:
    """A possible LinkedIn URL proposed by one resolver, before scoring."""
    linkedin_url: str
    source: str                      # which resolver produced it
    evidence: str                    # why it thinks this is the person
    context: str = ""                # search snippet/title — where the company name shows up
    prior: float = 0.0               # resolver's own confidence hint (e.g. SERP handle convergence)


@dataclass
class Resolution:
    """The chosen match for a person, with a confidence the gate can act on."""
    person_email: str
    linkedin_url: Optional[str]
    confidence: float
    source: str
    evidence: str
    cost_usd: float = 0.0
    snippet: str = ""                # the SERP text we already fetched — free profile data


@dataclass
class Profile:
    """Structured LinkedIn profile returned by the scrape step."""
    linkedin_url: str
    headline: str = ""
    location: str = ""
    experience: list = field(default_factory=list)
    education: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class PersonaCard:
    """The final enriched output: who they are + why they reached out."""
    person_email: str
    name: str
    linkedin_url: Optional[str]
    confidence: float
    who_they_are: str
    why_they_emailed: str
    last_contacted: str
    inboxes: str                     # comma-joined list
