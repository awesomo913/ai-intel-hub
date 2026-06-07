# Handoff

## State
Accounts tab fully working — FONTS["subheading"] KeyError fixed (→ heading_sm), 2 Chrome profile cards render correctly. exe built: Desktop/My Apps/AIIntelHub.exe (50MB, windowed). build_exe.bat committed. HEAD f9679f1 on main, pushed.

## Next
1. Smoke-test exe: launch `Desktop/My Apps/AIIntelHub.exe`, verify Accounts tab shows 2 cards, no crash
2. Run "Refresh All Feeds" to test notifications (toast fires at ≥0.85 relevance score)
3. Optional: add port 7891 "already-running" guard in api_server.py

## Context
- Run app from parent dir: `cd Desktop/AI && python -m ai_intel_hub` (relative imports break if run from inside project dir)
- Two instances were running mid-session (PIDs 32660/34508) — killed before verify. Check for stale instances before launching.
- QUICK_LAUNCH_TARGETS hardcoded at accounts_view.py:15-22 (low priority to move to config)
