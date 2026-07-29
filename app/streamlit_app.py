import streamlit as st

from rag_engine import (
    load_or_build_index,
    answer_question
)

st.set_page_config(
    page_title="Ask Your Microwave",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Custom styling
# -----------------------------
st.markdown(
    """
    <style>
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
        font-size: 2.3rem;
    }

    .hero p {
        margin-bottom: 0.4rem;
        font-size: 1.05rem;
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

# -----------------------------
# Display conversation history
# -----------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

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

# -----------------------------
# Chat input
# -----------------------------
prompt = st.chat_input(
    "Ask anything about your LG microwave..."
)

if pending_question:
    prompt = pending_question

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

    with st.chat_message("assistant"):
        with st.spinner("🔎 Searching the manuals..."):
            try:
                answer = answer_question(
                    query=prompt,
                    chunks=chunks,
                    faiss_index=faiss_index,
                    bm25_index=bm25_index,
                )
                st.markdown(answer)
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
            "content": answer
        }
    )

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