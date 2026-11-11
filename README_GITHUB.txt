EXPERT TEAM V8 — READY FOR GITHUB/CLOUDFLARE

1. Extract the ZIP file.
2. In GitHub repository ahatsmmalin-ai/expteam, branch main, upload ALL extracted contents to repository root.
3. CRITICAL: replace existing pages_build.py and requirements.txt and assets/v4.css with the files here.
4. Cloudflare Build command stays: pip install -r requirements.txt && python pages_build.py
5. Cloudflare Build output directory stays: dist
6. Once new deployment succeeds, open https://expteam-staging.pages.dev and hard-refresh (Ctrl+F5).

This is a PUBLIC static test site. Forms are demos; CMS authorization is not connected. The builder adds noindex headers and robots.txt; they do not restrict access.
