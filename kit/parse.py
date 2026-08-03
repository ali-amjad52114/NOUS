"""Natural-language promise parser — turns what you SAID into a commitment.

"i wanna meet with kevin next week for dinner"
  → person=Kevin · activity=dinner · window=7–14 days
  → proposes a real dated slot at a sensible hour (dinner=7pm, coffee=10am…)

Deterministic (regex + calendar math) so it can never fail on stage; an
optional Nebius LLM pass can enrich it, but the demo never depends on it.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

# activity -> (label, hour, duration_hours)
ACTIVITIES = [
    (r"\bdinner\b|\bsupper\b", "dinner", 19, 2.0),
    (r"\blunch\b", "lunch", 12, 1.5),
    (r"\bbreakfast\b|\bbrunch\b", "brunch", 10, 1.5),
    (r"\bcoffee\b", "coffee", 10, 1.0),
    (r"\bdrinks?\b|\bbeers?\b", "drinks", 18, 2.0),
    (r"\bcall\b|\bring\b|\bphone\b|\bfacetime\b", "a call", 16, 0.5),
    (r"\bvisit\b|\bcome (?:and )?see\b|\bcome by\b|\bcome over\b", "a visit", 14, 3.0),
    (r"\bcatch ?up\b", "a catch-up", 17, 1.5),
    (r"\bhang ?out\b|\bhang\b", "hanging out", 15, 3.0),
    (r"\bgym\b|\bworkout\b|\brun\b", "a workout", 8, 1.5),
]

# timeframe -> (earliest_day_offset, latest_day_offset, human label)
TIMEFRAMES = [
    (r"\btomorrow\b", 1, 1, "tomorrow"),
    (r"\bthis weekend\b", 5, 6, "this weekend"),
    (r"\bnext weekend\b", 12, 13, "next weekend"),
    (r"\bthis week\b", 1, 6, "this week"),
    (r"\bnext week\b", 7, 13, "next week"),
    (r"\bnext month\b", 28, 35, "next month"),
    (r"\bin (?:a|1) week\b", 6, 8, "in a week"),
    (r"\bin (?:a|1) month\b", 28, 32, "in a month"),
    (r"\bin (\d+) days?\b", None, None, "in {n} days"),
    (r"\bin (\d+) weeks?\b", None, None, "in {n} weeks"),
    (r"\bbefore (?:you|he|she|they) (?:go|goes|leave|leaves|move|moves)\b", 1, 14, "before they go"),
    (r"\bsoon\b|\bsometime\b", 1, 14, "soon"),
]

STOPWORDS = {"with", "the", "my", "him", "her", "them", "you", "up", "out", "again",
             "for", "at", "in", "to", "a", "an", "and", "some", "someone", "everyone",
             "next", "this", "tomorrow", "today", "later", "soon"}


def _person(text: str) -> str | None:
    # strongest signal first: "with <name>"
    for pat in (r"\bwith\s+(?:my\s+|your\s+|the\s+)?([A-Za-z][A-Za-z'\-]*)",
                r"\b(?:see|seeing|visit|call|meet|meeting|text|message)\s+"
                r"(?:my\s+|your\s+|his\s+|her\s+|the\s+)?([A-Za-z][A-Za-z'\-]*)"):
        for m in re.finditer(pat, text, re.I):
            w = m.group(1)
            if w.lower() not in STOPWORDS:
                return w[:1].upper() + w[1:]
    # fallback: any capitalized word that isn't sentence-initial boilerplate
    for w in re.findall(r"\b([A-Z][a-z]{1,20})\b", text):
        if w.lower() not in STOPWORDS and w.lower() not in {"i", "ill", "im"}:
            return w
    return None


def _activity(text: str):
    for pat, label, hour, dur in ACTIVITIES:
        if re.search(pat, text, re.I):
            return label, hour, dur
    return "time together", 18, 1.5


def _window(text: str) -> tuple[int, int, str]:
    for pat, lo, hi, label in TIMEFRAMES:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        if lo is None:                       # numeric forms
            n = int(m.group(1))
            days = n * 7 if "week" in m.group(0).lower() else n
            return max(1, days - 1), days + 1, label.format(n=n)
        return lo, hi, label
    return 1, 14, "in the next two weeks"


def _fmt(dt: datetime) -> str:
    hour = (dt.strftime("%I:%M %p") if dt.minute else dt.strftime("%I %p")).lstrip("0")
    return f"{dt.strftime('%A %b')} {dt.day}, {hour}"


def propose_slot(lo: int, hi: int, hour: int, now: datetime | None = None) -> tuple[str, int]:
    """Pick a plausible real date inside the window. Prefers Thu/Fri/Sat for
    evening plans, and never proposes a slot in the past."""
    now = now or datetime.now()
    prefer = [4, 5, 3, 6, 2, 1, 0]  # Fri, Sat, Thu, Sun, Wed, Tue, Mon
    best = None
    for offset in range(max(1, lo), max(lo, hi) + 1):
        d = now + timedelta(days=offset)
        rank = prefer.index(d.weekday())
        if best is None or rank < best[0]:
            best = (rank, d, offset)
    _, d, offset = best
    slot = d.replace(hour=hour, minute=0, second=0, microsecond=0)
    return _fmt(slot), offset


def parse_promise(text: str, now: datetime | None = None) -> dict:
    """Free text -> structured commitment proposal."""
    now = now or datetime.now()
    person = _person(text)
    activity, hour, dur = _activity(text)
    lo, hi, window_label = _window(text)
    slot, days_out = propose_slot(lo, hi, hour, now)
    return {
        "person": person,
        "activity": activity,
        "window_label": window_label,
        "deadline_days": hi,
        "proposed_slot": slot,
        "days_out": days_out,
        "duration_hours": dur,
        "promise": text.strip(),
        "understood": bool(person),
    }
