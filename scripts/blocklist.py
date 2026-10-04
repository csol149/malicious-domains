#!/usr/bin/env python3
import argparse
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
LIST_FILE = ROOT / "domains.txt"
CHANGELOG = ROOT / "CHANGELOG.md"

SECTIONS = {
    "click-fix": "! Click-Fix domains",
    "unknown-payload": "! Unknown payload",
}
MARKERS = {title.lower(): key for key, title in SECTIONS.items()}

DOMAIN_RE = re.compile(
    r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
ENTRY_RE = re.compile(r"^\|\|(.+)\^$")
VERSION_RE = re.compile(r"^!\s*Version:\s*(.*)$", re.I)


def clean_domain(raw):
    s = raw.strip().lower()
    s = s.removeprefix("||").removesuffix("^")
    s = s.replace("[.]", ".").replace("hxxp", "http")
    if "://" in s:
        s = urlparse(s).hostname or ""
    s = s.split("/", 1)[0].split(":", 1)[0].strip(".")
    return s if DOMAIN_RE.match(s) else None


def parse(text):
    header, entries, problems = [], {k: [] for k in SECTIONS}, []
    current = None
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s:
            continue
        if s.lower() in MARKERS:
            current = MARKERS[s.lower()]
            continue
        if current is None:
            header.append(s)
            continue
        m = ENTRY_RE.match(s)
        d = clean_domain(m.group(1)) if m else None
        if d is None:
            problems.append(f"line {n}: invalid entry: {s!r}")
        else:
            entries[current].append(d)
    if not any(h.lower().startswith("! title") for h in header):
        problems.append("header: missing '! Title:' line")
    return header, entries, problems


def load():
    text = LIST_FILE.read_text()
    header, entries, problems = parse(text)
    return text, header, entries, problems


def to_map(entries):
    return {d: k for k, v in entries.items() for d in v}


def consolidate(entries):
    click = set(entries["click-fix"])
    unknown = set(entries["unknown-payload"]) - click
    return {"click-fix": sorted(click), "unknown-payload": sorted(unknown)}


def get_version(header):
    for h in header:
        m = VERSION_RE.match(h)
        if m:
            return m.group(1).strip()
    return ""


def with_version(header, version):
    out, done = [], False
    for h in header:
        if VERSION_RE.match(h):
            out.append(f"! Version: {version}")
            done = True
        else:
            out.append(h)
    if not done:
        out.insert(min(2, len(out)), f"! Version: {version}")
    return out


def render(header, sections, version):
    out = with_version(header, version)
    for key in SECTIONS:
        out += ["", SECTIONS[key], ""]
        out += [f"||{d}^" for d in sections[key]]
    return "\n".join(out) + "\n"


def update_changelog(version, old_map, new_map):
    lines = [f"- Added `{d}` ({new_map[d]})" for d in sorted(new_map) if d not in old_map]
    lines += [
        f"- Moved `{d}` to {new_map[d]}"
        for d in sorted(new_map)
        if d in old_map and old_map[d] != new_map[d]
    ]
    lines += [f"- Removed `{d}`" for d in sorted(old_map) if d not in new_map]
    if not lines:
        return
    text = CHANGELOG.read_text() if CHANGELOG.exists() else "# Changelog\n"
    rows = text.splitlines()
    heading = f"## {version}"
    idx = next((i for i, r in enumerate(rows) if r.startswith("## ")), None)
    if idx is not None and rows[idx].strip() == heading:
        pos = idx + 1
        if pos < len(rows) and rows[pos] == "":
            pos += 1
        rows[pos:pos] = lines
    else:
        block = [heading, ""] + lines + [""]
        if idx is None:
            rows += [""] + block
        else:
            rows[idx:idx] = block
    CHANGELOG.write_text("\n".join(rows).rstrip("\n") + "\n")


def finalize(old_text, header, old_map, sections):
    if render(header, sections, get_version(header)) == old_text:
        print("No changes.")
        return 0
    version = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    LIST_FILE.write_text(render(header, sections, version))
    new_map = to_map(sections)
    update_changelog(version, old_map, new_map)
    total = sum(len(v) for v in sections.values())
    print(f"Updated to version {version}: {total} domains "
          f"({len(sections['click-fix'])} click-fix, {len(sections['unknown-payload'])} unknown-payload).")
    return 0


def split_input(value):
    return [p for p in re.split(r"[\s,]+", value.strip()) if p]


def require_clean(problems):
    if problems:
        for p in problems:
            print(f"ERROR: {p}")
        sys.exit(1)


def cmd_validate(_args):
    _text, _header, entries, problems = load()
    counts = Counter(d for v in entries.values() for d in v)
    m = to_map(entries)
    for d, c in sorted(counts.items()):
        if c > 1:
            problems.append(f"duplicate entry: {d}")
    for key in SECTIONS:
        if not entries[key]:
            problems.append(f"section is empty: {SECTIONS[key]}")
    if problems:
        for p in problems:
            print(f"ERROR: {p}")
        return 1
    print(f"OK: {len(m)} unique domains.")
    return 0


def cmd_normalize(_args):
    text, header, entries, problems = load()
    require_clean(problems)
    return finalize(text, header, to_map(entries), consolidate(entries))


def cmd_add(args):
    text, header, entries, problems = load()
    require_clean(problems)
    old_map = to_map(entries)
    existing = dict(old_map)
    added, invalid = [], []
    for raw in split_input(args.domains):
        d = clean_domain(raw)
        if d is None:
            invalid.append(raw)
            print(f"::warning::Skipped invalid domain: {raw}")
        elif d in existing:
            print(f"Skipped (already listed under {existing[d]}): {d}")
        else:
            entries[args.category].append(d)
            existing[d] = args.category
            added.append(d)
    if not added:
        print("Nothing to add.")
        return 1 if invalid else 0
    return finalize(text, header, old_map, consolidate(entries))


def cmd_remove(args):
    text, header, entries, problems = load()
    require_clean(problems)
    old_map = to_map(entries)
    targets, missing = set(), []
    for raw in split_input(args.domains):
        d = clean_domain(raw)
        if d is not None and d in old_map:
            targets.add(d)
        else:
            missing.append(raw)
            print(f"::warning::Not found in list: {raw}")
    if not targets:
        print("Nothing to remove.")
        return 1 if missing else 0
    for key in SECTIONS:
        entries[key] = [d for d in entries[key] if d not in targets]
    return finalize(text, header, old_map, consolidate(entries))


def main():
    p = argparse.ArgumentParser(description="Maintain domains.txt")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    sub.add_parser("normalize").set_defaults(fn=cmd_normalize)
    a = sub.add_parser("add")
    a.add_argument("--category", required=True, choices=list(SECTIONS))
    a.add_argument("--domains", required=True)
    a.set_defaults(fn=cmd_add)
    r = sub.add_parser("remove")
    r.add_argument("--domains", required=True)
    r.set_defaults(fn=cmd_remove)
    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
