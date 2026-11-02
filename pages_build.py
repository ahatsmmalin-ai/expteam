#!/usr/bin/env python3
"""Expert Team / Cloudflare Pages. Safe first deployment.

Default: upload only a harmless holding page to public Pages domain.
After Cloudflare Access protects BOTH the production Pages domain and previews,
set EXPERTTEAM_INTERNAL_REVIEW=YES on Cloudflare Pages to publish a staging
site from the same repo. Staging is always noindex; never enables production.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist"


def run(*args: str) -> None:
    print("$", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    if os.environ.get("EXPERTTEAM_INTERNAL_REVIEW") != "YES":
        if OUT.exists():
            shutil.rmtree(OUT)
        OUT.mkdir(parents=True)
        (OUT / "index.html").write_text(
            """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><title>Expert Team — тестовый сервер</title>
<style>body{min-height:100vh;margin:0;display:grid;place-items:center;background:#111410;color:#f1f0ea;font:16px/1.7 Arial,sans-serif}main{max-width:550px;padding:28px}h1{font-size:clamp(27px,5vw,46px);line-height:1.2}em{color:#d5ff45;font-style:normal}p{color:#bdc3b7}</style>
</head><body><main><p>EXPERT TEAM / INTERNAL STAGING</p><h1>Тестовый сайт <em>готовится к проверке</em></h1><p>Предварительная настройка хостинга. Контент и рабочая CMS пока недоступны.</p></main></body></html>""",
            encoding="utf-8",
        )
        (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
        print("SAFE HOLDING BUILD: content is NOT being deployed.")
    else:
        run(sys.executable, "scripts/content_integrity.py")
        run(sys.executable, "build.py")  # without --production: forced noindex
        run(sys.executable, "scripts/qa_check.py")
        run(sys.executable, "scripts/cms_smoke_test.py")
        html = (OUT / "index.html").read_text(encoding="utf-8")
        assert 'noindex' in html, "Staging build unexpectedly indexable"
        assert 'Disallow: /' in (OUT / "robots.txt").read_text(encoding="utf-8")
        print("INTERNAL STAGING BUILD: full site generated, noindex maintained.")


if __name__ == "__main__":
    main()
