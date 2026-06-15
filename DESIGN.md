# Daimon - Design System (UI contract)

> The visual language for the Daimon UI: a single `gr.Blocks` app in `app/blocks_ui.py`,
> mounted at `/` (the `offbrand-frontend` persona owns this file). Dark theme, three columns,
> everything bound to real `state.json` / audit data.

---

## 1. Principles

1. **Show the cage.** Every governed trait (L3, L5) is drawn as a bar against its envelope
   `[min, max]`, with a tick for its declared baseline. The boundary is the point: the persona
   moves freely, but never past the wall.
2. **Truth over spectacle.** Every number and every audit line binds to real `state.json` /
   `mutation_log`. Never show a mutation, clamp, or rejection that did not happen.
3. **The rejection is the climax.** The governance demo (identity-change attempt blocked,
   envelope overflow clamped) must be the most visually distinct event on screen.
4. **One accent for life/governance, one for danger.** Restraint everywhere else.

---

## 2. Color tokens

Defined once in `CUSTOM_CSS` (`app/blocks_ui.py`); don't hardcode hex elsewhere.

| Role | Token | Value | Use |
|---|---|---|---|
| Background | `--bg` | `#0a0a10` | Page background |
| Panel | `--panel` / `--panel-2` | `#14141f` / `#191926` | Cards, chat, panels |
| Border | `--panel-border` | `rgba(255,255,255,0.08)` | Card and bar borders |
| Text | `--ink` / `--ink-dim` | `#f1f0f7` / `#908dab` | Primary / muted text |
| **Accent** | `--accent` | `#8c7bf6` | Bar fill, governance-controlled badge |
| **Baseline** | `--baseline` | `#4fd1c5` | Baseline tick on bars |
| **Caution** | `--clamp` | `#f0a93a` | A delta that hit the envelope wall (clamped) |
| **Danger** | `--block` | `#f06a6a` | Governance-blocked mutation, human-approval badge |

---

## 3. Layout

One screen, three columns side by side, each scrolling independently (the page itself does
not scroll):

```
+----------------------------------------------------------------+
| # Daimon - Governed, self-evolving local AI persona            |
+------------------+---------------------------+-----------------+
| ## Talk to Daimon | ## State vector - 10 layers | ## PERSONA.md |
|                   |                              | - live persona|
| gr.Chatbot        | 10 layer cards:              |               |
| (streaming, via   |  - L1/L2/L4/L6-L10: read-only| ## Audit log  |
|  loop.step_stream)|  - L3/L5: bars [min..max] +  |               |
|                   |    baseline tick + GitHub-   | ## Governance |
| textbox + send    |    style diffs (- before /   | demo          |
|                   |    + after) for recent edits |  [Run] button |
+------------------+---------------------------+-----------------+
```

- **Layer cards** carry a badge: human approval required / governance controlled / review
  required, matching `personaxis.md`'s edit policy per layer.
- **Audit log**: append-only diff blocks, newest last. A clamped delta gets the `--clamp`
  border; a blocked mutation gets `--block`.
- **Governance demo**: two real checks against the spec engine (`engine/governance_demo.py`,
  no model needed) - an identity-change attempt (blocked) and an envelope overflow (clamped),
  then a reset to baseline.

---

## 4. Typography

- UI text: system sans (Gradio default).
- Data/log/values: monospace (`--mono`, `"Roboto Mono"`).
- No serif, no extra display faces.

---

## 5. Do / Don't

**Do**
- Draw L3/L5 traits against their declared envelope and baseline.
- Make the governance rejection visually distinct (`--block`).
- Bind all visuals to real `state.json` / `mutation_log` / `PERSONA.md`.
- Keep each of the three columns independently scrollable; the page itself never scrolls.

**Don't**
- Don't fake a mutation, clamp, or rejection.
- Don't add gradients, glows, or colors beyond the tokens above.
- Don't claim the persona is conscious; it is a functional state model.
