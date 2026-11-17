#!/usr/bin/env python3
"""Copies one benchmark session from Quench's bench/build/reports folder into results/raw.

Keeps report.md, results.json and every run's JSON as they are, and packs the run logs into
logs.zip. The home folder's path is replaced with "~" everywhere, so a user name in a path
doesn't get published. Uses only the standard library.

    python3 scripts/collect.py <Quench>/bench/build/reports/bench results/raw/<machine>/<date>/01-name --name 01-name
"""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def home_variants() -> list[str]:
    """The home folder as it can appear in logs and JSON: native, forward slashes, JSON-escaped, MSYS."""
    home = str(Path.home())
    variants = {home, home.replace("\\", "/"), home.replace("\\", "\\\\")}
    if len(home) > 2 and home[1] == ":":
        variants.add("/" + home[0].lower() + home[2:].replace("\\", "/"))
    # Longest first, so the JSON-escaped form is replaced before the plain one inside it
    return sorted(variants, key=len, reverse=True)


def scrub(text: str) -> str:
    for variant in home_variants():
        text = text.replace(variant, "~")
    return text


def collect(report: Path, destination: Path, session: dict) -> None:
    if not (report / "results.json").is_file():
        raise SystemExit(f"No results.json in {report}; did the session finish?")
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("report.md", "results.json"):
        (destination / name).write_text(scrub((report / name).read_text(encoding="utf-8")), encoding="utf-8")
    runs = destination / "runs"
    runs.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination / "logs.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as logs:
        for file in sorted((report / "runs").iterdir()):
            text = scrub(file.read_text(encoding="utf-8", errors="replace"))
            if file.suffix == ".json":
                (runs / file.name).write_text(text, encoding="utf-8")
            else:
                logs.writestr(file.name, text)
    (destination / "session.json").write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("report", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--mods", type=int, default=0, help="generated mods the -mods profiles loaded")
    args = parser.parse_args()
    collect(args.report, args.destination, {"name": args.name, "mods": args.mods})


if __name__ == "__main__":
    main()
