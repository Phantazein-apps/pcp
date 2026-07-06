# Bootstrapping a profile from connected sources — draft (informative)

Status: DRAFT · Informative

## The pattern

A person should not have to type their profile into a form. The natural flow:

1. **Connect sources.** The owner connects tools (notes, email, calendar,
   documents) to their context. This is the only mandatory manual step.
2. **An agent derives the profile.** Any AI client the owner trusts — a local
   LLM, a hosted assistant — connects to the context over MCP with
   `profile.core:write` + `memory:write`, observes the owner's actual data
   (through the context's own `conn.*` tools, or through tool access it
   already has locally), and:
   - patches `profile.core` via `profile.update` with **observed facts only**;
   - writes a full writing-style analysis to memory.
3. **The host prompts for gaps.** Whatever no agent could derive, the host's
   management UI surfaces as missing and lets the owner fill in manually.

## Rules for deriving agents

1. **Observe, don't invent.** Every derived field must trace to something the
   agent actually saw. If uncertain, leave the field empty and report it as a
   gap — a wrong profile is worse than an empty one.
2. **Style lives in memory, marked sensitive.** The full writing-style
   analysis goes to the memory page **`style/writing-profile`** (this path is
   the convention; clients and servers should expect it there), written with
   frontmatter **`sensitivity: sensitive`**. The ability to write in someone's
   voice is impersonation-adjacent: gating style pages behind
   `memory.sensitive:read` keeps them out of the §7.2 default grant, so voice
   access is an explicit, per-client consent decision. Only the distilled
   preferences (tone, verbosity, formatting) go into `profile.communication`.
3. **Core stays core.** Nothing sensitive goes into `profile.core` during
   bootstrap — health, legal, family, residency observations belong in their
   extension namespaces (which require their own write scopes) or nowhere.
4. **Report what's missing.** End by telling the owner which fields could not
   be derived, so the host UI's gap prompts make sense.

## Host obligations

- Track **provenance** per profile field: which actor (owner vs. which
  client) last set it, and when. Owners must be able to see that their
  timezone came from "you" but their languages came from "client:Claude".
- Compute and expose **gaps** (recommended-but-empty fields) so UIs can
  prompt. The recommended baseline set: `name`, `languages`, `timezone`,
  `communication`, `ai_instructions`.
- Provenance is host metadata. It is **not** part of the `profile.core`
  document (whose schema is closed) and is not served to MCP clients.
