# Style profiles — draft (informative)

Status: DRAFT · Informative, except where it cites SPEC.md
Prior art: this pattern generalizes ideas from Percona Lab's MYNAH (MIT),
rebuilt here as an open HCS convention.

## What this is

A **style profile** teaches any AI client to write *as* the context owner —
their register, rhythm, greetings, sign-offs, even their consistent
imperfections — per communication context and per language.

Voice is impersonation-adjacent, so the entire mechanism rides on two things
the protocol already has: memory pages and the sensitivity gate. There is no
new subsystem, no new scope, and no product dependency. Any conforming HCS
server hosts style profiles; any client that can read sensitive memory can
use them.

## Addressing (the only part servers must know)

Style profiles are memory pages (SPEC §5) under the reserved **`style/`**
namespace:

```
style/writing-profile          general voice profile (default; always valid)
style/{context-id}             per-context profile, e.g. style/email-external
style/{context-id}.{lang}      language variant, e.g. style/email-external.pt
style/_guide                   optional: how-to-apply instructions, as data
```

- Pages under `style/` **SHOULD be written with `sensitivity: sensitive`**,
  which puts them behind `memory.sensitive:read` (SPEC §5, §7.1) and outside
  the §7.2 default grant. Granting a client your voice is an explicit,
  per-client consent decision.
- `{context-id}` is a short kebab-case label for a communication context.
  The taxonomy below is a starting vocabulary, not a closed list.
- `{lang}` is a BCP 47 primary subtag (`pt`, `de`, `ja`). Clients fall back:
  exact variant → base context → `style/writing-profile`.
- The page body is Markdown. Its internal structure (below) is convention —
  servers MUST treat it as opaque content.

## Profile body (convention for authors and clients)

Keep each profile compact — 8 to 15 bullet lines. Recommended fields:

| Field | Notes |
|---|---|
| **Tone** | e.g. "casual-collaborative — warm but efficient" |
| **Formality** | 1–5 with a one-clause rationale |
| **Sentence / message length** | typical rhythm and size |
| **Greeting / Closing** | exact habitual forms, or "none" |
| **Emoji / Punctuation** | frequency and signature marks |
| **Directness** | how asks, pushback, and no's are phrased |
| **Signature moves** | 2–3 recurring patterns, quoted |
| **Avoid** | what would instantly not sound like the owner |
| *Imperfections* (optional) | consistent misspellings, casing, abbreviations — reproducible style unless the owner disables it |
| *Formality markers* (optional, non-English) | tu/vous, du/Sie, honorifics |

Header metadata (in the page body, below the frontmatter): last-updated,
sample count, language(s).

Starting context taxonomy: `chat-dm`, `chat-channel`, `email-internal`,
`email-external`, `doc-comment`, `notes-internal`, `calendar-invite`,
`blog-public`.

## Deriving profiles (LEARN)

Extends the rules in [profile-bootstrap.md](profile-bootstrap.md):

1. **Samples, not vibes.** Derive from 5+ real samples of the owner's own
   writing per context. Fewer samples → note lower confidence in the page.
2. **Consistency is voice; accident is noise.** A quirk that appears three or
   more times across samples is style and belongs in the profile (including
   imperfections). One-offs are ignored.
3. **Merge, never overwrite.** Updating a profile merges new observations and
   notes drift inline ("shifted warmer through 2026") rather than replacing
   history silently.
4. **One language per pass.** Multilingual owners get language variants when
   their style genuinely differs per language; a shared profile with a
   multi-value language note when it doesn't.
5. Write with `sensitivity: sensitive`. Always.

## Using profiles (COMPOSE)

1. Pick the profile by context (recipient relationship beats channel;
   audience size beats topic), then by target language, with the fallback
   chain above.
2. Apply it closely — including imperfections unless disabled. Never fall
   back to generic assistant voice while claiming to write as the owner.
3. **Fail loudly on the consent gate.** If style pages exist but the token
   lacks `memory.sensitive:read`, say exactly that and stop impersonating —
   never silently degrade to a generic voice the owner didn't approve.
4. Drafting in another language means writing natively in that language's
   register, not translating an English draft.

## What is deliberately NOT standardized

Field wording, the exact taxonomy, disambiguation heuristics, and derivation
prompts are all free to evolve without touching the protocol. A server that
knows nothing about this document but serves memory pages correctly already
supports style profiles in full.
