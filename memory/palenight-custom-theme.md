---
name: palenight-custom-theme
description: User wants standalone Palenight colors matching their screenshot, without installing Vira
metadata:
  type: user
---

2026-11-05: User requested a custom VS Code extension to get Palenight colors
without installing Vira. Their reference screenshot has measured background
`#282A37`; the downloaded Vira 2026.9.6 default is `#232634`.

**Why:** The screenshot is the visual target and independence from Vira is explicit.

**How to apply:** Maintain the standalone theme in
`vscode-palenight-custom/` (label **Phong Palenight**). Installation and palette
are documented in its README. A local VSIX is generated in that folder and is
git-ignored. The VSIX was verified with a temporary VS Code installation directory;
the user's normal VS Code settings and active theme were not changed.
