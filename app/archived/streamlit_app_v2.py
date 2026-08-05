import random
import sys
from pathlib import Path

# Archived UI: kept for reference/rollback (see CLAUDE.md's "UI versions"
# section). rag_engine.py lives one directory up (app/), not alongside
# archived files, so it's added to the import path explicitly here — this
# keeps `streamlit run app/archived/streamlit_app_v2.py` runnable on its
# own without needing PYTHONPATH set manually.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
from theme_v2 import inject_theme

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
# Theme
# -----------------------------
# Streamlit's frontend doesn't expose the active theme via a CSS attribute we
# can select on, so st.context.theme.type (resolved server-side) picks the
# right token set in Python; native widget styling comes from
# .streamlit/config.toml, everything else from theme.inject_theme().
_theme_type = getattr(st.context.theme, "type", None) or "light"
_is_dark = _theme_type == "dark"
inject_theme(_is_dark)

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

    if st.button("🔄 Start a New Conversation", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

    st.toggle("🔊 Read answers aloud", value=True, key="read_aloud")

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

    st.caption("Answers are based on the LG microwave manuals provided to this assistant.")

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
        <h1><span class="hero-emoji">🤖</span> Ask Your Microwave</h1>
        <p class="hero-subtitle"><strong>Your friendly guide to your LG microwave.</strong></p>
        <p class="hero-subtitle">Ask questions in plain English about cooking functions, settings, accessories, cleaning, and safety.</p>
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
        "🍞 How can I bake a cake?",
        "🔥 How do I use the smoking function?",
        "🥘 How do I cook paneer?",
        "🍗 How do I use the rotisserie?",
        "🍕 How do I cook frozen pizza?",
        "🧼 How do I clean the microwave?",
    ]

    st.markdown('<div class="section-label">👨‍🍳 Cooking Mode</div>', unsafe_allow_html=True)
    st.caption("Tell me what you're cooking, and I'll help you find a suitable method from the manual.")

    with st.container(key="cooking_mode_card", border=False):
        cooking_food = st.text_input(
            "What are you cooking?",
            placeholder="e.g., chicken breast, paneer, frozen pizza...",
            key="cooking_food_input",
        )

        if st.button("🍳 Find a Cooking Method", use_container_width=True, key="cooking_find_btn", type="primary"):
            if cooking_food.strip():
                st.session_state.pending_question = (
                    f"I am cooking {cooking_food.strip()}. What cooking method from the microwave manual would you recommend, and how should I use it?"
                )
                st.rerun()

    st.markdown('<div class="section-label">💬 Try asking me...</div>', unsafe_allow_html=True)

    remaining_questions = example_questions[1:]
    grid_cols = st.columns(2)
    for i, question in enumerate(remaining_questions):
        with grid_cols[i % 2]:
            with st.container(key=f"example_card_{i}", border=False):
                if st.button(question, use_container_width=True, key=f"example_q_{i}"):
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
    if st.button(f"💬 Ask a follow-up: {followup}", use_container_width=True, key="followup_btn", type="tertiary"):
        st.session_state.pending_question = followup.split(" ", 1)[1]
        del st.session_state.followup_question
        st.rerun()

_last_assistant_msg = next(
    (m for m in reversed(st.session_state.messages)
     if m["role"] == "assistant" and m.get("question")),
    None,
)
if _last_assistant_msg:
    if st.button("📖 Explain that in more detail", use_container_width=True, key="detail_btn", type="tertiary"):
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

# -----------------------------
# Creator credit
# -----------------------------
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
