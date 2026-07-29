"""
Appliance Assistant
RAG + OpenAI + FAISS + BM25 (hybrid retrieval)

Author: Noel Thomas

Purpose:
- Load appliance manuals from PDF (tracking document + page for every chunk)
- Build a vector database (FAISS) AND a keyword index (BM25) over the manuals
- Retrieve relevant manual sections using hybrid search
- Answer user questions about appliance operation, with citations
"""

import os
from pathlib import Path
import pickle
import re

import faiss
import numpy as np

from dotenv import load_dotenv
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from rank_bm25 import BM25Okapi

# ============================================================
# CONFIGURATION
# ============================================================

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
PAGE_STITCH_OVERLAP = 150  # chars of prior page carried forward so cross-page procedures aren't lost
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"
EMBED_BATCH_SIZE = 100
RETRIEVAL_K = 8            # final number of chunks sent to the LLM (raised from 6 so
                            # multi-example synthesis, e.g. rotisserie install + several
                            # recipes, has room to bring in more than one supporting chunk)
CANDIDATE_K = 20           # how many candidates each retriever pulls before fusion
RRF_K = 60                 # standard Reciprocal Rank Fusion smoothing constant

# A small, always-included reference block listing what modes/accessories this
# appliance actually has. This is what lets the LLM recommend a real alternative
# ("try Grill or Charcoal/Indian Cuisine instead") rather than just refusing.
CAPABILITIES_QUERY = (
    "cooking mode list: grill convection combination auto cook healthy heart "
    "diet fry charcoal indian cuisine roti basket ghee steam clean rotisserie"
)
CAPABILITIES_K = 5

# Generic words to ignore when checking whether the user's actual subject
# (e.g. "smoking") shows up anywhere in what was retrieved.
STOPWORDS = {
    "how", "do", "does", "i", "use", "the", "a", "an", "to", "for", "of", "on",
    "in", "is", "are", "can", "what", "my", "with", "and", "or", "it", "this",
    "that", "perform", "operation", "function", "mode", "microwave", "oven",
}

DATA_DIR = Path("data")
INDEX_FILE = DATA_DIR / "faiss_index.bin"
CHUNKS_FILE = DATA_DIR / "chunks.pkl"

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

# Resolves .env relative to this file, so it works on any machine/path
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _get_openai_api_key():
    """Prefer Streamlit Cloud's secrets store; fall back to the .env-loaded
    environment variable for local development."""
    try:
        import streamlit as st
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return os.getenv("OPENAI_API_KEY")


client = OpenAI(api_key=_get_openai_api_key())

# ============================================================
# READ PDF FILES (per-page, with metadata)
# ============================================================

def load_pdfs():
    """
    Load all PDF manuals in the data directory.

    Returns a list of page records:
        [{"doc": "LG Microwave Owner's Manual.pdf", "page": 15, "text": "..."}, ...]

    Keeping this per-page (instead of one giant concatenated string) is what
    lets every downstream chunk carry accurate document + page metadata.
    """
    pdf_files = sorted(DATA_DIR.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError("No PDF files found in the data directory.")

    pages = []

    for pdf_file in pdf_files:
        print(f"Loading {pdf_file.name}...")
        reader = PdfReader(pdf_file)
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append({
                "doc": pdf_file.name,
                "page": page_num,
                "text": page_text,
            })

    return pages

# ============================================================
# CHUNKING (per document, page-aware, with cross-page overlap)
# ============================================================

def create_chunks(pages):
    """
    Splits page text into chunks while keeping {doc, page} metadata attached
    to every chunk.

    To avoid losing procedures that span a page break, each page's text is
    prefixed with the tail end of the previous page (same document only)
    before splitting. The chunk is still tagged with the *current* page,
    since that's where most of its content lives.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )

    chunks = []
    prev_doc = None
    prev_tail = ""

    for record in pages:
        doc, page, text = record["doc"], record["page"], record["text"]

        if doc != prev_doc:
            prev_tail = ""  # don't leak context across different manuals

        stitched_text = f"{prev_tail}\n{text}" if prev_tail else text

        for piece in splitter.split_text(stitched_text):
            piece = piece.strip()
            if piece:
                chunks.append({"doc": doc, "page": page, "text": piece})

        prev_tail = text[-PAGE_STITCH_OVERLAP:] if text else ""
        prev_doc = doc

    return chunks

# ============================================================
# EMBEDDINGS (batched)
# ============================================================

def create_embeddings(chunks):
    """Embeds chunk text in batches instead of one API call per chunk."""
    texts = [c["text"] for c in chunks]
    embeddings = []

    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i:i + EMBED_BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        embeddings.extend([item.embedding for item in response.data])
        print(f"Embedded {min(i + EMBED_BATCH_SIZE, len(texts))}/{len(texts)} chunks")

    return embeddings

# ============================================================
# VECTOR DATABASE
# ============================================================

def build_faiss_index(embeddings):
    dimension = len(embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype("float32"))
    return index

# ============================================================
# KEYWORD INDEX (BM25)
# ============================================================

def _tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())

def build_bm25_index(chunks):
    tokenized_corpus = [_tokenize(c["text"]) for c in chunks]
    return BM25Okapi(tokenized_corpus)

# ============================================================
# LIGHTWEIGHT FEATURE-EXISTENCE CHECK
# ============================================================

def extract_key_terms(query):
    """Pulls out the likely 'subject' words from a question, e.g. 'smoking'
    out of 'how do I perform the smoking operation?'. This is intentionally
    simple (stopword removal, no NLP model) — it's a heuristic, not a source
    of truth."""
    words = _tokenize(query)
    return [w for w in words if w not in STOPWORDS and len(w) > 3]


def check_feature_coverage(key_terms, retrieved_chunk_texts):
    """
    Returns True (flag as likely unsupported) unless at least one retrieved
    chunk contains ALL of the query's key terms together.

    This is stricter than checking the pooled context as a whole: a common
    word like "fruit" showing up in some unrelated recipe chunk shouldn't be
    enough to "clear" a query about fruit dehydration if no chunk actually
    connects "dehydrate" and "fruit" in the same place. Requiring co-occurrence
    within a single chunk catches that gap.

    For single-term queries (the common case — "smoking", "rotisserie") this
    behaves the same as before: is the term present anywhere.
    """
    if not key_terms:
        return False

    for chunk_text in retrieved_chunk_texts:
        chunk_lower = chunk_text.lower()
        stems = [term[:5] for term in key_terms]
        if all(stem in chunk_lower for stem in stems):
            return False

    return True

# ============================================================
# QUERY EMBEDDING
# ============================================================

def get_query_embedding(query):
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=query)
    return response.data[0].embedding

# ============================================================
# HYBRID RETRIEVAL (FAISS + BM25, fused with Reciprocal Rank Fusion)
# ============================================================

def retrieve_chunks(query, chunks, faiss_index, bm25_index, k=RETRIEVAL_K):
    # --- Vector search ---
    query_embedding = get_query_embedding(query)
    query_vector = np.array([query_embedding]).astype("float32")
    _, faiss_indices = faiss_index.search(query_vector, min(CANDIDATE_K, len(chunks)))
    vector_ranking = [int(i) for i in faiss_indices[0] if i != -1]

    # --- Keyword search ---
    bm25_scores = bm25_index.get_scores(_tokenize(query))
    keyword_ranking = list(np.argsort(bm25_scores)[::-1][:CANDIDATE_K])

    # --- Reciprocal Rank Fusion ---
    fused_scores = {}
    for rank, idx in enumerate(vector_ranking):
        fused_scores[idx] = fused_scores.get(idx, 0) + 1 / (RRF_K + rank)
    for rank, idx in enumerate(keyword_ranking):
        fused_scores[idx] = fused_scores.get(idx, 0) + 1 / (RRF_K + rank)

    top_indices = sorted(fused_scores, key=fused_scores.get, reverse=True)[:k]

    return [chunks[i] for i in top_indices]

# ============================================================
# LLM REASONING
# ============================================================

def _format_context(retrieved):
    blocks = [f"[Source: {c['doc']}, Page {c['page']}]\n{c['text']}" for c in retrieved]
    return "\n\n---\n\n".join(blocks)


def answer_question(query, chunks, faiss_index, bm25_index):
    retrieved = retrieve_chunks(query, chunks, faiss_index, bm25_index)

    # Always pull a small reference block naming the appliance's actual modes/
    # accessories, deduplicated against the main retrieval. This is what lets
    # the model recommend a *real* alternative when the asked-about feature
    # doesn't exist, instead of just refusing.
    capability_chunks = retrieve_chunks(
        CAPABILITIES_QUERY, chunks, faiss_index, bm25_index, k=CAPABILITIES_K
    )
    seen = {(c["doc"], c["page"], c["text"]) for c in retrieved}
    capability_chunks = [
        c for c in capability_chunks if (c["doc"], c["page"], c["text"]) not in seen
    ]

    manual_context = _format_context(retrieved)
    capabilities_context = _format_context(capability_chunks) if capability_chunks else "(none)"

    key_terms = extract_key_terms(query)
    all_retrieved_texts = [c["text"] for c in retrieved] + [c["text"] for c in capability_chunks]
    likely_unsupported = check_feature_coverage(key_terms, all_retrieved_texts)

    if likely_unsupported:
        feature_guidance = f"""
FEATURE-EXISTENCE WARNING:
No single retrieved excerpt below contains all of the question's key subject terms
({", ".join(key_terms)}) together. Individual terms may appear elsewhere out of context
(e.g. a generic ingredient mentioned in an unrelated recipe) — that does NOT count as
support. This is a strong signal the appliance does NOT have this specific feature — do
not invent, infer, or approximate a procedure for it just because it sounds plausible,
and do not stretch an unrelated feature to cover it just because the terminology sounds
similar.

Instead:
1. Clearly and directly state that this feature is not available on this microwave,
   based on the manual.
2. Recommend the closest available mode(s) from the AVAILABLE MODES REFERENCE (for
   example Grill or Charcoal/Indian Cuisine, whichever is genuinely closest), and give
   their real step-by-step operating instructions using the manual content provided.
"""
    else:
        feature_guidance = """
The question's subject appears to be covered somewhere in the manual context below.
Answer normally, following the synthesis guidance above.
"""

    prompt = f"""
You are an expert LG appliance assistant.

Answer ONLY using the information provided in the MANUAL CONTEXT and AVAILABLE MODES
REFERENCE below. Never rely on outside/general knowledge about microwaves.

SYNTHESIZING GENERAL PROCEDURES:
Some features (e.g. accessories like the rotisserie) don't have one single "how to" section
— instead they're described once in a general installation/setup section, and then referenced
again inside several individual recipes that each restate part of the procedure. When you see
this pattern, combine the setup/installation steps with the operating steps that repeat across
those recipes (e.g. "assemble," "insert into the oven," "select category and press start")
into ONE general step-by-step procedure. Do NOT pull recipe-specific ingredients, quantities,
or seasonings into that general procedure — only include steps about operating the appliance
itself.

HANDLING MULTIPLE VALID METHODS:
Sometimes a question (e.g. "what's the best way to cook chicken?") could be answered by
several different recipes that use genuinely different equipment or techniques (for example,
one recipe uses the rotisserie, another uses a tawa on a rack). These are NOT the same feature
described in multiple places — they are separate, mutually exclusive methods. Do not merge
their steps into a single linear numbered procedure, since that misleadingly implies they're
sequential parts of one process. Instead, present each distinct method as its own clearly
labeled option (e.g. "Option A — Using the Rotisserie:" / "Option B — Using a Tawa:"), each
with its own short step list, so the reader can pick one.

{feature_guidance}

Be concise but complete. Mention any safety warnings. Cite the source document and page
number for each key fact, using the [Source: ..., Page ...] labels provided in the context.

MANUAL CONTEXT:

{manual_context}

AVAILABLE MODES REFERENCE:

{capabilities_context}

QUESTION:

{query}
"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content

# ============================================================
# INDEX BUILD / LOAD
# ============================================================

def load_or_build_index():
    cache_is_valid = False

    if INDEX_FILE.exists() and CHUNKS_FILE.exists():
        print("Found existing index files, checking compatibility...")
        with open(CHUNKS_FILE, "rb") as f:
            chunks = pickle.load(f)

        # The chunk schema changed from plain strings to {"doc","page","text"}
        # dicts. If an old-format cache is loaded, every downstream function
        # that does c["text"] / c["doc"] will crash with a cryptic TypeError.
        # Detect that up front and rebuild instead of failing.
        if chunks and isinstance(chunks[0], dict) and "text" in chunks[0]:
            cache_is_valid = True
        else:
            print(
                "Cached chunks.pkl is in an old/incompatible format "
                "(expected dicts with 'doc'/'page'/'text'). Rebuilding index..."
            )

    if cache_is_valid:
        print("Loading existing FAISS index...")
        faiss_index = faiss.read_index(str(INDEX_FILE))
    else:
        print("Building index from scratch...")

        pages = load_pdfs()
        chunks = create_chunks(pages)
        print(f"Created {len(chunks)} chunks")

        embeddings = create_embeddings(chunks)
        faiss_index = build_faiss_index(embeddings)

        faiss.write_index(faiss_index, str(INDEX_FILE))
        with open(CHUNKS_FILE, "wb") as f:
            pickle.dump(chunks, f)

        print("Index saved successfully.")

    bm25_index = build_bm25_index(chunks)  # cheap to rebuild, not persisted
    return faiss_index, bm25_index, chunks

EXIT_COMMANDS = {"exit", "quit", "q"}


def main():
    faiss_index, bm25_index, chunks = load_or_build_index()

    print("\nSystem ready.")
    print("Ask a question about the microwave, or type 'exit' to quit.\n")

    while True:
        query = input("Ask a question (or 'exit' to quit): ").strip()

        if not query:
            continue  # don't waste an API call on an empty Enter press

        if query.lower() in EXIT_COMMANDS:
            print("\nGoodbye!")
            break

        answer = answer_question(
            query=query,
            chunks=chunks,
            faiss_index=faiss_index,
            bm25_index=bm25_index,
        )

        print("\n========================")
        print("ANSWER")
        print("========================\n")
        print(answer)
        print()  # blank line before the next prompt, for readability


if __name__ == "__main__":
    main()
