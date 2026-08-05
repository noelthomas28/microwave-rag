# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Streamlit chat app ("Ask Your Microwave") that answers questions about an LG microwave using
hybrid RAG (FAISS vector search + BM25 keyword search) over two PDF manuals in `data/`. All
answers are grounded strictly in retrieved manual excerpts — the system prompt forbids the LLM
from using outside knowledge, and a feature-existence check flags/redirects questions about
capabilities the appliance doesn't have.

## Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the app locally (currently deployed UI, via the app/streamlit_app.py shim)
streamlit run app/streamlit_app.py

# Run a specific version directly (bypasses the shim; useful while iterating
# on a not-yet-promoted version) — see "UI versions" below
streamlit run app/streamlit_app_v3.py

# Run an archived (previous) UI, kept for reference/rollback
streamlit run app/archived/streamlit_app_v2.py
streamlit run app/archived/streamlit_app_v1.py

# Run the RAG engine standalone (CLI Q&A loop, no Streamlit)
python app/rag_engine.py
```

There is no lint/test/build tooling configured in this repo (no test suite, no linter config).

Requires `OPENAI_API_KEY` in a `.env` file at the repo root (see `get_secret()` in
`rag_engine.py` — it checks `st.secrets` first for Streamlit Cloud, then falls back to
`.env`/env vars for local dev). An optional `APP_PIN` env var enables a PIN gate in the UI.

## Architecture

- **`app/rag_engine.py`** — the RAG pipeline, usable standalone or imported by every UI version,
  current and archived alike.
- **`app/streamlit_app.py`** — the deployment entry point. Streamlit Community Cloud and
  `.devcontainer/devcontainer.json` both hardcode this literal filename, so it always has to
  exist at this path — its only job is `import streamlit_app_v3`, which runs that module's
  top-level code exactly as if Streamlit had executed it directly. No UI code lives in this file;
  don't add any here. Promoting a new version to production is a one-line change to which module
  it imports (plus the file moves described in "UI versions").
- **`app/streamlit_app_v3.py`** / **`app/theme_v3.py`** / **`app/effects_v3.py`** — the current
  UI's actual code (imported by the shim above). See "UI versions" below.
- **`app/archived/`** — previous UI versions, kept for reference/rollback, no longer imported by
  anything live. See "UI versions" below.

### Indexing (`load_or_build_index`)

On first run (or if `data/faiss_index.bin` / `data/chunks.pkl` are missing or in an old schema),
PDFs in `data/` are loaded **per-page** (`load_pdfs`) so every chunk can carry `{doc, page}`
metadata for citations. Chunking (`create_chunks`) stitches the tail of each page onto the next
page before splitting, so procedures spanning a page break aren't lost — chunks are still tagged
with the page most of their content is on. Chunks are embedded in batches (`create_embeddings`)
and stored in a FAISS `IndexFlatL2`; results are cached to disk (`faiss_index.bin`, `chunks.pkl`).
BM25 is cheap enough to rebuild from chunks every run rather than persisting it.

### Retrieval (`retrieve_chunks`)

Hybrid search: FAISS (vector) and BM25 (keyword) each produce a candidate ranking, fused via
Reciprocal Rank Fusion (`RRF_K = 60`). Tune candidate/result sizes via `CANDIDATE_K` and
`RETRIEVAL_K` at the top of `rag_engine.py`.

### Answering (`answer_question`)

1. Retrieves manual chunks for the query, plus a small separate "capabilities" block (always
   pulled via `CAPABILITIES_QUERY`) listing the appliance's actual modes/accessories — this is
   what lets the LLM suggest a real alternative instead of just refusing when a feature doesn't
   exist.
2. `check_feature_coverage` does a cheap heuristic check: do all of the query's key terms
   (`extract_key_terms`, stopword-filtered) co-occur in a single retrieved chunk? If not, a
   `FEATURE-EXISTENCE WARNING` block is injected into the prompt instructing the model to say the
   feature isn't supported and recommend the closest real mode, rather than inventing a procedure.
3. The prompt also carries standing instructions for two recurring manual patterns: (a)
   synthesizing one general procedure out of steps repeated across several recipes (e.g.
   rotisserie setup), and (b) presenting genuinely different methods for the same goal as
   separate labeled options rather than merging them into one linear procedure.
4. `detail_level="detailed"` (used by the "Explain that in more detail" button) raises
   `RETRIEVAL_K` and swaps in more exhaustive prompt guidance.
5. Returns `{"answer": ..., "sources": [...]}` — sources are the raw retrieved chunks, shown in
   the UI as expandable excerpts with doc/page citations.

### Streamlit UI notes

- `st.context.theme.type` is read server-side to pick light/dark color palettes in Python, since
  Streamlit doesn't expose the active theme as a selectable CSS attribute — custom CSS is
  generated per-request rather than written as a static dark-mode stylesheet.
- Chat history lives in `st.session_state.messages`; each message can carry `sources` and
  generated `audio` (TTS) bytes.
- Voice: `st.audio_input` → `transcribe_audio` (Whisper) → routed through the same
  `pending_question` flow as typed/button input; `synthesize_speech` (TTS) generates read-aloud
  audio for answers, autoplayed once via a `components.html` script injection (Streamlit has no
  native post-rerun autoplay hook).
- Because Streamlit's built-in auto-scroll only fires for direct `st.chat_input` submissions, the
  app injects its own scroll-correction JS for button/voice-triggered questions (see the bottom of
  `streamlit_app_v3.py`, and the equivalent block in each archived version) — scroll-to-top on a
  fresh session, scroll-to-just-above-the-answer after a question is answered, canceling itself if
  the user manually scrolls.
- OpenAI error handling is deliberately mapped to plain-language messages
  (`AuthenticationError`, `RateLimitError` w/ quota vs. rate-limit distinction,
  `APIConnectionError`) since the intended audience is non-technical family members, not
  developers.

## UI versions

Every UI version shares the same backend (`rag_engine.py`) and the same on-disk index cache, so
they all behave identically functionally — only presentation differs. Versions are numbered
(`v1`, `v2`, `v3`, ...) in the order they were built; whichever one is current lives directly
under `app/` and is what `app/streamlit_app.py` (the deployment shim, see "Architecture") imports.
Superseded versions move into `app/archived/` and are no longer imported by anything live —
they're kept only for reference/rollback, and are still directly runnable
(`streamlit run app/archived/streamlit_app_vN.py`) since each carries a small `sys.path` bootstrap
so it can still find `rag_engine.py` up in `app/`.

- **`app/streamlit_app_v3.py`** (current) / **`app/theme_v3.py`** / **`app/effects_v3.py`** — a
  fuller Apple/Google-Antigravity-inspired redesign: a full-bleed hero landing moment, a
  scroll-revealed "capabilities showcase" card grid, an editorial type scale, and a cursor-glow
  (desktop) / tap-ripple + scroll-driven ambient drift (touch) effect scoped to the hero, plus the
  same spotlight effect on the capability cards, cooking-mode card, example-question tiles, and
  feature pills. Preserves every feature of `v2` (PIN gate, sidebar tips/toggles, cooking-mode
  search, voice input, source excerpts, follow-up/detail buttons, scroll-management JS,
  conversation export). Styling comes from three places: `.streamlit/config.toml` (native widget
  colors, the Inter font, button/corner radii), `theme_v3.py`'s `inject_theme_v2(is_dark)`
  (everything `config.toml` can't reach — hero, cards, pills, animations, the glow/reveal CSS;
  function name kept as `inject_theme_v2` from before this renaming pass, harmless), and
  `effects_v3.py`'s `inject_cursor_effects()` / `inject_scroll_reveal()` (the cursor-glow/ripple
  and `IntersectionObserver` scroll-reveal JS, injected via `components.html`). `theme_v3.py`
  intentionally inlines its base color/radius/spacing tokens rather than importing them from
  `app/archived/theme_v2.py` — archived files are frozen snapshots, not a live dependency.
- **`app/archived/streamlit_app_v2.py`** / **`app/archived/theme_v2.py`** — the previous live UI:
  an Apple-inspired redesign (bigger typography, glass-card surfaces, staggered fade-in
  animations, a two-column example-question grid). Styled via `theme_v2.py`'s
  `inject_theme(is_dark)`.
- **`app/archived/streamlit_app_v1.py`** — the original UI, before any redesign. Styles itself
  with an inline `st.markdown(f"""<style>...""")` block computed from `_is_dark`-branched Python
  variables; no separate theme file.

**Note:** `.streamlit/config.toml` applies to any Streamlit app run from this repo, so it subtly
restyles every version (native widget colors/font/radius only) regardless of which one is current.

**Promoting a new version** (e.g. building a `v4`): build it alongside the current version under
`app/` (don't touch the current version's files while iterating), review it, then: move the
outgoing current version's files into `app/archived/` under their `vN` names, fix their imports/
`sys.path` bootstrap the same way `v1`/`v2` were handled, move the new version's files from their
build names into `app/` under the next `vN` name, and update `app/streamlit_app.py`'s single
import line to point at the new version's module. Update this section of CLAUDE.md to match.

## Deployment

Configured for both GitHub Codespaces (`.devcontainer/devcontainer.json`, runs
`streamlit run app/streamlit_app.py`) and Streamlit Community Cloud (secrets via `st.secrets`
instead of `.env`). Both point at the literal filename `app/streamlit_app.py`, which is a thin
shim that never changes — promoting a UI version to production only ever means editing that one
import line (see "UI versions"), never touching deployment config.

## Data

`data/*.pdf` (the manuals) are gitignored — only the derived `faiss_index.bin` and `chunks.pkl`
are committed. If you add/change PDFs, delete `data/faiss_index.bin` and `data/chunks.pkl` (or
just `chunks.pkl`, since `load_or_build_index` detects a schema mismatch) to force a rebuild.
