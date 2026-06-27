# LinkedIn Profile Finder - Email to LinkedIn URL Lookup

Find someone's public LinkedIn profile from just their email address. No cookies, no LinkedIn login, no third-party data broker. Bring your own free search + AI keys.

Available as an [Apify Actor](https://apify.com/anshumanatrey/linkedin-harvester) and runnable locally as a CLI.

---

## What does it do?

You give it an email, it returns the most likely public LinkedIn URL plus a confidence score. It works the way every honest email-to-LinkedIn tool works under the hood: derive the person's name and company from the email, search the public web for their `linkedin.com/in` profile, then score how well the result matches. For people who have left other public traces (a GitHub commit, a Gravatar), it also pulls those to recover the real name.

It is the reverse of a profile scraper. Scrapers go LinkedIn URL to data; this goes email to LinkedIn URL.

## How does it work? (extract to retrieve to rank)

1. **Extract** - parse the name and company from the email. Optionally enrich from GitHub / Gravatar / social handles to recover a name the email itself does not contain.
2. **Retrieve** - search `site:linkedin.com/in "Name" "Company"` (Brave or Google CSE) for candidate profiles.
3. **Rank** - score each candidate with a classical name-matcher (Jaro-Winkler + nickname table + cross-source corroboration). The AI is optional and only steps in on genuinely ambiguous matches.

## Which AI flow should I pick?

One simple choice:

| Flow | What it does | Cost |
|---|---|---|
| **No AI** | Deterministic only. Fastest, free. Clear matches resolve, uncertain ones park. | $0 |
| **Balanced** (default) | AI steps in only when the deterministic score is uncertain. | tiny |
| **Full AI** | AI judges everything. Highest match rate. | higher |

Most work emails (`first.last@company.com`) resolve the same in all three, because the deterministic path already nails them.

## Run it locally (2 minutes)

```bash
git clone https://github.com/AnshumanAtrey/linkedin-harvester.git
cd linkedin-harvester
pip3 install requests openai httpx

# bring your own keys (free tiers): Groq -> console.groq.com/keys, Brave -> brave.com/search/api
GROQ_API_KEY=your_groq_key BRAVE_API_KEY=your_brave_key \
  python3 -m harvester.find "satya.nadella@microsoft.com" --flow balanced
```

Swap in any work email. Output is a JSON record:

```json
{
  "email": "satya.nadella@microsoft.com",
  "derived_name": "Satya Nadella",
  "company": "microsoft",
  "linkedin_url": "https://www.linkedin.com/in/satyanadella",
  "confidence": 0.97,
  "passes_gate": true,
  "source": "dork:brave"
}
```

Flags: `--flow regex|balanced|full`, `--name "Full Name"` (skip name derivation), `--mode incremental|backfill`.

## Run it on Apify

Open the actor, paste one or more emails, pick a flow, add your Groq + Brave keys, Start. Results land in the dataset, one row per email.

## What does it cost (on Apify)?

Pay-per-event: a small per-email fee plus a charge only when a confident match is found. A confident lookup is well under a cent. Search and AI run on your own free-tier keys, so the actor fee is just the orchestration.

## How accurate is it?

Honest by design. It resolves confidently when there is a public anchor:

- **Corporate emails** (`first.last@company.com`) resolve well - name + company + search is a strong signal.
- **Developers / public people** resolve even from a bare gmail, via the GitHub/Gravatar enrich step.
- **Bare gmail with no name pattern** (`coolguy@gmail.com`) is an honest miss - there is no public anchor, and the tool returns `found: false` rather than guessing.

A name-only match must be corroborated by a second independent signal before it clears the confidence gate, so common names do not produce false positives.

## Limitations

- Public OSINT, not a private contact database. No public footprint means no match.
- Search needs a key (Brave or Google CSE) to resolve non-developer emails.
- Free-provider emails with cryptic local parts cannot be resolved by anyone without paid data brokers.

## Ethical use

For legitimate research, sales enrichment, and verification. Respect the privacy laws that apply to you (GDPR, CCPA, local equivalents). Do not use it to contact people who have asked not to be contacted.

## License

MIT (see LICENSE).
