from __future__ import annotations

import os
import streamlit as st

from .orchestrator import orchestrate

st.set_page_config(page_title="Parallel Research Assistant", page_icon="🧭", layout="wide")

st.title("Parallel Research Assistant")

with st.sidebar:
    st.header("Settings")
    use_browser = st.toggle("Use browser-use (if available)", value=False, help="Fallback will use DuckDuckGo search")
    model_name = st.text_input("Gemini model", value=os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002"))
    st.caption("Set GOOGLE_API_KEY in your environment for Gemini access.")

prompt = st.text_area("Describe what you need", placeholder="Trip to Tokyo, 5 days in Nov, budget $1500...", height=120)

if st.button("Run", type="primary", disabled=not prompt.strip()):
    with st.spinner("Thinking and planning tasks..."):
        try:
            result = orchestrate(prompt, use_browser=use_browser, model_name=model_name)
        except Exception as exc:
            st.error(f"Error: {exc}")
            st.stop()

    st.success("Done!")

    tasks = result.get("tasks", [])
    paths = result.get("task_paths", [])
    summary = result.get("final_summary", "")

    cols = st.columns(min(3, max(1, len(tasks))))
    for idx, t in enumerate(tasks):
        with cols[idx % len(cols)]:
            st.subheader(t.title)
            st.markdown(f"**Status**: {t.status.value}")
            st.markdown(f"**Objective**: {t.objective}")
            st.markdown(f"**File**: `{paths[idx]}`")

    st.divider()
    st.subheader("Final Plan")
    st.markdown(summary)

st.caption("Run via: `streamlit run app/ui.py` in the project root.")
