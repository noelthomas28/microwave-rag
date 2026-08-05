"""
Deployment entry point — do not put UI code here.

Streamlit Community Cloud and .devcontainer/devcontainer.json both hardcode
the literal path app/streamlit_app.py as this app's main file, so a file has
to exist at exactly this path for either to work. The actual UI is
versioned (see CLAUDE.md's "UI versions" section) and currently lives in
app/streamlit_app_v3.py — this file just imports it, which executes
streamlit_app_v3.py's top-level code (st.set_page_config() and everything
after it) exactly as if Streamlit had run that file directly.

Promoting a future version to production is then just a one-line change
here (point the import at the new version's filename) — no deployment
config to touch, no dashboard settings to update.
"""

import streamlit_app_v3  # noqa: F401
