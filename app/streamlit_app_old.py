import random

import streamlit as st
import streamlit.components.v1 as components
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
    page_icon="🍽️",
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
# Streamlit's frontend doesn't expose the active theme via a CSS attribute we
# can select on (there is no [data-theme] anywhere in its DOM), so a fixed
# palette written with only light-mode colors would go unreadable in dark
# mode. st.context.theme.type reports the browser's actual active theme
# server-side, so we pick the right palette in Python instead and the CSS
# just uses it directly — no dead selectors, and it updates live if the user
# flips the theme in Streamlit's settings menu.
_theme_type = getattr(st.context.theme, "type", None) or "light"
_is_dark = _theme_type == "dark"

_hero_bg = (
    "linear-gradient(135deg, #9a3412 0%, #7c2d12 100%)"
    if _is_dark
    else "linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%)"
)
_hero_border = "#c2410c" if _is_dark else "#fed7aa"
_hero_text = "#fff7ed" if _is_dark else "#1f2937"

_pill_bg = "rgba(255, 255, 255, 0.14)" if _is_dark else "rgba(255, 255, 255, 0.78)"
_pill_border = "rgba(255, 247, 237, 0.45)" if _is_dark else "#fdba74"
_pill_text = "#fff7ed" if _is_dark else "#1f2937"

_tip_bg = "#141821" if _is_dark else "#ffffff"
_tip_border = "#4b5563" if _is_dark else "#d1d5db"
_tip_text = "#f8fafc" if _is_dark else "#1f2937"
_tip_accent = "#fb923c" if _is_dark else "#f97316"

_status_bg = "#052e16" if _is_dark else "#f0fdf4"
_status_border = "#166534" if _is_dark else "#bbf7d0"
_status_text = "#bbf7d0" if _is_dark else "#14532d"

_credit_text = "#9ca3af" if _is_dark else "#6b7280"
_credit_border = "#374151" if _is_dark else "#e5e7eb"

_card_shadow = "0 6px 18px rgba(0, 0, 0, 0.35)" if _is_dark else "0 6px 16px rgba(31, 41, 55, 0.08)"
_hero_title_gradient = (
    "linear-gradient(135deg, #fed7aa 0%, #fff7ed 100%)"
    if _is_dark
    else "linear-gradient(135deg, #c2410c 0%, #9a3412 100%)"
)

st.markdown(
    f"""
    <style>
    /* Larger base text throughout — easier reading for older eyes */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] li {{
        font-size: 1.15rem;
        line-height: 1.65;
    }}

    .stButton button {{
        font-size: 1.05rem;
    }}

    .main .block-container {{
        max-width: 1050px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }}

    @keyframes fadeSlideIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes heroFadeSlideIn {{
        from {{ opacity: 0; transform: translateY(24px) scale(0.98); }}
        to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}

    .hero {{
        padding: 1.8rem 2rem;
        border-radius: 20px;
        background: {_hero_bg};
        border: 1px solid {_hero_border};
        margin-bottom: 1.5rem;
        color: {_hero_text};
        box-shadow: {_card_shadow};
        animation: heroFadeSlideIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    .hero h1 {{
        margin-bottom: 0.35rem;
        font-size: 2.5rem;
        background: {_hero_title_gradient};
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }}

    .hero p {{
        margin-bottom: 0.4rem;
        font-size: 1.2rem;
    }}

    .hero p {{
        color: {_hero_text} !important;
    }}

    .feature-row {{
        display: flex;
        flex-wrap: nowrap;
        gap: 0.5rem;
        margin-top: 1rem;
        overflow-x: auto;
        padding-bottom: 0.15rem;
    }}

    .feature-pill {{
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        background: {_pill_bg};
        border: 1px solid {_pill_border};
        color: {_pill_text};
        font-size: 0.9rem;
        white-space: nowrap;
    }}

    .section-label {{
        font-size: 1.05rem;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }}

    div[data-testid="stChatMessage"] {{
        border-radius: 16px;
        padding: 0.25rem 0.5rem;
        animation: fadeSlideIn 0.35s ease-out;
    }}

    div[data-testid="stChatInput"] {{
        padding-bottom: 1rem;
    }}

    .creator-credit {{
        text-align: center;
        color: {_credit_text};
        font-size: 0.82rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid {_credit_border};
    }}

    .tip-card {{
        padding: 0.9rem 1rem;
        border-radius: 10px;
        background: {_tip_bg};
        border: 1px solid {_tip_border};
        color: {_tip_text};
        margin-top: 0.75rem;
        box-shadow: {_card_shadow};
    }}

    .tip-card em {{
        color: {_tip_text};
    }}

    .daily-tip {{
        padding: 0.85rem 1rem;
        border-radius: 10px;
        background: {_tip_bg};
        border: 1px solid {_tip_border};
        border-left: 4px solid {_tip_accent};
        color: {_tip_text};
        box-shadow: {_card_shadow};
        font-size: 0.92rem;
        line-height: 1.55;
    }}

    .status-card {{
        padding: 0.65rem 0.8rem;
        border-radius: 12px;
        background: {_status_bg};
        border: 1px solid {_status_border};
        color: {_status_text};
        font-size: 0.9rem;
        box-shadow: {_card_shadow};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Sidebar
# -----------------------------
DAILY_TIPS = [
    "You can ask me to explain any setting step-by-step.",
    "You can record your question instead of typing it — just tap the microphone below.",
    "Tap \"Explain that in more detail\" under an answer for a deeper explanation.",
    "Add this app to your phone's home screen for one-tap access, no need to remember the web address.",
    "I can read my answers aloud — toggle it below if you'd rather just listen.",
]
# A fresh tip is picked every time the script reruns (e.g. asking a question,
# clicking any button) rather than on a JS timer — this avoids needing a
# fixed-height iframe (which was clipping longer tips) and still feels like
# it "rotates" since this app reruns on almost every user interaction.
_daily_tip = random.choice(DAILY_TIPS)

with st.sidebar:
    st.header("🤖 Microwave Assistant")
    st.caption("Your friendly guide to getting the most out of your LG microwave.")

    st.markdown(
        f'<div class="daily-tip">💡 <strong>Did you know?</strong> {_daily_tip}</div>',
        unsafe_allow_html=True,
    )

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
    st.caption("Built with ❤️ by Noel Thomas  \n(with help from Claude Code 😅)")

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
# Display conversation history
# -----------------------------
CHAT_AVATARS = {"assistant": "🍽️"}

for _i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar=CHAT_AVATARS.get(message["role"])):
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

# -----------------------------
# Follow-up suggestion — shown after the latest answer, not above it
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

    with st.chat_message("assistant", avatar=CHAT_AVATARS.get("assistant")):
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
    st.session_state.scroll_to_answer = True

    if succeeded:
        st.session_state.followup_question = get_fun_followup(answer)
        if not st.session_state.get("celebrated_first_answer"):
            st.session_state.celebrated_first_answer = True
            st.balloons()
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
    '<span>Co-created by Claude Code 🦾</span>'
    '</div>',
    unsafe_allow_html=True,
)

# -----------------------------
# Scroll management
# -----------------------------
# Streamlit's built-in auto-scroll-to-bottom (tied to st.chat_input) only
# fires when the user submits through that widget directly — not when a
# question comes from a button (example question, cooking-mode search,
# follow-up, voice input). So on a brand-new session we force scroll-to-top
# (to reveal the hero/welcome section), and right after any question is
# answered we force scroll-to-bottom (to reveal the new answer), regardless
# of which input method triggered it.
if not st.session_state.messages:
    components.html(
        """
        <script>
        function scrollTop() {
            const doc = window.parent.document;
            const main = doc.querySelector('section.stMain');
            if (main) { main.scrollTop = 0; }
            doc.documentElement.scrollTop = 0;
            doc.body.scrollTop = 0;
        }
        [50, 300, 800, 1500, 3000].forEach(t => setTimeout(scrollTop, t));
        </script>
        """,
        height=0,
    )
elif st.session_state.pop("scroll_to_answer", False):
    # Scroll so the question just asked sits at the top of the view, with the
    # answer visible right below it — not scrolled all the way to the bottom,
    # which would hide the start of a long answer above the fold. Streamlit's
    # own built-in scroll-to-bottom (tied to chat_input) wins any one-shot or
    # observer-based race — it seems to re-assert itself at least once after
    # the script finishes, on a schedule we can't hook into. So we keep
    # re-applying our position on a tight interval for several seconds —
    # whenever Streamlit's own scroll fires, our next tick (within 200ms)
    # corrects it back. But that must stop the instant the user actually
    # tries to scroll themselves (wheel/touch/keyboard), or it fights them —
    # only our own programmatic scrollIntoView calls should be ignored.
    components.html(
        """
        <script>
        function scrollToQuestion() {
            const doc = window.parent.document;
            const messages = doc.querySelectorAll('[data-testid="stChatMessage"]');
            if (messages.length === 0) return;
            const idx = messages.length >= 2 ? messages.length - 2 : 0;
            messages[idx].scrollIntoView({ block: "start", behavior: "auto" });
        }
        const mainDoc = window.parent.document;
        const target = mainDoc.querySelector('section.stMain') || mainDoc.body;
        let cancelled = false;
        function cancel() { cancelled = true; }
        target.addEventListener('wheel', cancel, { once: true, passive: true });
        target.addEventListener('touchmove', cancel, { once: true, passive: true });
        target.addEventListener('keydown', cancel, { once: true });
        scrollToQuestion();
        const intervalId = setInterval(() => {
            if (cancelled) { clearInterval(intervalId); return; }
            scrollToQuestion();
        }, 200);
        setTimeout(() => { cancelled = true; clearInterval(intervalId); }, 45000);
        </script>
        """,
        height=0,
    )