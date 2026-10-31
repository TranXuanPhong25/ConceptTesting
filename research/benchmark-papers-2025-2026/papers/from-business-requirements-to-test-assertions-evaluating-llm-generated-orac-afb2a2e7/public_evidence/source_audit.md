# Requirements-to-oracle artifact audit

Checked 2026-10-15. Paper: [arXiv:2607.10277 v1](https://arxiv.org/abs/2607.10277).

- Paper's Data Availability section links Figshare share `https://figshare.com/s/50c240d183532de44c7a` and claims the 171.51 MB package contains business requirements, REQ oracles, generated LLM oracles, test suites and evaluation scripts.
- The Figshare landing page was accessible during one browse request and identifies the exact paper context (“ESEM data”, Defects4J Lang bugs 1 and 3–11), lists MIT, and labels the item **“shared privately.”** It links file ID 64861545.
- Follow-up browser request returned HTTP 403; direct shell requests to the share and downloader returned HTTP 202 with an empty body. No file archive, checksum, or internal directory listing could be verified. Treat the artifact as a restricted/private share rather than a confirmed publicly downloadable package.
- Defects4J upstream itself is public, but the manually authored business requirements, REQ oracle labels, generated outputs, test suites and code are not in the local Defects4J repository.
- No code or model execution. Detailed verdict: `../../../../audit/reviews/079.json`.
