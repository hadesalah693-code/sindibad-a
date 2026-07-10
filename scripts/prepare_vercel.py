"""Copy dashboard static assets into public/ for Vercel CDN."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"
PUBLIC = ROOT / "public"


def main() -> None:
    if not STATIC.exists():
        raise SystemExit(f"Static source not found: {STATIC}")

    PUBLIC.mkdir(exist_ok=True)
    shutil.copy2(STATIC / "index.html", PUBLIC / "index.html")

    for sub in ("css", "js"):
        src = STATIC / sub
        if src.exists():
            dest = PUBLIC / "static" / sub
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)

    print(f"Prepared Vercel static assets in {PUBLIC}")


if __name__ == "__main__":
    main()
