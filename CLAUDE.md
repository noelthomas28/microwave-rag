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

# Run the app locally (redesigned UI, currently deployed)
streamlit run app/streamlit_app.py

# Run the previous UI (kept for reference/rollback — see UI versions below)
streamlit run app/streamlit_app_old.py

# Run the RAG engine standalone (CLI Q&A loop, no Streamlit)
python app/rag_engine.py
```

There is no lint/test/build tooling configured in this repo (no test suite, no linter config).

Requires `OPENAI_API_KEY` in a `.env` file at the repo root (see `get_secret()` in
`rag_engine.py` — it checks `st.secrets` first for Streamlit Cloud, then falls back to
`.env`/env vars for local dev). An optional `APP_PIN` env var enables a PIN gate in the UI.

## Architecture

- **`app/rag_engine.py`** — the RAG pipeline, usable standalone or imported by either UI.
- **`app/streamlit_app.py`** / **`app/theme.py`** — the current, deployed Streamlit UI (an
  Apple-inspired redesign), imports functions from `rag_engine.py`. Styling lives in `theme.py`
  plus `.streamlit/config.toml`, not inline in this file.
- **`app/streamlit_app_old.py`** — the previous UI, kept for reference/rollback. Has its own
  inline CSS (does not use `theme.py`). See "UI versions" below.

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
  app injects its own scroll-correction JS for button/voice-triggered questions (see the bottom
  of `streamlit_app.py`/`streamlit_app_old.py`) — scroll-to-top on a fresh session,
  scroll-to-just-above-the-answer after a question is answered, canceling itself if the user
  manually scrolls.
- OpenAI error handling is deliberately mapped to plain-language messages
  (`AuthenticationError`, `RateLimitError` w/ quota vs. rate-limit distinction,
  `APIConnectionError`) since the intended audience is non-technical family members, not
  developers.

## UI versions

There are two Streamlit UIs sharing the same backend (`rag_engine.py`) and the same on-disk index
cache, so both behave identically functionally — only presentation differs:

- **`app/streamlit_app.py`** — the current, deployed UI: an Apple-inspired redesign (bigger
  typography, glass-card surfaces, staggered fade-in animations, a two-column example-question
  grid). Preserves every feature of the previous UI (PIN gate, sidebar tips/toggles, cooking-mode
  search, voice input, source excerpts, follow-up/detail buttons, scroll-management JS,
  conversation export). Its styling comes from two places: `.streamlit/config.toml` (native
  widget colors, the Inter font, button/corner radii — via `[theme.light]`/`[theme.dark]` blocks)
  and `app/theme.py`'s `inject_theme(is_dark)` (everything `config.toml` can't reach: the hero,
  glass cards, pills, chat bubbles, animations), called once near the top of the file.
  **Note:** `.streamlit/config.toml` applies to any Streamlit app run from this repo, so it will
  also subtly restyle `streamlit_app_old.py` (native widget colors/font/radius only — none of
  `theme.py`'s custom CSS, since that's only invoked from `streamlit_app.py`).
- **`app/streamlit_app_old.py`** — the previous UI, kept around for reference/rollback. Styles
  itself with an inline `st.markdown(f"""<style>...""")` block computed from `_is_dark`-branched
  Python variables; does not import `theme.py`.

This UI was originally built as `app/streamlit_app_v2.py` alongside the (then-current)
`app/streamlit_app.py`, reviewed, and then promoted by renaming: the old file became
`streamlit_app_old.py` and the new one took over the `streamlit_app.py` name. This was done
specifically so that `.devcontainer/devcontainer.json` and the Streamlit Community Cloud
deployment (both of which reference the literal filename `app/streamlit_app.py`) would pick up
the new UI without needing their own config changed.

## Deployment

Configured for both GitHub Codespaces (`.devcontainer/devcontainer.json`, runs
`streamlit run app/streamlit_app.py`) and Streamlit Community Cloud (secrets via `st.secrets`
instead of `.env`). Both point at the literal filename `app/streamlit_app.py`, so which UI is
"deployed" is determined entirely by which file currently has that name (see "UI versions").

## Data

`data/*.pdf` (the manuals) are gitignored — only the derived `faiss_index.bin` and `chunks.pkl`
are committed. If you add/change PDFs, delete `data/faiss_index.bin` and `data/chunks.pkl` (or
just `chunks.pkl`, since `load_or_build_index` detects a schema mismatch) to force a rebuild.
