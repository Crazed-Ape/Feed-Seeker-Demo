#!/usr/bin/env python3
"""The Seeker demo scanner (spec section 9).

Usage:
    scan.py DEMO_REPO [--terms DENY_LIST.md] [--patterns PATTERNS.json]

Reads every file in DEMO_REPO except .git/ and this scanner's own three files (scan.py, images.py, patterns.json)
with their compiled .pyc files in its __pycache__/, when they sit inside DEMO_REPO, and every path's name. Flags:

1. every pattern in the public patterns file (tools/demo/patterns.json beside this script, unless --patterns names
   another), on text with hidden characters removed and NFKC applied, plus each hidden character itself;
2. with --terms, every term in the private deny list, as whole words in any case with simple plural and possessive
   forms (a term marked "(exact case)" only as written);
3. any image that still carries metadata (EXIF, XMP, ICC, text chunks, comments, thumbnails, data after its end);
4. any symbolic link (the scan would read its target while the repo serves the link).

Without --terms (the demo repo's public CI) a flag prints only the file, line and pattern number, never the text it
matched. With --terms (before a content PR) it prints the matched text too. A path's own name is line 0.

Exit codes: 0 clean, 1 something flagged, 2 something couldn't be read.
"""

import argparse
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import images  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT_EXT = (".txt", ".md", ".csv", ".json", ".jsonl", ".yml", ".yaml", ".html", ".svg", ".js", ".css", ".py", "")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")
TERM_LINE = re.compile(r"^\s*\d+\.\s+`([^`]+)`(.*)$")
SECTION = re.compile(r"^##\s+(\d+)\.")
OWN_FILES = ("scan.py", "images.py", "patterns.json")
ZWJ, VS16, KEYCAP = "\u200d", "\ufe0f", "\u20e3"
# A letter: a word character that isn't a digit or `_`, so `rue_plan`, `Rue2` and `RueTeam`'s edges end a word.
NOT_LETTER_BEFORE, NOT_LETTER_AFTER = r"(?<![^\W\d_])", r"(?![^\W\d_])"


class Unreadable(Exception):
    pass


def load_patterns(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        hidden = re.compile(data["hidden"])
        # An allowed link is matched from where the address starts, whole: nothing more of a path may follow it.
        allow = [re.escape(u) + r"(?![A-Za-z0-9_./?#-])" for u in data.get("allow_urls") or []]
        out = []
        for entry in data["patterns"]:
            if entry["re"] == "hidden":
                out.append({"n": entry["n"], "what": entry["what"], "hidden": True})
                continue
            unless = []
            for u in entry.get("unless") or []:
                unless.extend([re.compile(a) for a in allow] if u == "@allow_urls" else [re.compile(u)])
            out.append({"n": entry["n"], "what": entry["what"], "re": re.compile(entry["re"]), "unless": unless})
        return hidden, out
    except (OSError, ValueError, KeyError, TypeError, re.error) as error:
        raise Unreadable("patterns %s: %s" % (path, error))


def load_terms(path):
    """The deny list's terms: numbered lines in backticks, outside the patterns section (7)."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().split("\n")
    except OSError as error:
        raise Unreadable("terms %s: %s" % (path, error))
    terms, section = [], None
    for line in lines:
        head = SECTION.match(line)
        if head:
            section = int(head.group(1))
            continue
        found = TERM_LINE.match(line)
        if not found or section is None or section >= 7:
            continue
        term, rest = found.group(1).strip(), found.group(2)
        exact = "(exact case)" in rest
        words = r"[\s-]+".join(re.escape(w) for w in term.split())
        rx = re.compile(NOT_LETTER_BEFORE + words + r"(?:s|es|'s|’s|s'|s’|'|’)?" + NOT_LETTER_AFTER,
                        0 if exact else re.IGNORECASE)
        terms.append({"term": term, "re": rx, "section": section})
    if not terms:
        raise Unreadable("terms %s: no terms found" % path)
    return terms


def clean_line(line, hidden):
    return unicodedata.normalize("NFKC", hidden.sub("", line))


def _symbol(ch):
    return bool(ch) and unicodedata.category(ch) in ("So", "Sk")


def _emoji_part(line, i):
    """Whether the hidden character at i is one ordinary emoji use: a joiner between an emoji and a symbol, or the
    emoji presentation selector after a symbol (or after 0-9, # or * when the keycap mark follows)."""
    ch = line[i]
    before = line[i - 1] if i else ""
    after = line[i + 1] if i + 1 < len(line) else ""
    if ch == ZWJ:
        return (_symbol(before) or before == VS16) and _symbol(after)
    if ch == VS16:
        return _symbol(before) or (before in "0123456789#*" and before != "" and after == KEYCAP)
    return False


def hidden_hits(line, hidden):
    """Hidden characters that aren't part of an ordinary emoji."""
    return ["U+%04X" % ord(m.group(0)) for m in hidden.finditer(line) if not _emoji_part(line, m.start())]


def scan_text(name, text, hidden, patterns, terms):
    flags = []
    for number, raw in enumerate(text.split("\n"), 1):
        for code in hidden_hits(raw, hidden):
            pattern = next(p for p in patterns if p.get("hidden"))
            flags.append((name, number, "pattern %d" % pattern["n"], pattern["what"], code))
        line = clean_line(raw, hidden)
        for pattern in patterns:
            if pattern.get("hidden"):
                continue
            for match in pattern["re"].finditer(line):
                if any(u.match(line, match.start()) for u in pattern["unless"]):
                    continue
                flags.append((name, number, "pattern %d" % pattern["n"], pattern["what"], match.group(0)))
        for term in terms or []:
            for match in term["re"].finditer(line):
                flags.append((name, number, "term", "section %d" % term["section"], match.group(0)))
    return flags


def walk(repo):
    """(path, is a symlink) for every file and folder in the repo but .git/ and this scanner's own files. Anything
    else beside them is scanned like the rest."""
    root = os.path.realpath(repo)
    here = os.path.realpath(HERE)
    skip = {os.path.join(root, ".git")}
    skip.update(os.path.join(here, n) for n in OWN_FILES)
    cache = os.path.join(here, "__pycache__")  # only the .pyc files Python writes there are skipped
    out = []
    for folder, dirs, names in os.walk(root):
        keep = []
        for d in sorted(dirs):
            path = os.path.join(folder, d)
            if path in skip:
                continue
            if os.path.islink(path):
                out.append((path, True))
            else:
                keep.append(d)
                out.append((path, False))
        dirs[:] = keep
        for n in sorted(names):
            path = os.path.join(folder, n)
            if folder == cache and n.endswith(".pyc") and not os.path.islink(path):
                continue
            if path not in skip:
                out.append((path, os.path.islink(path)))
    return root, out


def scan(repo, patterns_path, terms_path=None):
    """(flags, problems): flags as (file, line, kind, what, matched) tuples (line 0 is the path's own name),
    problems as (file, why it couldn't be read)."""
    hidden, patterns = load_patterns(patterns_path)
    terms = load_terms(terms_path) if terms_path else None
    flags, problems = [], []
    root, paths = walk(repo)
    for path, link in paths:
        name = os.path.relpath(path, root)
        for _, _, kind, what, matched in scan_text(name, name, hidden, patterns, terms):
            flags.append((name, 0, kind, what, matched))
        if link:
            flags.append((name, 0, "symlink", "a symbolic link", name))
            continue
        if os.path.isdir(path):
            continue
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError as error:
            problems.append((name, str(error)))
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXT or images.kind_of(data):
            try:
                left = images.metadata(data)
            except images.ImageError as error:
                problems.append((name, str(error)))
                continue
            for kind in left:
                flags.append((name, 0, "image", "image metadata", kind))
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append((name, "not UTF-8 text and not an image"))
            continue
        flags.extend(scan_text(name, text, hidden, patterns, terms))
    return flags, problems


def report(flags, problems, show):
    """The lines to print. With show (the terms were given) each flag shows what it matched. Without it, nothing
    matched is shown: a path whose own name was flagged is masked, and so is every file under it."""
    named = {name for name, line, kind, _, _ in flags if line == 0 and kind not in ("image", "symlink")}

    def shown(name):
        if show or not any(name == n or name.startswith(n + os.sep) for n in named):
            return name
        return "(a path whose name is flagged)"

    out = []
    for name, line, kind, what, matched in flags:
        if show:
            out.append("%s:%d: %s (%s): %r" % (name, line, kind, what, matched))
        else:
            out.append("%s:%d: %s" % (shown(name), line,
                                      {"image": "image metadata", "symlink": "a symbolic link"}.get(kind, kind)))
    for name, problem in problems:
        out.append("can't read %s: %s" % (shown(name), problem))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scan a Seeker demo repo for anything that must not be in it.")
    parser.add_argument("repo")
    parser.add_argument("--terms", help="the private deny list (office only); without it, patterns only")
    parser.add_argument("--patterns", default=os.path.join(HERE, "patterns.json"))
    args = parser.parse_args(argv)
    try:
        flags, problems = scan(args.repo, args.patterns, args.terms)
    except Unreadable as error:
        print("scan: can't read %s" % error)
        return 2
    for line in report(flags, problems, bool(args.terms)):
        print(line)
    print("scan: %d flag%s, %d unreadable" % (len(flags), "" if len(flags) == 1 else "s", len(problems)))
    if problems:
        return 2
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main())
