# Handoff

## State
Chrome account manager, API server (localhost:7891), breakthrough notifications (Windows toast + PS terminal banner), and memory bridge all built and pushed (commit 7d4bc7d, main branch). Accounts tab + Discord tab both wired in app.py. PS banner hook installed in $PROFILE. Security fix applied (PS command injection in toast strings). No exe built yet.

## Next
1. Run `python run.py` — visually confirm Accounts tab shows 2 profile cards (awesomo913 + Elyanna)
2. Test API: `curl http://localhost:7891/feed?limit=5` while app is running
3. Create `build_exe.bat` and build AIIntelHub.exe → copy to Desktop/My Apps/

## Context
- `QUICK_LAUNCH_TARGETS` in `ui/accounts_view.py:14-21` — edit here to add Perplexity, Reddit, etc.
- API needs fastapi+uvicorn: `uv pip install fastapi uvicorn`
- Intel hints land at `~/.claude/tmp/intel_hints.md` after every fetch (for Claude memory)
- Alert banner file: `~/.claude/tmp/alerts/latest.json`
