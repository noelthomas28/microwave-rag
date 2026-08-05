"""
Ambient JS effects for streamlit_app_v3.py: the hero cursor-glow / touch-
ripple, and the scroll-reveal for the editorial sections below the hero.

Both live here, separate from streamlit_app_v3.py's own scroll-management
JS (ported from streamlit_app.py), because they're generic and
presentation-only — no st.session_state coupling — and because they have a
deliberately different lifecycle: the scroll-management JS is *meant* to
re-run and re-assert itself on every Streamlit rerun, while the listeners
here must attach exactly once per page load (re-attaching on every rerun
would stack up duplicate `pointermove`/`scroll` handlers). Both functions
reach into window.parent.document from inside components.html's sandboxed
iframe, the same DOM-reach-through technique the existing scroll JS uses.
"""

import streamlit.components.v1 as components

# -----------------------------------------------------------------------
# Cursor-glow (desktop) + touch-ripple / scroll-ambient (mobile)
# -----------------------------------------------------------------------
# Scoped entirely to .hero-v2 (per design decision: a moving glow behind the
# chat transcript would hurt readability, especially for this app's
# non-technical family-member audience) — the glow overlay is created as a
# child *inside* the hero, so the hero's own overflow:hidden clips it for
# free; no viewport-wide fixed overlay involved.
#
# Desktop-only glow-follow is the guard + reduced-motion check + one
# pointermove listener + setGlow (~30-35 lines). Touch support reuses the
# exact same setGlow/overlay scaffolding and adds a ripple-on-tap plus a
# scroll-driven ambient drift (~25-30 more lines) — not a second, parallel
# effect system.
_CURSOR_EFFECTS_JS = """
<script>
(function () {
    var doc = window.parent.document;

    // Guard against re-attaching listeners on every Streamlit rerun — this
    // element persists across reruns even though this script's own iframe
    // may be recreated, so a flag on it is a reliable "already initialized"
    // marker (unlike the scroll-management JS, which *wants* to re-run).
    if (doc.documentElement.dataset.glowInit) return;

    // Respect prefers-reduced-motion: skip attaching any listeners at all.
    // (theme_v3.py's CSS also hides the glow/ripple under the same media
    // query as defense in depth.)
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        doc.documentElement.dataset.glowInit = '1';
        return;
    }

    doc.documentElement.dataset.glowInit = '1';

    var isCoarsePointer = window.matchMedia('(pointer: coarse)').matches;

    function getHero() {
        return doc.querySelector('.hero-v2');
    }

    function ensureOverlay(hero) {
        var overlay = hero.querySelector('.glow-overlay');
        if (!overlay) {
            overlay = doc.createElement('div');
            overlay.className = 'glow-overlay';
            hero.appendChild(overlay);
        }
        return overlay;
    }

    function setGlow(hero, x, y) {
        hero.style.setProperty('--glow-x', x + 'px');
        hero.style.setProperty('--glow-y', y + 'px');
    }

    function spawnRipple(hero, x, y) {
        var ripple = doc.createElement('div');
        ripple.className = 'glow-ripple';
        ripple.style.setProperty('--ripple-x', x + 'px');
        ripple.style.setProperty('--ripple-y', y + 'px');
        hero.appendChild(ripple);
        setTimeout(function () {
            if (ripple.parentNode) ripple.parentNode.removeChild(ripple);
        }, 750);
    }

    // One shared pointermove listener: Pointer Events unify mouse/pen/touch,
    // so branching on e.pointerType is the whole "desktop vs. mobile" split
    // for the continuous glow-follow — no separate mouse-only listener.
    doc.addEventListener('pointermove', function (e) {
        var hero = getHero();
        if (!hero) return;
        var rect = hero.getBoundingClientRect();
        var inside = e.clientX >= rect.left && e.clientX <= rect.right &&
                     e.clientY >= rect.top && e.clientY <= rect.bottom;

        if (e.pointerType === 'mouse') {
            hero.classList.toggle('glow-active', inside);
            if (inside) {
                ensureOverlay(hero);
                setGlow(hero, e.clientX - rect.left, e.clientY - rect.top);
            }
        }
    }, { passive: true });

    // Cursor-follow spotlight on cards & pills below the hero (capability
    // cards, the cooking-mode card, example-question tiles, hero feature
    // pills) — same visual language as the hero glow, just scoped smaller
    // per element via theme_v3.py's ::after rules. One delegated listener
    // with closest() rather than per-element listeners, so it keeps working
    // for buttons/cards Streamlit tears down and recreates on every rerun
    // (e.g. the example-question grid) without any re-wiring needed.
    // Visibility is plain CSS :hover; this only ever updates position.
    var CARD_GLOW_SELECTOR =
        '.capability-card, .st-key-cooking_mode_card, ' +
        '[class*="st-key-example_card_"] button, .feature-pill';

    doc.addEventListener('pointermove', function (e) {
        if (e.pointerType !== 'mouse') return;
        var target = e.target.closest && e.target.closest(CARD_GLOW_SELECTOR);
        if (!target) return;
        var rect = target.getBoundingClientRect();
        target.style.setProperty('--mx', (e.clientX - rect.left) + 'px');
        target.style.setProperty('--my', (e.clientY - rect.top) + 'px');
    }, { passive: true });

    // Tap-to-ripple on touch/pen — a persistent hover glow doesn't make
    // sense once the finger lifts, so touch gets a burst instead.
    doc.addEventListener('pointerdown', function (e) {
        if (e.pointerType === 'mouse') return;
        var hero = getHero();
        if (!hero) return;
        var rect = hero.getBoundingClientRect();
        var inside = e.clientX >= rect.left && e.clientX <= rect.right &&
                     e.clientY >= rect.top && e.clientY <= rect.bottom;
        if (!inside) return;
        ensureOverlay(hero);
        spawnRipple(hero, e.clientX - rect.left, e.clientY - rect.top);
    }, { passive: true });

    // Ambient motion for touch devices, tied to scroll instead of a static
    // hover position (there's no hover state on touch): a slow drift while
    // the hero is in view, throttled to one update per animation frame.
    if (isCoarsePointer) {
        var ticking = false;
        function updateAmbient() {
            ticking = false;
            var hero = getHero();
            if (!hero) return;
            var rect = hero.getBoundingClientRect();
            var inView = rect.bottom > 0 && rect.top < window.innerHeight;
            hero.classList.toggle('glow-ambient', inView);
            if (!inView) return;
            ensureOverlay(hero);
            var t = window.scrollY || 0;
            var x = rect.width * (0.5 + 0.18 * Math.sin(t / 300));
            var y = rect.height * (0.4 + 0.14 * Math.cos(t / 400));
            setGlow(hero, x, y);
        }
        doc.addEventListener('scroll', function () {
            if (!ticking) {
                ticking = true;
                window.requestAnimationFrame(updateAmbient);
            }
        }, { passive: true });
        updateAmbient();
    }
})();
</script>
"""

# -----------------------------------------------------------------------
# Scroll-reveal for the editorial sections below the hero
# -----------------------------------------------------------------------
_SCROLL_REVEAL_JS = """
<script>
(function () {
    var doc = window.parent.document;
    if (doc.documentElement.dataset.revealInit) return;
    doc.documentElement.dataset.revealInit = '1';

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        // Reduced motion: just mark everything visible immediately, no
        // observer needed.
        var markAll = function () {
            doc.querySelectorAll('.reveal').forEach(function (el) {
                el.classList.add('is-visible');
            });
        };
        markAll();
        return;
    }

    var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                io.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });

    function observeAll() {
        doc.querySelectorAll('.reveal:not(.is-visible)').forEach(function (el) {
            io.observe(el);
        });
    }

    observeAll();

    // Streamlit re-renders the main page's DOM on every rerun (e.g. a fresh
    // ".reveal" section reappearing after "Start a new conversation" resets
    // the welcome state) independently of whether this script's own iframe
    // re-executes — a MutationObserver keeps picking up newly inserted
    // .reveal elements for the life of the page, rather than a one-shot
    // querySelectorAll that would miss anything rendered later.
    var mo = new MutationObserver(function () { observeAll(); });
    mo.observe(doc.body, { childList: true, subtree: true });
})();
</script>
"""


def inject_cursor_effects() -> None:
    """Hero cursor-glow (desktop) + touch-ripple/ambient-drift (mobile)."""
    components.html(_CURSOR_EFFECTS_JS, height=0)


def inject_scroll_reveal() -> None:
    """IntersectionObserver-driven fade/slide-in for `.reveal` elements."""
    components.html(_SCROLL_REVEAL_JS, height=0)
