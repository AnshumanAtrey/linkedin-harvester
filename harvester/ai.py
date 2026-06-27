"""Provider-agnostic LLM wrapper. Groq preferred, Gemini fallback.

The pipeline treats AI as OPTIONAL: with no key (or once a quota hits) ask_json()
returns None and every caller falls back to a heuristic. Groq is preferred because
its free tier is far more generous than Gemini's (llama-3.1-8b-instant: ~14.4K
requests/day, 500K tokens/day — vs Gemini free's ~1K/day).

Pick the brain by env:
  AI_PROVIDER=groq|gemini   (optional — forces one)
  else: GROQ_API_KEY -> groq ; GEMINI_API_KEY -> gemini
"""
import os
import json

_WARNED = False
_DISABLED = False        # circuit breaker: trips on first quota/rate hit, stops hammering


def _provider() -> str:
    forced = os.environ.get("AI_PROVIDER", "").strip().lower()
    if forced in ("groq", "gemini"):
        return forced
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return ""


def available() -> bool:
    return bool(_provider()) and not _DISABLED


def provider_label() -> str:
    """Human-readable name of the active brain, for the run header."""
    p = _provider()
    if not p or _DISABLED:
        return "heuristic (no AI key)"
    if p == "groq":
        return f"Groq · {os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')}"
    return f"Gemini · {os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-lite')}"


def ask_json(prompt: str, retries: int = 1) -> dict | None:
    """Ask the active provider for a JSON object. None -> heuristic fallback.

    Quota-respectful:
    - 429 / rate-limit -> do NOT retry; trip the circuit breaker so the rest of
      the run uses the heuristic instead of hammering the API.
    - 503 / overloaded -> retry once after a short backoff (genuine transient load).
    """
    global _DISABLED, _WARNED
    import time
    if _DISABLED:
        return None
    prov = _provider()
    if not prov:
        if not _WARNED:
            print("  [ai] no GROQ/GEMINI key -> using heuristic fallback")
            _WARNED = True
        return None
    for attempt in range(retries + 1):
        try:
            return _groq(prompt) if prov == "groq" else _gemini(prompt)
        except Exception as e:  # never crash the run
            msg = str(e).lower()
            if any(s in msg for s in ("429", "resource_exhausted", "rate_limit", "rate limit")):
                _DISABLED = True
                print(f"  [ai] {prov} rate/quota hit -> heuristic for the rest of this run")
                return None
            if any(s in msg for s in ("503", "unavailable", "overloaded")) and attempt < retries:
                time.sleep(2.0)
                continue
            print(f"  [ai] {prov} call failed ({str(e)[:80]}); heuristic fallback")
            return None


def _groq(prompt: str) -> dict:
    from openai import OpenAI          # Groq is OpenAI-compatible
    client = OpenAI(api_key=os.environ["GROQ_API_KEY"],
                    base_url="https://api.groq.com/openai/v1")
    model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt + "\n\nRespond with ONLY a JSON object."}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(resp.choices[0].message.content)


def _gemini(prompt: str) -> dict:
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config={"response_mime_type": "application/json"})
    return json.loads(resp.text)
