# Shared memory (Claude + Codex)

This folder is the single shared knowledge base for every agent working in this repo (Claude Code, Codex, subagents).
Claude's auto-memory directory (`~/.claude/projects/-home-phong-dev-ConceptTester/memory`) is a symlink to this folder,
so Claude loads `MEMORY.md` automatically; Codex is pointed here by `AGENTS.md` rule 6.

## Reading order for a new agent
1. `MEMORY.md`: the index, one line per memory.
2. `research-state.md`: the research direction, where everything lives, current status, next steps.
3. `working-rules.md`: all operational rules (user preferences, safety, git, GPU, folders).
4. Then the topic memories the index points to, as needed.

## Format (one fact per file)
```markdown
---
name: <short-kebab-case-slug>          # = file name without .md
description: <one line, used to decide relevance>
metadata:
  type: user | feedback | project | reference
---
<the fact; for feedback/project add **Why:** and **How to apply:** lines; link others with [[slug]]>
```
- `user`: who the user is and their preferences. `feedback`: how to work (corrections and confirmed approaches, with
  the reason). `project`: ongoing work, decisions, results not derivable from code/git (absolute dates).
  `reference`: pointers to external resources.
- After adding a file, add one line to `MEMORY.md`: `- [Title](file.md) — hook`. Never put content in MEMORY.md.

## Rules for editing
- Update an existing file instead of creating a duplicate; delete memories that turn out wrong.
- Do not store what the repo already records (code, RESULTS.md, PREREG.md, git history); link to it instead.
- Never store secrets, keys or the ngrok URL.
- Mark who/when on substantive changes inside the body if useful (e.g. "(Codex, 2026-10-14)").
- Both agents may edit; keep edits small and factual. The folder is tracked in git (first commit 2026-10-14 at the user's request); commit later edits when the user asks.
