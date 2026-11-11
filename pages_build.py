#!/usr/bin/env python3
"""Cloudflare Pages builder for Expert Team V8 approved STATIC preview.

Current Cloudflare settings (leave unchanged):
  Build command: pip install -r requirements.txt && python pages_build.py
  Build output directory: dist
  Root directory: blank

This publishes only the static site and DOES NOT enable CMS, forms or CRM.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "dist"
PAGES = (
    "404", "admin", "assets", "blog", "ceny", "downloads",
    "kalkulyator-marketologa", "kejsy", "kontakty",
    "marketingovyj-plan", "materialy", "o-kompanii",
    "politika-konfidencialnosti", "resheniya", "stranicy", "uslugi",
)


def main():
    home = ROOT / "index.html"
    css = ROOT / "assets" / "v4.css"
    if not home.is_file() or not css.is_file():
        raise SystemExit("ERROR: missing V8 index.html or assets/v4.css in GitHub root")
    # Prevent a silent successful deployment of the OLD site.
    if "V8 / fix 1" not in css.read_text(encoding="utf-8"):
        raise SystemExit("ERROR: V8 styles missing: upload V8 assets/v4.css to GitHub")
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    for filename in ("index.html", "404.html"):
        file = ROOT / filename
        if file.is_file():
            shutil.copy2(file, DEST / filename)
    for name in PAGES:
        directory = ROOT / name
        if directory.is_dir():
            shutil.copytree(directory, DEST / name)
    (DEST / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (DEST / "_headers").write_text("/*\n  X-Robots-Tag: noindex, nofollow, noarchive\n",encoding="utf-8")
    html = list(DEST.rglob("*.html"))
    print(f"Expert Team V8 STATIC BUILD SUCCESS: {len(html)} HTML files in dist")
    print("Warning: public preview. Decap CMS and CRM form sending are NOT configured.")


if __name__ == "__main__":
    main()
