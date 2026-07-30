import streamlit as st
from openai import APIConnectionError, AuthenticationError, RateLimitError

from rag_engine import (
    load_or_build_index,
    answer_question,
    get_secret,
    transcribe_audio,
    synthesize_speech,
)

st.set_page_config(
    page_title="Ask Your Microwave",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Optional PIN gate (set APP_PIN as a secret/env var to enable)
# -----------------------------
APP_PIN = get_secret("APP_PIN")

if APP_PIN and not st.session_state.get("authenticated"):
    st.title("🔒 Ask Your Microwave")
    st.caption("Enter the family PIN to continue.")
    pin_attempt = st.text_input("PIN", type="password", key="pin_attempt")
    if st.button("Enter", use_container_width=True):
        if pin_attempt == str(APP_PIN):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect PIN, please try again.")
    st.stop()

# -----------------------------
# Custom styling
# -----------------------------
st.markdown(
    """
    <style>
    /* Larger base text throughout — easier reading for older eyes */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] li {
        font-size: 1.15rem;
        line-height: 1.65;
    }

    .stButton button {
        font-size: 1.05rem;
    }

    .main .block-container {
        max-width: 1050px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        padding: 1.8rem 2rem;
        border-radius: 20px;
        background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
        border: 1px solid #fed7aa;
        margin-bottom: 1.5rem;
        color: #1f2937;
    }

    .hero h1 {
        margin-bottom: 0.35rem;
        font-size: 2.5rem;
    }

    .hero p {
        margin-bottom: 0.4rem;
        font-size: 1.2rem;
    }

    .hero h1,
    .hero p {
        color: #1f2937 !important;
    }

    .feature-row {
        display: flex;
        flex-wrap: nowrap;
        gap: 0.5rem;
        margin-top: 1rem;
        overflow-x: auto;
        padding-bottom: 0.15rem;
    }

    .feature-pill {
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid #fdba74;
        color: #1f2937;
        font-size: 0.9rem;
        white-space: nowrap;
    }

    .section-label {
        font-size: 1.05rem;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 16px;
        padding: 0.25rem 0.5rem;
    }

    div[data-testid="stChatInput"] {
        padding-bottom: 1rem;
    }

    .creator-credit {
        text-align: center;
        color: #6b7280;
        font-size: 0.82rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
    }

    .tip-card {
        padding: 0.9rem 1rem;
        border-radius: 10px;
        background: #ffffff;
        border: 1px solid #d1d5db;
        color: #1f2937;
        margin-top: 0.75rem;
    }

    .tip-card em {
        color: #1f2937;
    }

    [data-theme="dark"] .hero {
        background: linear-gradient(135deg, #9a3412 0%, #7c2d12 100%);
        border-color: #c2410c;
        color: #fff7ed;
    }

    [data-theme="dark"] .hero h1,
    [data-theme="dark"] .hero p {
        color: #fff7ed !important;
    }

    [data-theme="dark"] .feature-pill {
        background: rgba(255, 255, 255, 0.14);
        border-color: rgba(255, 247, 237, 0.45);
        color: #fff7ed;
    }

    [data-theme="dark"] .tip-card {
        background: #141821;
        border-color: #4b5563;
        color: #f8fafc;
    }

    [data-theme="dark"] .tip-card em {
        color: #f8fafc;
    }

    .status-card {
        padding: 0.65rem 0.8rem;
        border-radius: 12px;
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("🤖 Microwave Assistant")
    st.caption("Your friendly guide to getting the most out of your LG microwave.")

    st.divider()

    if st.button("🔄 Start a New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.toggle("🔊 Read answers aloud", value=True, key="read_aloud")

    st.divider()

    with st.expander("📱 Add this to your phone's home screen"):
        st.markdown(
            """
            **iPhone (Safari):** tap the Share icon, then
            "Add to Home Screen".

            **Android (Chrome):** tap the ⋮ menu, then
            "Add to Home screen".

            Then you can open it like any other app — no need to
            remember the web address.
            """
        )

    st.divider()

    st.subheader("📖 What I can help with")
    st.markdown(
        """
        - 🔥 Smoking
        - 🍗 Rotisserie
        - 🍕 Cooking modes
        - 🍞 Baking
        - 🧼 Cleaning
        - ⚠️ Safety and accessories
        """
    )

    st.divider()
    st.caption("Answers are based on the LG microwave manuals provided to this assistant.")

    st.divider()
    st.subheader("✨ Little extras")
    st.markdown(
        """
        - 💡 Ask follow-up questions naturally
        - 🧠 Ask me to explain a setting step-by-step
        - 🍽️ Ask how to cook a specific food
        - 🍰 Ask about baking and baking modes
        - 🛡️ Ask about safety before trying something new
        """
    )

    st.markdown(
        '<div class="status-card">🟢 <strong>Manual-powered</strong><br>'
        'My answers come from your microwave manuals.</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption("Built with ❤️ by Noel Thomas  \n(with help from ChatGPT and Claude 😅)")

# -----------------------------
# Load RAG system
# -----------------------------
@st.cache_resource
def load_system():
    return load_or_build_index()

faiss_index, bm25_index, chunks = load_system()

# -----------------------------
# Initialize chat history
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------
# Hero / welcome section
# -----------------------------
st.markdown(
    """
    <div class="hero">
        <h1>🤖 Ask Your Microwave</h1>
        <p><strong>Your friendly guide to your LG microwave.</strong></p>
        <p>Ask questions in plain English about cooking functions, settings, accessories, cleaning, and safety.</p>
        <div class="feature-row">
            <span class="feature-pill">🔥 Smoking</span><span class="feature-pill">🍗 Rotisserie</span><span class="feature-pill">🍕 Cooking</span><span class="feature-pill">🍞 Baking</span><span class="feature-pill">🧼 Cleaning & Safety</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Welcome message when chat is empty
# -----------------------------
if not st.session_state.messages:

    example_questions = [
        "👨‍🍳 What are you cooking?",
        "🍞 How can I bake a cake in this microwave?",
        "🔥 How do I use the smoking function?",
        "🥘 How do I cook paneer?",
        "🍗 How do I use the rotisserie?",
        "🍕 How do I cook frozen pizza?",
        "🧼 How do I clean the microwave?",
    ]

    st.markdown('<div class="section-label">👨‍🍳 Cooking Mode</div>', unsafe_allow_html=True)
    st.caption("Tell me what you're cooking, and I'll help you find a suitable method from the manual.")

    cooking_food = st.text_input(
        "What are you cooking?",
        placeholder="e.g., chicken breast, paneer, frozen pizza...",
        key="cooking_food",
    )

    if st.button("🍳 Find a Cooking Method", use_container_width=True):
        if cooking_food.strip():
            st.session_state.pending_question = (
                f"I am cooking {cooking_food.strip()}. What cooking method from the microwave manual would you recommend, and how should I use it?"
            )
            st.rerun()

    st.markdown('<div class="section-label">💬 Try asking me...</div>', unsafe_allow_html=True)

    for question in example_questions[1:]:
        if st.button(question, use_container_width=True):
            st.session_state.pending_question = question.split(" ", 1)[1]
            st.rerun()

    st.markdown('<div class="section-label">💡 Not sure what to ask?</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tip-card">Try asking: <em>"I have chicken breast. What cooking method from the manual should I use?"</em></div>',
        unsafe_allow_html=True,
    )

# -----------------------------
# Follow-up suggestion
# -----------------------------
if "followup_question" in st.session_state and st.session_state.messages:
    followup = st.session_state.followup_question
    if st.button(f"💬 Ask a follow-up: {followup}", use_container_width=True):
        st.session_state.pending_question = followup.split(" ", 1)[1]
        del st.session_state.followup_question
        st.rerun()

_last_assistant_msg = next(
    (m for m in reversed(st.session_state.messages)
     if m["role"] == "assistant" and m.get("question")),
    None,
)
if _last_assistant_msg:
    if st.button("📖 Explain that in more detail", use_container_width=True):
        st.session_state.pending_detail_question = _last_assistant_msg["question"]
        st.rerun()

# -----------------------------
# Display conversation history
# -----------------------------
for _i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("📄 Show manual excerpts used"):
                for src in message["sources"]:
                    st.markdown(f"**{src['doc']}, page {src['page']}**")
                    st.caption(src["text"])
        if message.get("audio"):
            is_latest = _i == len(st.session_state.messages) - 1
            autoplay = is_latest and st.session_state.get("autoplay_last_audio", False)
            st.audio(message["audio"], format="audio/mp3", autoplay=autoplay)

# Audio should only autoplay once, right after it's generated — not on every
# later rerun (e.g. clicking an unrelated button would otherwise replay it).
st.session_state.autoplay_last_audio = False

def get_fun_followup(answer_text):
    """Return a light follow-up suggestion based on the assistant's answer."""
    answer_lower = answer_text.lower()
    if "smok" in answer_lower:
        return "🔥 What foods can I smoke in this microwave?"
    if "rotisserie" in answer_lower:
        return "🍗 What accessories do I need for the rotisserie?"
    if "clean" in answer_lower:
        return "🧼 How often should I clean it?"
    if "safety" in answer_lower or "warning" in answer_lower:
        return "⚠️ What are the most important safety rules?"
    return "💡 What else can I do with this microwave?"

# -----------------------------
# Handle example question selection
# -----------------------------
pending_question = st.session_state.pop("pending_question", None)
pending_detail_question = st.session_state.pop("pending_detail_question", None)

# -----------------------------
# Voice input
# -----------------------------
if "audio_key_counter" not in st.session_state:
    st.session_state.audio_key_counter = 0

st.markdown('<div class="section-label">🎤 Or ask by voice</div>', unsafe_allow_html=True)
audio_value = st.audio_input(
    "Record your question",
    label_visibility="collapsed",
    key=f"audio_input_{st.session_state.audio_key_counter}",
)

if audio_value is not None:
    with st.spinner("🎤 Transcribing..."):
        try:
            transcribed = transcribe_audio(audio_value)
        except Exception:
            transcribed = None

    st.session_state.audio_key_counter += 1  # clear the recorder after one attempt

    if transcribed and transcribed.strip():
        st.session_state.pending_question = transcribed.strip()
        st.rerun()
    else:
        st.error("Sorry, I couldn't understand that recording. Please try again or type your question.")

# -----------------------------
# Chat input
# -----------------------------
typed_prompt = st.chat_input(
    "Ask anything about your LG microwave..."
)

detail_level = "normal"
query_for_engine = None

if pending_detail_question:
    prompt = "🔍 Please explain that in more detail."
    detail_level = "detailed"
    query_for_engine = pending_detail_question
elif pending_question:
    prompt = pending_question
    query_for_engine = pending_question
elif typed_prompt:
    prompt = typed_prompt
    query_for_engine = typed_prompt
else:
    prompt = None

# -----------------------------
# Process question
# -----------------------------
if prompt:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    sources = []
    succeeded = False
    audio_bytes = None

    with st.chat_message("assistant"):
        with st.spinner("🔎 Searching the manuals..."):
            try:
                result = answer_question(
                    query=query_for_engine,
                    chunks=chunks,
                    faiss_index=faiss_index,
                    bm25_index=bm25_index,
                    detail_level=detail_level,
                )
                answer = result["answer"]
                sources = result["sources"]
                succeeded = True
                st.markdown(answer)

                if sources:
                    with st.expander("📄 Show manual excerpts used"):
                        for src in sources:
                            st.markdown(f"**{src['doc']}, page {src['page']}**")
                            st.caption(src["text"])

                # Generated here (not played here) so it's only synthesized once;
                # it's rendered with autoplay after the rerun below, since a widget
                # created in this transient render would be torn down before the
                # audio could actually finish (or even start) playing.
                if st.session_state.get("read_aloud", True):
                    try:
                        audio_bytes = synthesize_speech(answer)
                    except Exception:
                        audio_bytes = None

            except AuthenticationError:
                answer = (
                    "I'm having trouble reaching the AI service — there seems to be a "
                    "problem with the app's API key. Noel needs to check the app settings."
                )
                st.error(answer)
            except RateLimitError as e:
                if "insufficient_quota" in str(e).lower():
                    answer = (
                        "The assistant has run out of its OpenAI credits for now. "
                        "Noel needs to add more credit before it can answer again."
                    )
                else:
                    answer = (
                        "The assistant is getting too many requests right now. "
                        "Please wait a minute and try again."
                    )
                st.error(answer)
            except APIConnectionError:
                answer = (
                    "I couldn't connect to the AI service — this is usually a temporary "
                    "network hiccup. Please try again in a moment."
                )
                st.error(answer)
            except Exception as e:
                answer = (
                    "I'm sorry, I ran into a problem while searching the microwave manuals. "
                    "Please try asking your question again."
                )
                st.error(answer)
                st.caption(f"Technical details: {e}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "question": query_for_engine,
            "sources": sources,
            "audio": audio_bytes,
        }
    )

    st.session_state.autoplay_last_audio = audio_bytes is not None

    if succeeded:
        st.session_state.followup_question = get_fun_followup(answer)
    st.rerun()

# -----------------------------
# Creator credit
# -----------------------------
# -----------------------------
# Conversation export
# -----------------------------
if st.session_state.messages:
    conversation_text = "\n\n".join(
        f"{message['role'].capitalize()}: {message['content']}"
        for message in st.session_state.messages
    )

    with st.expander("📋 Save this conversation"):
        st.caption("You can copy the conversation below and save it anywhere you like.")
        st.code(conversation_text, language=None)

st.markdown(
    '<div class="creator-credit">'
    '🤖 <strong>Ask Your Microwave</strong> · Powered by your LG microwave manuals<br>'
    'Created by Noel Thomas ✌🏽<br>'
    '<span>Co-created by ChatGPT 🧠 and Claude 🦾</span>'
    '</div>',
    unsafe_allow_html=True,
)