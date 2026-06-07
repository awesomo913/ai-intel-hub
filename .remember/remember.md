# Handoff

## State
Accounts tab verified working (2 profile cards render — Your Chrome + Elyanna, all 6 quick-launch buttons). Bug fixed: refresh() now re-renders on every tab switch (commit 44edc65, main). build_exe.bat created in project root but NOT yet run — exe stale. Hermes agent-reach SKILL.md installed at AppData/Local/hermes/skills/agent-reach/.

## Next
1. Run `build_exe.bat` in `C:\Users\computer\Desktop\AI\ai_intel_hub` → Desktop\My Apps\AIIntelHub.exe
2. Build **Skills/Config Visual Dashboard** — new CustomTkinter app, dark UI, scans Hermes skills + Claude skills + Hermes config.yaml, card grid with status dots, at Desktop/AI/skills_dashboard/ + Desktop/My Apps/SkillsDashboard.exe

## Context
- Skills dashboard scan targets: `AppData/Local/hermes/skills/` (Hermes), `~/.claude/skills/` (Claude Code), `AppData/Local/hermes/config.yaml`
- Each skill card shows: name, description, tags, last-modified, installed status (green/yellow/red dot)
- Dark theme matching ai_intel_hub aesthetic — search bar, filterable by source (Hermes vs Claude)
- agent-reach SKILL has corrections baked in: `bird` not `twitter`, RSS+Weibo added, alt-account security note
- API server still on port 7891: `curl http://localhost:7891/feed?limit=5`
