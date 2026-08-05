"""
Deployment entry point — do not put UI code here.

Streamlit Community Cloud and .devcontainer/devcontainer.json both hardcode
the literal path app/streamlit_app.py as this app's main file, so a file has
to exist at exactly this path for either to work. The actual UI is
versioned (see CLAUDE.md's "UI versions" section) and currently lives in
app/streamlit_app_v3.py — this file runs it fresh on every single script
run via runpy.run_path(), rather than `import streamlit_app_v3`.

That distinction matters and is not cosmetic: Streamlit reruns this file
top-to-bottom on every interaction (every button click, every widget
change) within the *same* long-lived Python process, but a plain `import`
statement only executes a module's top-level code the first time it's
imported in that process — every subsequent `import streamlit_app_v3` in
this file would be a no-op cache hit against sys.modules, silently
rendering nothing (a blank page with only Streamlit's own chrome, since
none of streamlit_app_v3.py's st.* calls would run again). runpy.run_path()
re-executes the target file's source from scratch every time, exactly like
Streamlit's own ScriptRunner does for whichever file it's pointed at, so
this shim behaves identically to running streamlit_app_v3.py directly.

Promoting a future version to production is then just a one-line change
to the filename below — no deployment config to touch, no dashboard
settings to update.
"""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).parent / "streamlit_app_v3.py"), run_name="__main__")
