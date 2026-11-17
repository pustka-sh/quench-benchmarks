#!/usr/bin/env python3
"""Runs the Quench Benchmarks v1 protocol (methodology.md) and collects every run into results/raw.

Needs Python 3.10+, git, and a checkout of Quench at the release being measured:

    git clone --branch v0.1.0-alpha.1 https://github.com/pustka-sh/Quench
    python3 scripts/run_v1.py --quench ../Quench --accept-eula

Game windows open and close for several hours. Leave the machine alone while it runs: a keystroke
that reaches a game window can end an in-game run on the pause screen. Uses only the standard library.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect  # noqa: E402  (sibling script)

ZERO_MOD_CLIENT = ["vanilla", "quench", "quench-vanilla-fade", "fabric", "fabric-optimized"]
ZERO_MOD = ["vanilla", "quench", "fabric", "fabric-optimized"]
WITH_MODS = ["quench-mods", "fabric-mods", "fabric-optimized-mods"]


def sessions(startup_runs: int, world_runs: int, cold_runs: int, world_seconds: int) -> list[dict]:
    """The v1 sessions in order. The server session comes before the in-game ones because it
    creates the world the in-game benchmark world is generated from, and in-game-0 comes before
    in-game-50 so that vanilla, its first profile, generates that world when it doesn't exist yet."""
    return [
        {"name": "client-startup-50", "mods": 50, "profiles": ZERO_MOD_CLIENT + WITH_MODS, "sides": "client", "runs": startup_runs},
        {"name": "server-startup", "mods": 0, "profiles": ZERO_MOD, "sides": "server", "runs": startup_runs},
        {"name": "in-game-0", "mods": 0, "profiles": ZERO_MOD, "world": world_seconds, "runs": world_runs},
        {"name": "in-game-50", "mods": 50, "profiles": WITH_MODS, "world": world_seconds, "runs": world_runs},
        {"name": "client-startup-200", "mods": 200, "profiles": WITH_MODS, "sides": "client", "runs": startup_runs},
        {"name": "client-cold-200", "mods": 200, "profiles": ["quench", "fabric", "fabric-optimized"] + WITH_MODS,
         "sides": "client", "runs": cold_runs, "cold": True},
    ]


def gradle(quench: Path, *args: str) -> None:
    wrapper = quench / ("gradlew.bat" if os.name == "nt" else "gradlew")
    command = [str(wrapper), "--console=plain", *args]
    print("$", " ".join(command[1:]), flush=True)
    subprocess.run(command, cwd=quench, check=True)


def generated_mods(quench: Path, count: int) -> None:
    gradle(quench, ":bench:mods:generateMods", ":bench:mods:generateFabricMods", ":bench:mods:generateOptimizedFabricMods",
           f"-Pbench.mods={count}")


def revision(quench: Path) -> str:
    result = subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=quench, capture_output=True, text=True)
    return result.stdout.strip() or "unknown"


def preflight(quench: Path, expected: str | None) -> None:
    if not (quench / "bench" / "build.gradle.kts").is_file():
        sys.exit(f"{quench} isn't a Quench checkout (no bench/build.gradle.kts)")
    found = revision(quench)
    print(f"Quench checkout: {quench} at {found}")
    if found.endswith("-dirty"):
        print("  warning: the checkout has uncommitted changes; results won't match a published build")
    if expected and found != expected:
        print(f"  warning: expected {expected}; pass --expect '' to skip this check")
    if platform.system() == "Windows":
        plan = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True).stdout
        if "High performance" not in plan and "Ultimate" not in plan:
            print("  warning: the active power plan isn't High performance:", plan.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quench", type=Path, required=True, help="path to a Quench checkout")
    parser.add_argument("--machine", default=platform.node().lower() or "machine",
                        help="folder name for this machine under results/raw (default: the host name)")
    parser.add_argument("--expect", default="v0.1.0-alpha.1", help="the git tag the checkout should be at")
    parser.add_argument("--accept-eula", action="store_true",
                        help="accept the Minecraft EULA (https://aka.ms/MinecraftEULA) for the benchmark servers; needed")
    parser.add_argument("--startup-runs", type=int, default=25)
    parser.add_argument("--world-runs", type=int, default=20)
    parser.add_argument("--cold-runs", type=int, default=10)
    parser.add_argument("--world-seconds", type=int, default=30)
    parser.add_argument("--only", nargs="*", help="run only these sessions, by name")
    parser.add_argument("--out", type=Path, help="results folder (default: results/raw/<machine>/<date>)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    args = parser.parse_args()
    if not args.accept_eula:
        sys.exit("The server sessions run a Minecraft server, which needs the Minecraft EULA accepted "
                 "(https://aka.ms/MinecraftEULA). Pass --accept-eula to accept it.")

    quench = args.quench.resolve()
    plan = sessions(args.startup_runs, args.world_runs, args.cold_runs, args.world_seconds)
    if args.only:
        plan = [s for s in plan if s["name"] in args.only]
    out = (args.out or REPO / "results" / "raw" / args.machine / dt.date.today().isoformat()).resolve()
    print(f"{len(plan)} sessions into {out}:")
    for i, session in enumerate(plan, 1):
        kind = f"{session['world']} s in the world" if session.get("world") else ("cold" if session.get("cold") else "warm") + f" {session['sides']} start"
        print(f"  {i}. {session['name']}: {', '.join(session['profiles'])}; {session['runs']} runs, {kind}, {session['mods']} generated mods")
    if args.dry_run:
        return
    preflight(quench, args.expect or None)

    started = time.monotonic()
    generated = None
    for i, session in enumerate(plan, 1):
        print(f"\n=== {i}/{len(plan)} {session['name']} ===", flush=True)
        # Sessions without -mods profiles don't load the generated mods, so whatever is generated stays
        if session["mods"] and generated != session["mods"]:
            generated_mods(quench, session["mods"])
            generated = session["mods"]
        world = session.get("world", 0)
        report = quench / "bench" / "build" / "reports" / ("bench-world" if world else "bench")
        shutil.rmtree(report, ignore_errors=True)
        options = [f"-Pbench.profiles={','.join(session['profiles'])}", f"-Pbench.runs={session['runs']}", "-Pbench.acceptEula=true"]
        if world:
            options.append(f"-Pbench.world={world}")
        else:
            options.append(f"-Pbench.sides={session['sides']}")
        if session.get("cold"):
            options.append("-Pbench.cold=true")
        gradle(quench, ":bench:benchmark", *options)
        destination = out / f"{i:02d}-{session['name']}"
        collect.collect(report, destination, {
            "name": session["name"],
            "mods": session["mods"],
            "protocol": "v1",
            "quenchRevision": revision(quench),
            "collectedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        })
        print(f"Collected into {destination} ({(time.monotonic() - started) / 60:.0f} min so far)", flush=True)

    print(f"\nDone in {(time.monotonic() - started) / 3600:.1f} h. Summarize with:\n  python3 scripts/analyze.py {out}")


if __name__ == "__main__":
    main()
