"""
Design-system CSS for streamlit_app_v3.py (the current live UI).

Previous versions' UI/theme files live under app/archived/ (see CLAUDE.md's
"UI versions" section) — this module intentionally does not import from
them, since archived files are frozen reference/rollback snapshots, not a
dependency the current app should rely on. The base color/radius/spacing
tokens below were originally introduced in app/archived/theme_v2.py and are
inlined here rather than imported, then layered with a bigger editorial
type scale, a curated set of easing curves, and CSS for the full-bleed
hero, scroll-revealed sections, capabilities showcase, and the cursor-glow /
touch-ripple effect driven by effects_v3.py.

Numeric proportions for the type scale, spacing tiers, and easing curves
are loosely inspired by the design tokens captured in .claude/Antigravity.txt
(a raw computed-styles dump from Google's Antigravity page) — only the
*numbers*, not its font-family or literal CSS, since this app keeps Inter
(loaded by .streamlit/config.toml, which can't be edited here).

Light/dark is resolved server-side (st.context.theme.type) and the whole
token set is baked into one injected <style> block per render.
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

# Extra spacing tiers for the more editorial section rhythm this page uses
# (the base SPACE scale above only goes up to "6" / 32px, which is fine for
# compact cards but too tight for full-bleed section padding).
SPACE_V2 = {**SPACE, "7": "48px", "8": "64px", "9": "96px"}

# clamp()-based fluid type scale — bigger and more editorial than the
# archived v2 UI's hero (which topped out at 3rem). Values are
# viewport-fluid so the same rules work from phone to wide desktop without
# a wall of media queries.
TYPE_SCALE = {
    # Min end is tuned low (vs. a flat 2.75rem) so "Ask Your Microwave" can
    # stay on one line (white-space: nowrap, see .hero-v2 h1) down to narrow
    # phone widths without overflowing the viewport.
    "hero": "clamp(1.5rem, 7vw, 4.75rem)",
    "display": "clamp(1.85rem, 4vw, 2.75rem)",
    "kicker": "0.8rem",
    "body-lg": "1.15rem",
    "caption": "0.85rem",
}

# Curated cubic-bezier curves (subset of the easing scale found in
# .claude/Antigravity.txt) used for entrance/reveal/hover motion.
EASING = {
    "out-quart": "cubic-bezier(0.165, 0.84, 0.44, 1)",
    "out-expo": "cubic-bezier(0.19, 1, 0.22, 1)",
    "out-back": "cubic-bezier(0.34, 1.85, 0.64, 1)",
    "in-out-cubic": "cubic-bezier(0.645, 0.045, 0.355, 1)",
}

# A punchier, higher-alpha glow color for the cursor-follow effect —
# accent-soft (0.14-0.18 alpha) is tuned for static borders/backgrounds and
# reads as too faint once it's a moving spotlight, so the glow gets its own
# stronger token instead of bumping accent-soft everywhere it's used.
GLOW_STRONG = {
    True: "rgba(251, 146, 60, 0.55)",   # dark mode
    False: "rgba(249, 115, 22, 0.42)",  # light mode
}


def _root_vars(is_dark: bool) -> str:
    tokens = DARK_TOKENS if is_dark else LIGHT_TOKENS
    lines = [f"  --{name}: {value};" for name, value in tokens.items()]
    lines += [f"  --radius-{k}: {v};" for k, v in RADIUS.items()]
    lines += [f"  --space-{k}: {v};" for k, v in SPACE_V2.items()]
    lines += [f"  --type-{k}: {v};" for k, v in TYPE_SCALE.items()]
    lines += [f"  --ease-{k}: {v};" for k, v in EASING.items()]
    lines += [f"  --glow-strong: {GLOW_STRONG[is_dark]};"]
    # Cursor-glow position, written at runtime by effects_v3.py's JS onto
    # the .hero-v2 element itself (scoped there, not documentElement, so the
    # glow never leaks outside the hero's overflow:hidden bounds).
    lines += ["  --glow-x: 50%;", "  --glow-y: 40%;"]
    return "\n".join(lines)


def inject_theme_v2(is_dark: bool) -> None:
    """Injects the full custom CSS for streamlit_app_v3.py. Native widget
    colors/font/radius still come from .streamlit/config.toml (shared across
    every UI version in this repo); this covers everything config.toml
    can't reach."""

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
            font-size: var(--type-body-lg);
            line-height: 1.65;
        }}

        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {{
            font-size: 1rem;
            line-height: 1.5;
        }}

        .stButton button {{
            font-size: 1.02rem;
            font-weight: 500;
        }}

        /* Streamlit reserves space above .block-container to clear its own
           fixed header (the translucent bar holding the "Deploy" button and
           the ⋮ menu) — several selectors across Streamlit versions, hence
           the belt-and-suspenders list, all zeroed so the hero can sit
           right at the same level as that header instead of below it. */
        .main .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"] {{
            max-width: 1180px;
            padding-top: 0 !important;
            padding-bottom: 3rem;
        }}

        section.stMain {{
            padding-top: 0 !important;
        }}

        /* ==============================================================
           Animation keyframes
           ============================================================== */
        @keyframes fadeSlideIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes heroFadeSlideIn {{
            from {{ opacity: 0; transform: translateY(32px) scale(0.98); }}
            to {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}

        @keyframes pillFadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes chevronBounce {{
            0%, 100% {{ transform: translateY(0); opacity: 0.55; }}
            50% {{ transform: translateY(8px); opacity: 1; }}
        }}

        @keyframes rippleExpand {{
            from {{ transform: scale(0); opacity: 0.85; }}
            to {{ transform: scale(16); opacity: 0; }}
        }}

        /* ==============================================================
           Full-bleed hero
           ============================================================== */
        /* Break out of .block-container's centered max-width to go edge to
           edge — the trickiest rule in this file. Relies on the hero being
           a normal block-flow descendant with no clipping/transformed
           ancestor between it and the viewport; if a future Streamlit
           version wraps .block-container in something that clips overflow,
           this rule stops reaching full width (falls back to
           block-container's width, which still looks fine, just not
           edge-to-edge). */
        .hero-v2 {{
            position: relative;
            overflow: hidden;
            margin-left: calc(50% - 50vw);
            margin-right: calc(50% - 50vw);
            width: 100vw;
            min-height: 90svh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: var(--space-6) var(--space-5) var(--space-8);
            background: var(--hero-bg);
            border-bottom: 1px solid var(--hero-border);
            color: var(--text-primary);
            animation: heroFadeSlideIn 1s var(--ease-out-expo);
            container-type: inline-size;
        }}

        .hero-v2::before {{
            content: "";
            position: absolute;
            top: -45%;
            right: -15%;
            width: 65%;
            height: 170%;
            background: radial-gradient(circle, var(--accent-soft) 0%, transparent 70%);
            pointer-events: none;
        }}

        /* Cursor-glow overlay — created and positioned (via --glow-x/--glow-y)
           by effects_v3.py's JS. Absolutely positioned *inside* the hero, so
           .hero-v2's own overflow:hidden naturally clips it to the hero —
           this is what keeps the glow scoped to the hero instead of bleeding
           into the calmer, more readable chat area further down the page. */
        .hero-v2 .glow-overlay {{
            position: absolute;
            inset: 0;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.5s ease;
            background: radial-gradient(
                circle at var(--glow-x) var(--glow-y),
                var(--glow-strong) 0%,
                transparent 60%
            );
        }}

        .hero-v2.glow-active .glow-overlay {{
            opacity: 1;
        }}

        .hero-v2.glow-ambient .glow-overlay {{
            opacity: 0.85;
        }}

        .glow-ripple {{
            position: absolute;
            left: var(--ripple-x);
            top: var(--ripple-y);
            width: 14px;
            height: 14px;
            margin: -7px 0 0 -7px;
            border-radius: 50%;
            background: radial-gradient(circle, var(--glow-strong) 0%, transparent 70%);
            pointer-events: none;
            animation: rippleExpand 0.7s var(--ease-out-quart) forwards;
        }}

        .hero-v2 > * {{
            position: relative;
            z-index: 1;
        }}

        .hero-kicker {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            font-size: var(--type-kicker);
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--accent);
            margin-bottom: var(--space-4);
            animation: fadeSlideIn 0.7s ease-out 0.05s backwards;
        }}

        .hero-v2 h1 {{
            margin: 0 0 var(--space-4) 0;
            font-size: var(--type-hero);
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.02;
            /* Kept on one line at any viewport width — the fluid clamp
               above (down to 1.5rem) is tuned specifically so this never
               overflows, even on narrow phones. */
            white-space: nowrap;
            max-width: 95vw;
            background: var(--hero-title-gradient);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: fadeSlideIn 0.8s ease-out 0.1s backwards;
        }}

        .hero-v2 h1 .hero-emoji {{
            -webkit-text-fill-color: initial;
            display: inline-block;
            margin-right: 0.1em;
        }}

        .hero-v2 p.hero-subtitle {{
            margin: 0 auto var(--space-2);
            font-size: var(--type-display);
            font-weight: 400;
            color: var(--text-primary) !important;
            opacity: 0.85;
            max-width: 40ch;
            animation: fadeSlideIn 0.8s ease-out 0.2s backwards;
        }}

        .feature-row {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 0.5rem;
            margin-top: var(--space-6);
        }}

        .feature-pill {{
            padding: 0.45rem 0.9rem;
            border-radius: var(--radius-pill);
            background: var(--surface-1);
            backdrop-filter: blur(16px) saturate(160%);
            -webkit-backdrop-filter: blur(16px) saturate(160%);
            border: 1px solid var(--surface-1-border);
            color: var(--text-primary);
            font-size: 0.85rem;
            font-weight: 500;
            white-space: nowrap;
            transition: transform 0.2s var(--ease-out-quart), background 0.2s ease;
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

        .hero-scroll-cue {{
            margin-top: var(--space-8);
            font-size: 1.4rem;
            color: var(--text-secondary);
            animation: chevronBounce 2s ease-in-out infinite;
        }}

        /* ==============================================================
           Cursor-follow spotlight on cards & pills
           ============================================================== */
        /* Same visual language as the hero's cursor-glow, scaled down to
           each element. effects_v3.py's delegated pointermove listener
           (mouse only) keeps --mx/--my updated to the cursor's position
           relative to whichever of these the pointer is currently over.
           Visibility itself is plain CSS :hover — so on touch (no hover
           state) or if the injected JS never runs, these are still fully
           usable cards/buttons, just without the moving spotlight. */
        .capability-card,
        .st-key-cooking_mode_card,
        [class*="st-key-example_card_"] button,
        .feature-pill {{
            position: relative;
            overflow: hidden;
        }}

        .capability-card::after,
        .st-key-cooking_mode_card::after,
        [class*="st-key-example_card_"] button::after,
        .feature-pill::after {{
            content: "";
            position: absolute;
            inset: 0;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
            background: radial-gradient(
                circle at var(--mx, 50%) var(--my, 50%),
                var(--glow-strong) 0%,
                transparent 65%
            );
        }}

        .capability-card:hover::after,
        .st-key-cooking_mode_card:hover::after,
        [class*="st-key-example_card_"] button:hover::after,
        .feature-pill:hover::after {{
            opacity: 1;
        }}

        @media (prefers-reduced-motion: reduce) {{
            .hero-v2, .hero-v2 h1, .hero-v2 p.hero-subtitle, .feature-pill,
            .hero-kicker, .hero-scroll-cue, div[data-testid="stChatMessage"],
            .reveal, .capability-card, .st-key-cooking_mode_card,
            [class*="st-key-example_card_"] button {{
                animation: none !important;
                transition: none !important;
            }}
            .hero-v2 .glow-overlay, .glow-ripple,
            .capability-card::after, .st-key-cooking_mode_card::after,
            [class*="st-key-example_card_"] button::after,
            .feature-pill::after {{
                display: none !important;
            }}
        }}

        /* ==============================================================
           Scroll-revealed sections (below the hero)
           ============================================================== */
        /* Guaranteed CSS-only fallback: every revealable element fades in
           on its own via this keyframe animation, ~1.8s after it mounts,
           even if the JS below (effects_v3.py's IntersectionObserver,
           injected via a sandboxed iframe) never runs — e.g. blocked by an
           ad blocker or a stricter CSP. The cooking-mode card and example
           questions are functional, not decorative, so they must never be
           permanently stuck at opacity:0 waiting on JS. When the JS *does*
           run, `.is-visible` (added on scroll-into-view) overrides this
           with a faster, undelayed version of the same animation for the
           snappier "reveal on scroll" feel — same guaranteed end state
           either way, just reached sooner and scroll-triggered when JS is
           available. */
        @keyframes revealFallback {{
            from {{ opacity: 0; transform: translateY(24px); }}
            to {{ opacity: 1; transform: none; }}
        }}

        .reveal,
        .st-key-cooking_mode_card,
        [class*="st-key-example_card_"] {{
            opacity: 0;
            transform: translateY(24px);
            animation: revealFallback 0.8s var(--ease-out-quart) 1s forwards;
        }}

        .reveal.is-visible,
        .st-key-cooking_mode_card.is-visible,
        [class*="st-key-example_card_"].is-visible {{
            animation: revealFallback 0.6s var(--ease-out-quart) forwards;
        }}

        .section-kicker {{
            font-size: var(--type-kicker);
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--accent);
            margin-top: var(--space-9);
            margin-bottom: var(--space-2);
        }}

        .section-title {{
            font-size: var(--type-display);
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--text-primary);
            margin-bottom: var(--space-5);
        }}

        .section-label {{
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            margin-top: var(--space-7);
            margin-bottom: 0.75rem;
            color: var(--text-primary);
        }}

        /* ==============================================================
           Capabilities showcase
           ============================================================== */
        .capabilities-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: var(--space-4);
            margin-bottom: var(--space-3);
        }}

        .capability-card {{
            padding: var(--space-5);
            border-radius: var(--radius-lg);
            background: var(--surface-1);
            backdrop-filter: blur(16px) saturate(160%);
            -webkit-backdrop-filter: blur(16px) saturate(160%);
            border: 1px solid var(--surface-1-border);
            box-shadow: var(--shadow-card);
            transition: transform 0.25s var(--ease-out-quart), background 0.25s ease;
        }}

        .capability-card:hover {{
            transform: translateY(-3px);
            background: var(--surface-1-hover);
        }}

        .capability-card .icon {{
            font-size: 1.6rem;
            margin-bottom: var(--space-2);
            display: block;
        }}

        .capability-card .title {{
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.25rem;
        }}

        .capability-card .desc {{
            font-size: 0.92rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }}

        @media (max-width: 900px) {{
            .capabilities-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}

        @media (max-width: 640px) {{
            .capabilities-grid {{ grid-template-columns: 1fr; }}
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
            transition: transform 0.15s var(--ease-out-quart), background 0.15s ease, border-color 0.15s ease;
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
            .hero-v2 {{
                padding: var(--space-8) var(--space-4) var(--space-6);
                min-height: 80svh;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
