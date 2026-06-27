"""Central config. Everything is env-overridable so nothing is hard-coded."""
import os

# Confidence gate: only scrape a person whose LinkedIn match scores >= this.
# Exposed as one tunable number.
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.80"))

# incremental = new mail, free tiers only (default, runs forever ~$0).
# backfill    = 6-year batch, allowed to spend on hosted enrichment.
RUN_MODE = os.environ.get("RUN_MODE", "incremental")

DB_PATH = os.environ.get("DB_PATH", "harvester.db")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")

# Hosted enrichment only fires in backfill mode (keeps incremental free).
USE_HOSTED_IN_BACKFILL = True

# Use the (free, calibrated) heuristic for confidence by default; reserve the AI
# scorer for backfill/ambiguous cases. Keeps the AI quota for personas — the
# high-value output. Set AI_SCORING=true to have Gemini judge every match.
AI_SCORING = os.environ.get("AI_SCORING", "false").lower() == "true"

# Mailboxes that are never a person — filtered before we spend anything.
ROLE_LOCALPARTS = {
    "info", "support", "admin", "hello", "contact", "sales", "team",
    "no-reply", "noreply", "donotreply", "careers", "jobs", "hr",
    "billing", "help", "notifications", "newsletter", "marketing",
}
FREE_MAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "proton.me", "protonmail.com", "aol.com", "live.com",
}

# Newsletter/ESP sending platforms. When the FROM domain is one of these, the
# real person + company is in the Reply-To, not the From (e.g. beehiiv, mailchimp).
ESP_DOMAINS = {
    "beehiiv.com", "substack.com", "mcsv.net", "rsgsv.net", "list-manage.com",
    "mailchimpapp.net", "sendgrid.net", "mailgun.org", "sparkpostmail.com",
    "sendinblue.com", "brevo.com", "hubspotemail.net", "klaviyomail.com",
    "cmail19.com", "cmail20.com", "amazonses.com", "mailerlite.com", "ck.page",
    "convertkit-mail.com", "postmarkapp.com", "intercom-mail.com",
}
# Body phrases that mark a bulk blast (vs a personal email) — used with a role
# Reply-To to filter newsletters out before any spend.
NEWSLETTER_MARKERS = (
    "unsubscribe", "edit your settings", "view in browser", "manage preferences",
    "update your preferences", "weekly newsletter", "you are receiving this",
    "you received this email", "view this email in your browser",
)
