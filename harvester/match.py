"""Classical name matching - the pre-LLM record-linkage toolkit.

Everything here is deterministic, dependency-free, and microsecond-cheap. This is
the "good algo" that makes the no-AI flow genuinely good instead of degraded:
Jaro-Winkler (the US-Census name-matching metric), a nickname gazetteer, and a
light phonetic key. The LLM is reserved for the ambiguous tail these can't crack.
"""
from __future__ import annotations

import re

# Bidirectional nickname gazetteer (the pre-AI answer to "AI handles nicknames").
_NICK_PAIRS = [
    ("rob", "robert"), ("bob", "robert"), ("bobby", "robert"),
    ("bill", "william"), ("will", "william"), ("liam", "william"),
    ("liz", "elizabeth"), ("beth", "elizabeth"), ("eliza", "elizabeth"),
    ("jim", "james"), ("jimmy", "james"), ("jamie", "james"),
    ("mike", "michael"), ("mick", "michael"), ("mikey", "michael"),
    ("dave", "david"), ("rick", "richard"), ("dick", "richard"), ("rich", "richard"),
    ("tom", "thomas"), ("tommy", "thomas"), ("chris", "christopher"),
    ("nick", "nicholas"), ("dan", "daniel"), ("danny", "daniel"),
    ("joe", "joseph"), ("joey", "joseph"), ("tony", "anthony"),
    ("steve", "steven"), ("stevphen", "stephen"), ("matt", "matthew"),
    ("alex", "alexander"), ("sandy", "alexander"), ("sam", "samuel"),
    ("ben", "benjamin"), ("benny", "benjamin"), ("ed", "edward"), ("eddie", "edward"),
    ("kate", "katherine"), ("katie", "katherine"), ("cathy", "catherine"),
    ("peggy", "margaret"), ("meg", "margaret"), ("maggie", "margaret"),
    ("sue", "susan"), ("suzie", "susan"), ("becky", "rebecca"),
    ("jen", "jennifer"), ("jenny", "jennifer"), ("abby", "abigail"),
]
_NICK = {}
for _a, _b in _NICK_PAIRS:
    _NICK.setdefault(_a, set()).add(_b)
    _NICK.setdefault(_b, set()).add(_a)


def alnum(s: str) -> str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", (name or "").lower()) if len(t) > 1]


def _jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    l1, l2 = len(s1), len(s2)
    if l1 == 0 or l2 == 0:
        return 0.0
    reach = max(l1, l2) // 2 - 1
    m1, m2 = [False] * l1, [False] * l2
    matches = 0
    for i in range(l1):
        for j in range(max(0, i - reach), min(i + reach + 1, l2)):
            if not m2[j] and s1[i] == s2[j]:
                m1[i] = m2[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    t = k = 0
    for i in range(l1):
        if m1[i]:
            while not m2[k]:
                k += 1
            if s1[i] != s2[k]:
                t += 1
            k += 1
    t /= 2
    return (matches / l1 + matches / l2 + (matches - t) / matches) / 3


def jaro_winkler(s1: str, s2: str, p: float = 0.1) -> float:
    j = _jaro(s1, s2)
    prefix = 0
    for a, b in zip(s1, s2):
        if a != b:
            break
        prefix += 1
        if prefix == 4:
            break
    return round(j + prefix * p * (1 - j), 4)


def _nick_eq(a: str, b: str) -> bool:
    return a == b or b in _NICK.get(a, ()) or a in _NICK.get(b, ())


def name_similarity(name: str, slug: str) -> float:
    """How well does a person name match a LinkedIn slug? 0..1, deterministic.

    Combines de-spaced Jaro-Winkler (typo/variant tolerant) with token coverage
    that understands nicknames. Real slugs are messy (concatenated, hyphenated,
    numeric suffixes), so we compare both flat and tokenized forms and take the
    most charitable that still requires real overlap.
    """
    if not name or not slug:
        return 0.0
    n_flat = alnum(name)
    s_flat = alnum(re.sub(r"\d+$", "", slug))           # drop trailing slug digits
    jw = jaro_winkler(n_flat, s_flat)

    n_toks = tokens(name)
    s_toks = tokens(slug.replace("-", " ")) or [s_flat]
    if n_toks:
        covered = sum(any(_nick_eq(nt, st) or nt in s_flat for st in s_toks) for nt in n_toks)
        token_score = covered / len(n_toks)
    else:
        token_score = 0.0

    # exact de-spaced match is the strongest deterministic signal
    if n_flat and n_flat == s_flat:
        return 1.0
    return round(max(jw, token_score), 3)
