"""
Design-system CSS for the redesigned UI (streamlit_app_v2.py).

Streamlit doesn't expose the active light/dark theme as a selectable CSS
attribute, so the caller resolves it server-side (via st.context.theme.type)
and passes it in here — the whole token set is picked in Python and baked
into one injected <style> block per render.
"""

import streamlit as st

RADIUS = {"sm": "10px", "md": "16px", "lg": "24px", "pill": "999px"}
SPACE = {"1": "4px", "2": "8px", "3": "12px", "4": "16px", "5": "24px", "6": "32px"}

DARK_TOKENS = {
    "surface-1": "rgba(255, 255, 255, 0.06)",
    "surface-1-hover": "rgba(255, 255, 255, 0.1)",
    "surface-1-border": "rgba(255, 255, 255, 0.12)",
    "surface-2": "#141417",
    "surface-2-border": "#2a2a2e",
    "text-primary": "#f5f5f7",
    "text-secondary": "#9ca3af",
    "accent": "#fb923c",
    "accent-soft": "rgba(251, 146, 60, 0.18)",
    "shadow-card": "0 6px 18px rgba(0, 0, 0, 0.45)",
    "shadow-hero": "0 30px 80px rgba(0, 0, 0, 0.55)",
    "hero-bg": "linear-gradient(160deg, #241405 0%, #0b0b0d 65%)",
    "hero-border": "rgba(255, 255, 255, 0.08)",
    "hero-title-gradient": "linear-gradient(135deg, #fed7aa 0%, #fdba74 45%, #fff7ed 100%)",
}

LIGHT_TOKENS = {
    "surface-1": "rgba(255, 255, 255, 0.65)",
    "surface-1-hover": "rgba(255, 255, 255, 0.92)",
    "surface-1-border": "rgba(31, 41, 55, 0.08)",
    "surface-2": "#ffffff",
    "surface-2-border": "#e5e7eb",
    "text-primary": "#1f2937",
    "text-secondary": "#6b7280",
    "accent": "#f97316",
    "accent-soft": "rgba(249, 115, 22, 0.14)",
    "shadow-card": "0 6px 16px rgba(31, 41, 55, 0.08)",
    "shadow-hero": "0 24px 60px rgba(194, 65, 12, 0.15)",
    "hero-bg": "linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%)",
    "hero-border": "#fed7aa",
    "hero-title-gradient": "linear-gradient(135deg, #9a3412 0%, #c2410c 50%, #ea580c 100%)",
}


def _root_vars(is_dark: bool) -> str:
    tokens = DARK_TOKENS if is_dark else LIGHT_TOKENS
    lines = [f"  --{name}: {value};" for name, value in tokens.items()]
    lines += [f"  --radius-{k}: {v};" for k, v in RADIUS.items()]
    lines += [f"  --space-{k}: {v};" for k, v in SPACE.items()]
    return "\n".join(lines)


def inject_theme(is_dark: bool) -> None:
    """Injects the full custom CSS for the app, using the token set for the
    given mode. Native widget colors/font/radius are handled separately by
    .streamlit/config.toml; this covers everything config.toml can't reach
    (hero, cards, pills, chat bubbles, animations)."""

    st.markdown(
        f"""
        <style>
        :root {{
{_root_vars(is_dark)}
        }}

        /* ==============================================================
           Global
           ============================================================== */
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stChatMessageContent"] p,
        [data-testid="stChatMessageContent"] li {{
            font-size: 1.15rem;
            line-height: 1.65;
        }}

        /* stAlert (st.error/st.warning/etc.) sizes its icon and box height
           for Streamlit's default text size — the larger size above clipped
           the message against the top of the alert box, so alerts opt back
           out and keep their normal, correctly-fitted size. */
        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {{
            font-size: 1rem;
            line-height: 1.5;
        }}

        .stButton button {{
            font-size: 1.02rem;
            font-weight: 500;
        }}

        .main .block-container {{
            max-width: 1050px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }}

        /* ==============================================================
           Animation keyframes
           ============================================================== */
        @keyframes fadeSlideIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes heroFadeSlideIn {{
            from {{ opacity: 0; transform: translateY(28px) scale(0.98); }}
            to {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}

        @keyframes pillFadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ==============================================================
           Hero
           ============================================================== */
        .hero {{
            position: relative;
            overflow: hidden;
            padding: 3.5rem 2.75rem;
            border-radius: var(--radius-lg);
            background: var(--hero-bg);
            border: 1px solid var(--hero-border);
            margin-bottom: 2rem;
            color: var(--text-primary);
            box-shadow: var(--shadow-hero);
            animation: heroFadeSlideIn 0.9s cubic-bezier(0.16, 1, 0.3, 1);
            container-type: inline-size;
        }}

        .hero::before {{
            content: "";
            position: absolute;
            top: -45%;
            right: -15%;
            width: 65%;
            height: 170%;
            background: radial-gradient(circle, var(--accent-soft) 0%, transparent 70%);
            pointer-events: none;
        }}

        .hero > * {{
            position: relative;
            z-index: 1;
        }}

        .hero h1 {{
            margin: 0 0 0.5rem 0;
            /* Sized off the viewport (vw) as a fallback for browsers without
               container query units; the real rule below sizes off the
               hero box itself (cqw), since .hero's rendered width is capped
               well under the full viewport by .block-container's max-width —
               using vw alone made the text lock near its max size and wrap. */
            font-size: clamp(1.75rem, 4.5vw, 3rem);
            font-size: clamp(1.5rem, 6.5cqw, 3rem);
            font-weight: 800;
            letter-spacing: -0.02em;
            line-height: 1.05;
            white-space: nowrap;
            background: var(--hero-title-gradient);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: fadeSlideIn 0.7s ease-out 0.1s backwards;
        }}

        .hero p.hero-subtitle {{
            margin: 0 0 0.4rem 0;
            font-size: 1.25rem;
            color: var(--text-primary) !important;
            opacity: 0.92;
            max-width: 640px;
            animation: fadeSlideIn 0.7s ease-out 0.2s backwards;
        }}

        .feature-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-top: 1.5rem;
        }}

        .feature-pill {{
            padding: 0.5rem 1.1rem;
            border-radius: var(--radius-pill);
            background: var(--surface-1);
            backdrop-filter: blur(16px) saturate(160%);
            -webkit-backdrop-filter: blur(16px) saturate(160%);
            border: 1px solid var(--surface-1-border);
            color: var(--text-primary);
            font-size: 0.92rem;
            font-weight: 500;
            white-space: nowrap;
            transition: transform 0.2s ease, background 0.2s ease;
            animation: pillFadeIn 0.5s ease-out backwards;
        }}

        .feature-pill:hover {{
            transform: translateY(-2px);
            background: var(--surface-1-hover);
        }}

        .feature-pill:nth-child(1) {{ animation-delay: 0.35s; }}
        .feature-pill:nth-child(2) {{ animation-delay: 0.40s; }}
        .feature-pill:nth-child(3) {{ animation-delay: 0.45s; }}
        .feature-pill:nth-child(4) {{ animation-delay: 0.50s; }}
        .feature-pill:nth-child(5) {{ animation-delay: 0.55s; }}

        /* ==============================================================
           Section labels
           ============================================================== */
        .section-label {{
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            margin-top: 2rem;
            margin-bottom: 0.75rem;
            color: var(--text-primary);
        }}

        /* ==============================================================
           Welcome-state cards
           ============================================================== */
        .st-key-cooking_mode_card {{
            background: var(--surface-1);
            backdrop-filter: blur(20px) saturate(160%);
            -webkit-backdrop-filter: blur(20px) saturate(160%);
            border: 1px solid var(--surface-1-border);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            box-shadow: var(--shadow-card);
            margin-bottom: 1.5rem;
        }}

        [class*="st-key-example_card_"] button {{
            width: 100%;
            min-height: 64px;
            text-align: left;
            padding: 1rem 1.25rem;
            font-size: 1.02rem;
            border-radius: var(--radius-md);
            background: var(--surface-1);
            backdrop-filter: blur(16px) saturate(160%);
            -webkit-backdrop-filter: blur(16px) saturate(160%);
            border: 1px solid var(--surface-1-border);
            color: var(--text-primary);
            box-shadow: var(--shadow-card);
            transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease;
        }}

        [class*="st-key-example_card_"] button:hover {{
            transform: translateY(-2px);
            background: var(--surface-1-hover);
            border-color: var(--accent-soft);
        }}

        [class*="st-key-example_card_"] button:active {{
            transform: scale(0.98);
        }}

        .tip-card {{
            padding: 1rem 1.25rem;
            border-radius: var(--radius-md);
            background: var(--surface-2);
            border: 1px solid var(--surface-2-border);
            border-left: 3px solid var(--accent);
            color: var(--text-primary);
            margin-top: 1rem;
            box-shadow: var(--shadow-card);
        }}

        .tip-card em {{
            color: var(--text-primary);
        }}

        /* ==============================================================
           Sidebar
           ============================================================== */
        .daily-tip {{
            padding: 0.9rem 1rem;
            border-radius: var(--radius-md);
            background: var(--surface-2);
            border: 1px solid var(--surface-2-border);
            border-left: 4px solid var(--accent);
            color: var(--text-primary);
            box-shadow: var(--shadow-card);
            font-size: 0.92rem;
            line-height: 1.55;
            margin-bottom: var(--space-5);
        }}

        .status-card {{
            padding: 0.7rem 0.85rem;
            border-radius: var(--radius-md);
            background: var(--surface-2);
            border: 1px solid var(--surface-2-border);
            color: var(--text-primary);
            font-size: 0.9rem;
            box-shadow: var(--shadow-card);
            margin-top: var(--space-4);
            margin-bottom: var(--space-4);
        }}

        .creator-credit {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.82rem;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid var(--surface-1-border);
        }}

        /* ==============================================================
           Chat area
           ============================================================== */
        div[data-testid="stChatMessage"] {{
            border-radius: var(--radius-md);
            padding: 0.25rem 0.5rem;
            animation: fadeSlideIn 0.35s ease-out;
        }}

        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{
            background: var(--surface-1);
            border: 1px solid var(--surface-1-border);
            padding: 0.75rem 1rem;
            box-shadow: var(--shadow-card);
        }}

        [data-testid="stExpander"] {{
            border-radius: var(--radius-md) !important;
            border: 1px solid var(--surface-1-border) !important;
        }}

        [data-testid="stAudio"] {{
            border-radius: var(--radius-sm);
            overflow: hidden;
            margin-top: 0.5rem;
        }}

        div[data-testid="stChatInput"] {{
            padding-bottom: 1rem;
        }}

        .st-key-followup_btn button,
        .st-key-detail_btn button {{
            border-radius: var(--radius-pill);
        }}

        /* ==============================================================
           Responsive
           ============================================================== */
        @media (max-width: 640px) {{
            .hero {{
                padding: 2.25rem 1.5rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
