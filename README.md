# Parallel Research Assistant (MVP)

Local Streamlit app that turns a user prompt into parallel web research tasks, runs workers concurrently (DuckDuckGo fallback, optional `browser-use`), and summarizes findings with Gemini.

## Quickstart

1. Python 3.11+
2. Install deps:
```bash
pip install -r requirements.txt
python -m playwright install chromium
```
3. Configure env:
```bash
cp .env.example .env
# put your GOOGLE_API_KEY
```
4. Run app:
```bash
streamlit run app/ui.py
```

## Notes
- If Gemini is unavailable, app falls back to heuristic task creation and a minimal summary.
- If `browser-use` is unavailable, workers fall back to DuckDuckGo search.
- Task files are written to `./tasks/` in Markdown with YAML-like headers.
# Parallel-Research-Assistant-MVP
