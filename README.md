# LinkedIn Profile Finder — Email to LinkedIn URL

Turn an email address into the person's public LinkedIn profile — with a confidence score on every match. Paste one email or a whole list and get back a clean table of LinkedIn URLs, ready for your CRM, outreach, or recruiting pipeline. **No LinkedIn login, no cookies, nothing tied to your account.**

---

## What you get

- **Email in → best-match LinkedIn URL out**, with a 0–100% confidence score on every row so you know which matches to trust.
- **Bulk or one-off** — look up a single address or thousands, one result row each.
- **Pay only for matches that land.** Emails that can't be matched cost almost nothing.
- **Near-zero cost per match** — the lookup runs on your own free-tier keys, so there's no data-broker markup.
- **Account-safe** — it never logs into LinkedIn or touches your session, so there's nothing to get flagged.

## Who it's for

- **Sales & growth** — enrich inbound leads and sign-ups with the right LinkedIn profile before you reach out.
- **Recruiting** — turn a list of candidate emails into LinkedIn profiles.
- **RevOps / CRM** — clean, verify, and backfill contact records at scale.
- **Founders & operators** — instantly see who actually emailed you.

## How to use it

1. Paste a single email, or a list of emails.
2. Pick a matching mode — **Balanced** is the default and works for most lists.
3. *(Optional)* add your free Brave Search and Groq keys for the widest coverage.
4. Hit **Start**. Results appear in the dataset, one row per email.

### Matching modes

| Mode | Best for |
|---|---|
| **No AI** | Fastest and free — accepts only the clear, unambiguous matches. |
| **Balanced** *(recommended)* | The default. Spends a little extra effort only on the uncertain matches. |
| **Full AI** | Highest match rate — works hardest on every email. |

### What a result looks like

| Email | Found | LinkedIn URL | Confidence | Name |
|---|---|---|---|---|
| satya.nadella@microsoft.com | ✅ | linkedin.com/in/satyanadella | 97% | Satya Nadella |
| coolguy@gmail.com | — | — | — | — |

Or as JSON:

```json
{
  "email": "satya.nadella@microsoft.com",
  "linkedin_url": "https://www.linkedin.com/in/satyanadella",
  "confidence": 0.97,
  "found": true,
  "name": "Satya Nadella"
}
```

## Pricing

**Pay-per-result.** A tiny fee per email processed, plus a small charge only when a confident match is found — a confident lookup costs well under a cent. Search and AI run on your own free-tier keys, so you're paying for the lookup itself, not data-broker markup.

## How good are the matches?

- **Work emails** (`name@company.com`) match reliably — that's the sweet spot.
- **People with a public professional presence** match even from a personal address.
- **No public profile to find?** You get a clean *not found* — never a confident guess. Every accepted match has to clear the confidence bar you set, so junk stays out of your list.

## Good to know

- Works on **public information only** — no private database, no broker-sourced contact data.
- Best on professional/work emails; some personal addresses simply have no public profile to match.
- **You stay in control** — set the confidence bar, choose how much AI to use, bring your own keys.

## Run it yourself (open source)

The actor is open source under the MIT license. To run it from the command line with your own keys:

```bash
git clone https://github.com/AnshumanAtrey/linkedin-harvester.git
cd linkedin-harvester
pip3 install -r requirements.txt

GROQ_API_KEY=your_groq_key BRAVE_API_KEY=your_brave_key \
  python3 -m harvester.find "satya.nadella@microsoft.com"
```

Free keys: Groq → console.groq.com/keys · Brave → brave.com/search/api

## Use responsibly

Built for legitimate sales, recruiting, research, and verification. Follow the privacy laws that apply to you (GDPR, CCPA, and local equivalents) and honor opt-out and do-not-contact requests.

## License

MIT — see [LICENSE](LICENSE).
