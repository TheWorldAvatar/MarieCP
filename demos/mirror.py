"""Download static TWA demo frontends for local serving."""

from __future__ import annotations

import argparse
import re
import shutil
import ssl
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://theworldavatar.io"
UA = "curl/8.0"
CTX = ssl.create_default_context()
REPO = Path(__file__).resolve().parent
MARIE_CLASSIC_SRC = REPO / "marie-classic"


def _get(url: str, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        return resp.read()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def install_twa_favicon(static_root: Path) -> None:
    """Use the same tab icon as https://theworldavatar.io/demos/marie (TWA site favicon)."""
    src = REPO / "hub" / "favicon.png"
    if not src.is_file():
        try:
            _write(src, _get(f"{BASE}/favicon.ico"))
        except urllib.error.HTTPError as exc:
            print("  skip hub favicon download", exc.code)
            return
    for rel in ("zaha/static/img/favicon.png", "marie-classic/static/img/favicon.png"):
        dest = static_root / rel
        if dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            print("  favicon", rel)


def mirror_zaha(out_root: Path) -> None:
    root = out_root / "zaha"
    index_url = f"{BASE}/demos/zaha/"
    html = _get(index_url)
    _write(root / "index.html", html)

    static_refs = set(re.findall(r'(?:href|src)="(\./static/[^"]+)"', html.decode("utf-8", errors="replace")))
    for ref in sorted(static_refs):
        rel = ref.removeprefix("./")
        url = f"{BASE}/demos/zaha/{rel}"
        try:
            _write(root / rel, _get(url))
            print("  zaha", rel)
        except urllib.error.HTTPError as exc:
            print("  skip", rel, exc.code)


def install_marie_classic(out_root: Path) -> None:
    """Copy committed Marie classic UI into demos/static (not on public TWA anymore)."""
    dest = out_root / "marie-classic"
    if not MARIE_CLASSIC_SRC.is_dir() or not (MARIE_CLASSIC_SRC / "index.html").is_file():
        raise RuntimeError(f"Missing committed Marie classic UI at {MARIE_CLASSIC_SRC}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(MARIE_CLASSIC_SRC, dest)
    print(f"  marie-classic copied to {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mirror TWA static demos into demos/static")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO / "static",
        help="Output directory (default: demos/static)",
    )
    parser.add_argument("--zaha-only", action="store_true", help="Mirror Zaha only")
    parser.add_argument("--marie-classic-only", action="store_true", help="Install Marie classic only")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    mirror_zaha_flag = not args.marie_classic_only
    mirror_marie_flag = not args.zaha_only

    if mirror_zaha_flag:
        print("Mirroring Zaha...")
        mirror_zaha(args.out)
        from demos.fetch_missing_zaha_assets import main as fetch_zaha_assets
        from demos.patch_zaha_static import patch_all as patch_zaha

        fetch_zaha_assets()
        patch_zaha(args.out / "zaha")

    if mirror_marie_flag:
        print("Installing Marie classic...")
        install_marie_classic(args.out)

    install_twa_favicon(args.out)
    print(f"Done. Static files under {args.out}")


if __name__ == "__main__":
    main()
