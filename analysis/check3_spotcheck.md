# Check-3 spot-check — verifying the HoVer ~90%-retrieval-only ceiling

**Date:** 2026-07-02 · **$0, read-only** (frozen necrosis capture untouched: `necrosis/reflections.json`,
`reflect_in_*.txt` mtime 2026-07-01). Verifies the offline-batch Check-3 claim (33 events → ~90%
retrieval-only → content-scorer addressable ceiling ~10%) before it reaches Lakshya. Method: re-judge 8
**stress-selected** events on the **byte-complete reasoning** (the original Check-3 judged on ~300-char
trimmed reasoning).

## The line being pinned
A failure is **ADDRESSABLE (reasoning-visible)** only if a better *prompt/instruction* could plausibly
change the reasoning to fix it. If the reasoning was **correct and complete — even naming the entity** —
but the retriever simply didn't return the gold document → **retrieval-only, invisible to any SI-content
curriculum scorer** (no prompt change to the reasoning helps).

## Per-event verdicts

| ev | selection | missed gold doc | original label | re-read verdict |
|--|--|--|--|--|
| 1 | recheck-(a) | Greek Fire (band) | reasoning-visible | **FLIP → retrieval-only** |
| 10 | recheck-(a) | Philip Glass | reasoning-visible | **FLIP → retrieval-only** |
| 4 | borderline | Gainesville, Florida | retrieval-only | HOLDS |
| 13 | borderline | Philip Glass | retrieval-only | HOLDS |
| 18 | borderline | Mikael Åkerfeldt | retrieval-only | HOLDS |
| 2 | calibration | Beached Az | retrieval-only | HOLDS |
| 7 | calibration | Shengzhou | retrieval-only | HOLDS |
| 24 | calibration | Toshi (musician) | retrieval-only | HOLDS |

### The two flips (my original addressable cases — both fail on re-read)

**Event 1 — Greek Fire (gen_query), missed `Greek Fire (band)`.** Byte-complete reasoning:
> "…The claim states that Greek Fire originated in 1998 and in a more southern location than the Smashing
> Pumpkins. **To verify this, we need to check the origin location of Greek Fire and confirm whether it is
> south of Chicago, and also confirm the date Greek Fire was established.**…"

The reasoning is **sound** — it correctly identifies that it must find Greek Fire's origin/date and queries
toward it. It does **not** "accept the implication" (my original Check-3 read the trimmed first ~300 chars,
which stopped before "To verify this, we need to check…"). The query is reasonable; the retriever didn't
return the `Greek Fire (band)` doc. → **retrieval-only, not prompt-fixable.**

**Event 10 — Schreker/Tim Fain (gen_query), missed `Philip Glass`.** Byte-complete reasoning:
> "…Tim Fain is an American violinist **best known for performing with composer Philip Glass**. … The
> composer Tim Fain is associated with, **Philip Glass**, is not identified as a teacher either…"

The reasoning **names Philip Glass explicitly** and reasons correctly. My original note ("refers to 'a
composer' without naming Philip Glass") was a **misread of the trimmed text.** The entity is named; the doc
just wasn't retrieved. → **retrieval-only.**

### The borderlines held (the under-count check)

**Event 18 — Sonic Youth/Åkerfeldt, missed `Mikael Åkerfeldt`** (the sharpest case): the reasoning does the
*exact* right disambiguation —
> "Michael Akerfeldt is **likely a confusion or misspelling—Mikael Åkerfeldt is the frontman of Opeth**, not
> a bassist…"

— and the doc *still* wasn't fetched. This is the "Michael Akerfeldt texture" from GATE 1, but with the
reasoning **correct**, so it is definitively retrieval-only and `failure_mode` is structurally blind to it.
Events 4 & 13 likewise name the missed entity (Gainesville, Florida; Philip Glass) with correct reasoning →
retrieval-only holds. Calibration events 2/7/24 hold (reasoning sound; entity un-retrieved or, for ev 24,
correctly flagged as still-needed).

## Result
- **Both** original reasoning-visible cases (ev 1, 10) **flip to retrieval-only** on the byte-complete
  reasoning. My original Check-3 slightly **over-counted addressable** because trimmed text hid the parts
  where the reasoning correctly named/targeted the missed entity.
- All 3 stress-borderline cases (chosen precisely to catch *under*-counting) and all 3 calibration cases
  **hold** as retrieval-only.
- **Revised addressable fraction: 2/30 → 0/30 on the spot-check.**

## Bottom line
**The ~90%-retrieval-only headline SURVIVES — and strengthens to ≈97–100% retrieval-only on the checked
subset; the content-scorer addressable ceiling is ≤7%, plausibly ~0–3%, even lower than the email states.**
The correction moves the number in the direction that further *closes* the content-scorer direction, so it
is not a rescue-biased adjustment. The email's ~90% stands (and could be stated more strongly as "≥90%,
spot-check found the addressable slice even thinner").

**Honest caveat:** I re-read 8 of 30 failures byte-complete — the 2 flagged-addressable (both flipped) + 3
strongest borderline retrieval-only + 3 calibration. I did **not** exhaustively re-read the other 22
retrieval-only events for (b)→(a) flips that would raise the fraction; but the stress-selected borderlines
all held and the pattern is consistent. One methodological note for future manual classifications: judge on
byte-complete reasoning, not trimmed spans — the trim caused both misclassifications here.
