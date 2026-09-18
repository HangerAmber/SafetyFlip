"""Check a source export for common anonymous-release leaks and broken site links.

Heuristic screening, not an anonymity guarantee. Git hosting, history, access logs,
PDF metadata and handwritten content still need review; see docs/ANONYMITY.md.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {".git", "__pycache__", ".venv", "venv", ".pytest_cache", ".DS_Store", "node_modules", "build", "dist", "runs", "checkpoints", ".vscode", ".idea", ".ipynb_checkpoints"}
TEXT = {".py", ".md", ".html", ".js", ".css", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".txt", ".svg", ".cff", ".vtt"}
PATTERNS = {
    "email address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "local user path": re.compile(r"(?:[A-Za-z]:[\\/]Users[\\/]|/Users/|/home/)[A-Za-z0-9._-]+", re.I),
    "private key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    "access token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{35,})\b"),
}


def release_files():
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(p in EXCLUDE or p.endswith(".egg-info") for p in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"symlinks are not allowed in release: {rel.as_posix()}")
        if path.is_file() and ((path.name == ".env" or path.name.startswith(".env.")) and path.name != ".env.example"
                               or path.suffix in {".pem", ".p12", ".pfx", ".key"}
                               or path.name in {"id_rsa", "id_ed25519"}):
            raise ValueError(f"sensitive file type is not allowed in release: {rel.as_posix()}")
        if path.is_file() and path.name != "MANIFEST.sha256" and path.suffix not in {".pyc", ".zip"}:
            yield path


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for attr in ("src", "href", "poster"):
            if attr in attrs:
                self.links.append((tag, attr, attrs[attr]))
        if "srcset" in attrs:
            for candidate in attrs["srcset"].split(","):
                parts = candidate.strip().split()
                if parts:
                    self.links.append((tag, "src", parts[0]))


def audit(deny=()):
    errors = []
    files = list(release_files())
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix not in TEXT and path.name not in {".gitignore", ".gitattributes"}:
            continue
        content = path.read_text(encoding="utf-8-sig")
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                errors.append(f"{rel}: potential {label}")
        for term in deny:
            if term.casefold() in content.casefold():
                errors.append(f"{rel}: supplied identity marker found")
        if path.suffix == ".css" and re.search(r"(?:url\s*\(|@import).*?https?://", content, re.I):
            errors.append(f"{rel}: externally loaded stylesheet asset")
        if path.suffix in {".html", ".md"}:
            parser = Links()
            parser.feed(content)
            if path.suffix == ".md":
                # Repository-authored inline Markdown images; HTML images and
                # picture sources are handled by the parser above.
                for target in re.findall(r"!\[[^\]]*\]\(<?([^\s)>]+)>?(?:\s+\"[^\"]*\")?\)", content):
                    parser.links.append(("img", "src", target))
            for tag, attr, target in parser.links:
                link = urlsplit(target)
                if link.scheme in {"http", "https"}:
                    if attr in {"src", "poster"} or tag == "link":
                        errors.append(f"{rel}: externally loaded asset")
                    continue
                if link.scheme:
                    if link.scheme != "data":
                        errors.append(f"{rel}: unexpected link scheme")
                    continue
                if not link.path:
                    if path.suffix == ".html" and link.fragment and link.fragment not in parser.ids:
                        errors.append(f"{rel}: missing anchor #{link.fragment}")
                    continue
                dest = (path.parent / unquote(link.path)).resolve()
                if not dest.is_relative_to(ROOT) or not dest.exists():
                    errors.append(f"{rel}: missing or escaping local link {target}")
    return files, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deny", action="append", default=[], help="identity marker to screen locally; never saved")
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--zip", type=Path, dest="archive", help="write deterministic anonymous export outside source tree")
    args = parser.parse_args()
    files, errors = audit(args.deny)
    if errors:
        print(json.dumps({"status": "failed", "findings": errors}, indent=2))
        raise SystemExit(1)
    if args.manifest or args.archive:
        manifest = ROOT / "MANIFEST.sha256"
        manifest.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}\n" for p in files), encoding="utf-8", newline="\n")
    if args.archive:
        destination = args.archive.resolve()
        if destination.is_relative_to(ROOT):
            parser.error("archive must be outside the source tree")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(files + [ROOT / "MANIFEST.sha256"]):
                info = zipfile.ZipInfo("SafetyFlip/" + path.relative_to(ROOT).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
    print(json.dumps({"status": "passed", "files_checked": len(files), "checks": "text markers, HTML links and embedded README assets", "limitations": "heuristic; see docs/ANONYMITY.md"}, indent=2))


if __name__ == "__main__":
    main()
