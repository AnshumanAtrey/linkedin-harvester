# LinkedIn Profile Finder - Email to LinkedIn URL Lookup

Turn an email address into the person's public LinkedIn profile, with a confidence score on every match. Paste one email or a whole list and get back a clean table of LinkedIn URLs for your CRM, outreach or recruiting pipeline. **No LinkedIn login, no cookies, nothing tied to your account.**

Use it as a reverse email lookup, an email to LinkedIn API or a lead enrichment step from the Apify Console, the Apify API, Python, JavaScript, n8n, Make or an AI agent, and export the rows as JSON, CSV or Excel. Available as an [Apify Actor](https://apify.com/anshumanatrey/linkedin-harvester). $0.005 per email checked plus $0.02 per confident match. Works with no API keys; free Brave Search and Groq keys widen coverage.

## What does it do?

- **Email in, best-match LinkedIn URL out**, with a 0 to 100% confidence score on every row so you know which matches to trust.
- **Bulk or one-off.** A single address or thousands, one result row each.
- **Pay for results.** Half a cent per email checked; the match fee applies only when a URL clears your confidence gate.
- **Public information only.** GitHub commit authors, Gravatar, PGP keyservers and handle probes on 8 platforms. No data broker, no private database.
- **Account-safe.** It never logs into LinkedIn or touches your session, so there is nothing to get flagged.

## How is it different from other email to LinkedIn finders?

- **Every row shows its evidence.** The confidence score comes with where the name came from (the address, a GitHub commit, Gravatar) and on how many platforms the handle was confirmed, so a match can be checked instead of taken on trust.
- **A miss is a clean miss.** Role mailboxes (info@, support@, sales@) are skipped, and an address with no candidate returns `found: false` rather than a confident guess.
- **Possible matches are free.** Rows between 50% and your gate come back with their score and no match fee, for you to verify.
- **No data broker behind it.** Results are rebuilt from public developer and social profiles on every run, so nothing comes from a purchased database.

## When should I use it?

- **Sales and growth:** enrich inbound leads and sign-ups with the right LinkedIn profile before you reach out.
- **Recruiting:** turn a list of candidate emails into LinkedIn profiles.
- **RevOps and CRM:** clean, verify and backfill contact records at scale.
- **Founders and operators:** see who actually emailed you.

## How much does it cost to find a LinkedIn profile from an email?

Pay per event. Platform compute is included in the prices.

| Event | Price | When it is charged |
|---|---|---|
| Run start | $0.01 | Once per run |
| Email checked | $0.005 | Once per email, found or not |
| Confident match | $0.02 | Only when a URL clears your confidence gate (80% by default) |

On paid Apify plans the email and match fees are 10% less on Scale ($0.0045 and $0.018) and 20% less on Business and above ($0.004 and $0.016). The run start fee is the same on every plan.

| Job (Free and Starter price) | Cost |
|---|---|
| The 6-email run below (1 confident match) | $0.06 |
| 1 email, confident match | $0.035 |
| 100 emails, 30 confident matches | $1.11 |
| 1,000 emails, 250 confident matches | $10.01 |

A run stops at its spending limit: an email is looked up only while the limit can still pay for it and a confident match, and a limit that cannot pay for one email ends with nothing looked up or charged.

## How does the price compare with other email to LinkedIn finders?

Actors on the Apify Store that turn an email into a LinkedIn profile, found by searching "email to linkedin", "linkedin profile finder email" and "reverse email lookup linkedin" on 2026-10-30, with 30 or more users in the last 30 days, ordered by users. Free-plan prices from each listing.

| Actor | Users, 30 days | Price |
|---|---|---|
| oday/mawsool-email-linkedin-lookup | 166 | $0.002 per email looked up |
| neuralverge/neuralverge-email-enrichment | 96 | $0.01 per result row |
| b2bsearch/reverse-email-lookup | 37 | $0.0032 per person found, $0.008 with full details |
| b2bsearch/email-to-linkedin | 32 | $0.0032 per profile found, misses free |
| enrich-crm/enrich-crm-reverse-email | 30 | $0.03 per enrichment result |
| This actor | 9 | $0.005 per email checked, $0.02 per confident match, $0.01 per run |

Where others are cheaper: oday's lookup costs less per email, and b2bsearch's two actors charge less per found profile and nothing for misses. This actor costs more per match because a match is charged only above your confidence gate and arrives with its evidence; compare on a sample of your own list.

## Which inputs does it take?

Only the emails are needed; every other field has a working default.

| Field | Required | What it does |
|---|---|---|
| Email address (`email`) | One of the two | A single address for a quick one-off, such as jane.doe@stripe.com |
| Emails (bulk) (`emails`) | One of the two | One email per row, or several separated by commas. Role mailboxes like info@ are skipped |
| AI assistance (`aiMode`) | No | `regex` (No AI: fastest, clear matches only), `balanced` (default: AI only on uncertain matches) or `full` (AI on every email; needs a Groq key) |
| Minimum confidence to scrape (%) (`minConfidencePct`) | No | The confidence gate, 80 by default. Only matches at or above it are charged as confident |
| Check public profiles (recommended) (`deepEnrich`) | No | On by default. Looks the address up on GitHub, Gravatar, PGP keyservers and 8 platforms' handles, which is what resolves a URL without a search key |
| Scrape the matched profile (`scrapeProfiles`) | No | Off by default. Fetches the full LinkedIn profile after a confident match; needs a Bright Data key |
| Run mode (`runMode`) | No | `incremental` (default, free resolvers only) or `backfill` (also the paid Findymail fallback for misses) |
| Groq API key (`groqApiKey`) | No | Free key for the AI name-splitting in Balanced and Full AI modes |
| Brave Search API key (`braveApiKey`) | No | Free key that adds a web-search check on each candidate, the designed way to lift 78% matches over the gate |
| Google Custom Search key (`googleCseKey`) and CX id (`googleCseCx`) | No | Legacy alternative to Brave for the search step |
| Bright Data API key (`brightdataApiKey`) | No | Needed only for Scrape the matched profile |
| Findymail API key (`findymailApiKey`) | No | Needed only for Backfill mode |

Example input:

```json
{
  "emails": ["anshumanatrey@gmail.com", "satya.nadella@microsoft.com"],
  "aiMode": "balanced"
}
```

## What does the output look like?

This is the real dataset from a run on 2026-09-12 (build 0.1.5, no API keys, default settings): six emails in 25 seconds at 1 GB of memory. One row, a private person's personal address, is left out here.

| Email | Found | LinkedIn URL | Confidence | Confident | Name | Name from | Evidence |
|---|---|---|---|---|---|---|---|
| anshumanatrey@gmail.com | yes | linkedin.com/in/anshumanatrey | 97% | yes | Anshuman Atrey | GitHub commit | handle confirmed on 4 platforms |
| satya.nadella@microsoft.com | yes | linkedin.com/in/satyanadella | 78% | no | Satya Nadella | address | handle confirmed on 4 platforms |
| jensen.huang@nvidia.com | yes | linkedin.com/in/jensenhuang | 78% | no | Jensen Huang | address | handle confirmed on 6 platforms |
| tim.cook@apple.com | yes | linkedin.com/in/timcook | 78% | no | Tim Cook | address | handle confirmed on 3 platforms |
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

## How fast is it?

About 4 seconds per email at the 1 GB default, so a 100-email list finishes in about 7 minutes. The 6-email run above used 0.0069 compute units.

## Common questions

### How accurate are the matches?

Measured on the run above: 5 of 6 addresses resolved to a URL, 1 above the gate, and the role mailbox was correctly skipped.

- **Work emails** (`first.last@company.com`) give the name from the address itself. The handle probes then look for that name as a handle across GitHub, GitLab, dev.to, npm, Gravatar, Linktree, About.me, YouTube and Telegram. Three or more hits put the match at 78%.
- **Personal addresses** resolve when the person has a public developer or social footprint. A GitHub commit author name or a Gravatar display name is authoritative and lifts confidence to the high 90s.
- **Over the gate.** A confident match needs a name from an authoritative source plus a handle that is consistent across platforms. A free Brave Search key adds a web-search check on each candidate.

### Does it log into LinkedIn?

No. It never logs in, uses no cookies and touches no session. LinkedIn login-walls its pages, so a URL is a strong lead confirmed by cross-platform evidence, not a fetched profile. Turn on Scrape the matched profile with a Bright Data key if you need the full profile.

### How do I run it from Python or an AI agent?

Through the Apify API, with your Apify token:

```python
from apify_client import ApifyClient

client = ApifyClient("<YOUR_APIFY_TOKEN>")
run = client.actor("anshumanatrey/linkedin-harvester").call(run_input={"emails": ["satya.nadella@microsoft.com"]})
for row in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(row["email"], row["linkedin_url"], row["confidence"])
```

AI agents can call it through the Apify MCP server at https://mcp.apify.com, and n8n and Make have Apify nodes.

### Am I charged for emails that find nothing?

The $0.005 email fee covers the lookup, found or not. The $0.02 match fee applies only to a URL at or above your confidence gate, so misses and possible matches cost nothing more.

### Is it legal to use?

It reads public information only. Use it for legitimate sales, recruiting, research and verification, follow the privacy laws that apply to you (GDPR, CCPA and local equivalents), and honor opt-out and do-not-contact requests.

## Limitations

- A URL is resolved from public evidence, not read from LinkedIn, which login-walls its pages.
- Personal addresses with no public developer or social footprint usually stay unresolved.
- Without a Brave Search key, most work-email matches land at 78%, just under the default gate; lower the gate or add the free key.
- Role mailboxes (info@, support@, sales@) are skipped by design.

## Who maintains it?

Built and maintained by **Anshuman Atrey** ([@AnshumanAtrey](https://github.com/AnshumanAtrey)), who publishes a portfolio of OSINT actors on Apify Store. For a feature request or a bug, message [LinkedIn](https://linkedin.com/in/anshumanatrey) (fastest), open an issue on the GitHub repo, or write through [atrey.dev](https://atrey.dev).

## Sibling actors

| Actor | Use case |
|---|---|
| [holehe-email-osint](https://apify.com/anshumanatrey/holehe-email-osint) | Email -> registered accounts across 120+ platforms |
| [domain-history-contact-osint](https://apify.com/anshumanatrey/domain-history-contact-osint) | Domain -> previous owner, WHOIS history, archived contacts with source URLs |
| [theharvester-osint](https://apify.com/anshumanatrey/theharvester-osint) | Domain -> emails, subdomains and IPs from 54+ public sources |

## Documentation

- Apify Store: https://apify.com/anshumanatrey/linkedin-harvester
- GitHub repo: https://github.com/AnshumanAtrey/linkedin-harvester (MIT license, see [LICENSE](LICENSE))

The actor is open source. To run it from the command line with your own keys:

```bash
git clone https://github.com/AnshumanAtrey/linkedin-harvester.git
cd linkedin-harvester
pip3 install -r requirements.txt

GROQ_API_KEY=your_groq_key BRAVE_API_KEY=your_brave_key \
  python3 -m harvester.find "satya.nadella@microsoft.com"
```

Free keys: Groq at console.groq.com/keys, Brave at brave.com/search/api

## Last updated

2026-10-30 (version 0.2)
