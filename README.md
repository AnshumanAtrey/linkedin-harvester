# LinkedIn Profile Finder - Email to LinkedIn URL

Turn an email address into the person's public LinkedIn profile, with a confidence score on every match. Paste one email or a whole list and get back a clean table of LinkedIn URLs for your CRM, outreach or recruiting pipeline. **No LinkedIn login, no cookies, nothing tied to your account.**

Available as an [Apify Actor](https://apify.com/anshumanatrey/linkedin-harvester). $0.005 per email checked plus $0.02 per confident match. Works with no API keys; free Brave Search and Groq keys widen coverage.

## What you get

- **Email in, best-match LinkedIn URL out**, with a 0 to 100% confidence score on every row so you know which matches to trust.
- **Bulk or one-off.** A single address or thousands, one result row each.
- **Pay for results.** Half a cent per email checked; the match fee applies only when a URL clears your confidence gate.
- **Public information only.** GitHub commit authors, Gravatar, PGP keyservers and handle probes on 8 platforms. No data broker, no private database.
- **Account-safe.** It never logs into LinkedIn or touches your session, so there is nothing to get flagged.

## Who it's for

- **Sales and growth:** enrich inbound leads and sign-ups with the right LinkedIn profile before you reach out.
- **Recruiting:** turn a list of candidate emails into LinkedIn profiles.
- **RevOps / CRM:** clean, verify and backfill contact records at scale.
- **Founders and operators:** see who actually emailed you.

## How to use it

1. Paste a single email, or a list of emails. The form comes prefilled with two demo addresses; replace them with yours.
2. Leave **Check public profiles** on. It recovers the name and a cross-platform handle, which is what resolves a URL without a search key.
3. Pick a matching mode. **Balanced** is the default and works for most lists.
4. Optional: add your free Brave Search and Groq keys for web-search corroboration and AI name-splitting.
5. Hit **Start**. Results appear in the dataset, one row per email.

### Matching modes

| Mode | Best for |
|---|---|
| **No AI** | Fastest and free. Accepts only the clear, unambiguous matches. |
| **Balanced** (recommended) | The default. Spends extra effort only on the uncertain matches. |
| **Full AI** | Highest match rate. Works hardest on every email. Needs a Groq key. |

## What does the output look like?

This is the real dataset from a run on 2026-09-12 (build 0.1.5, no API keys, default settings). Six emails, 25 seconds, 1 GB of memory.

| Email | Found | LinkedIn URL | Confidence | Confident | Name | Name from | Evidence |
|---|---|---|---|---|---|---|---|
| anshumanatrey@gmail.com | yes | linkedin.com/in/anshumanatrey | 97% | yes | Anshuman Atrey | GitHub commit | handle confirmed on 4 platforms |
| satya.nadella@microsoft.com | yes | linkedin.com/in/satyanadella | 78% | no | Satya Nadella | address | handle confirmed on 4 platforms |
| jensen.huang@nvidia.com | yes | linkedin.com/in/jensenhuang | 78% | no | Jensen Huang | address | handle confirmed on 6 platforms |
| tim.cook@apple.com | yes | linkedin.com/in/timcook | 78% | no | Tim Cook | address | handle confirmed on 3 platforms |
| sayujpillai63@gmail.com | yes | linkedin.com/in/sayuj63 | 64% | no | Sayuj Pillai | GitHub commit | handle confirmed on 1 platform |
| info@stripe.com | no | | 0% | no | | | role mailbox, no candidate |

**Confident** means the row cleared the 80% gate. Those are the only rows that carry the match fee. Rows between 50% and 79% are possible matches, returned free with their score, for you to verify before use.

One row as JSON (the `signals` block is what the scorer saw):

```json
{
  "email": "anshumanatrey@gmail.com",
  "found": true,
  "linkedin_url": "https://www.linkedin.com/in/anshumanatrey",
  "confidence": 0.97,
  "passes_gate": true,
  "gate_threshold": 0.8,
  "derived_name": "Anshuman Atrey",
  "name_source": "github_commit",
  "source": "handle_pivot",
  "evidence": "handle 'anshumanatrey' confirmed on 4 platform(s) -> likely LinkedIn slug",
  "signals": {
    "names": [{"value": "Anshuman Atrey", "source": "github_commit"}],
    "handles": ["anshumanatrey"],
    "confirmed_socials": ["GitHub: https://github.com/anshumanatrey", "YouTube: https://www.youtube.com/@anshumanatrey", "Telegram: https://t.me/anshumanatrey"]
  }
}
```

## What does it cost?

Pay per event. Platform compute is included in the prices.

| Event | Price | When it is charged |
|---|---|---|
| Run start | $0.01 | Once per run |
| Email checked | $0.005 | Once per email, found or not |
| Confident match | $0.02 | Only when a URL clears your confidence gate (80% by default) |

Typical jobs:

| Job | Cost |
|---|---|
| The 6-email run above (1 confident match) | $0.06 |
| 1 email, confident match | $0.035 |
| 100 emails, 30 confident matches | $1.11 |
| 1,000 emails, 250 confident matches | $10.01 |

The 6-email run used 0.0069 compute units at the 1 GB default, about 4 seconds per email.

## How good are the matches?

Measured on the run above: 5 of 6 addresses resolved to a URL, 1 above the gate, and the role mailbox was correctly skipped.

- **Work emails** (`first.last@company.com`) give the name from the address itself. The handle probes then look for that name as a handle across GitHub, GitLab, dev.to, npm, Gravatar, Linktree, About.me, YouTube and Telegram. Three or more hits put the match at 78%.
- **Personal addresses** resolve when the person has a public developer or social footprint. A GitHub commit author name or a Gravatar display name is authoritative and lifts confidence to the high 90s.
- **Over the gate.** A confident match needs a name from an authoritative source plus a handle that is consistent across platforms. A free Brave Search key adds a web-search check on each candidate, the designed way to lift 78% matches over the gate.
- **Not found is a clean not found**, never a confident guess. Role mailboxes (info@, support@, sales@) are skipped rather than probed.

## Good to know

- Speed: about 4 seconds per email at the 1 GB default; a 100-email list finishes in about 7 minutes.
- Works on **public information only**. No private database, no broker-sourced contact data.
- LinkedIn login-walls its pages, so a URL is a strong lead confirmed by cross-platform evidence, not a fetched profile. Turn on **Scrape the matched profile** with a Bright Data key if you need the full profile.
- **You stay in control.** Set the confidence bar, choose how much AI to use, bring your own keys.

## Sibling actors

| Actor | Use case |
|---|---|
| [holehe-email-osint](https://apify.com/anshumanatrey/holehe-email-osint) | Email -> registered accounts across 120+ platforms |
| [domain-history-contact-osint](https://apify.com/anshumanatrey/domain-history-contact-osint) | Domain -> previous owner, WHOIS history, archived contacts with source URLs |
| [theharvester-osint](https://apify.com/anshumanatrey/theharvester-osint) | Domain -> emails, subdomains and IPs from 54+ public sources |

## Run it yourself (open source)

The actor is open source under the MIT license. To run it from the command line with your own keys:

```bash
git clone https://github.com/AnshumanAtrey/linkedin-harvester.git
cd linkedin-harvester
pip3 install -r requirements.txt

GROQ_API_KEY=your_groq_key BRAVE_API_KEY=your_brave_key \
  python3 -m harvester.find "satya.nadella@microsoft.com"
```

Free keys: Groq at console.groq.com/keys, Brave at brave.com/search/api

## Use responsibly

Built for legitimate sales, recruiting, research and verification. Follow the privacy laws that apply to you (GDPR, CCPA and local equivalents) and honor opt-out and do-not-contact requests.

## License

MIT, see [LICENSE](LICENSE).

## Last updated

2026-09-12 (version 0.1.5)
