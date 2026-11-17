#!/usr/bin/env python3
"""Summarizes a results folder written by run_v1.py, as methodology.md defines it.

For every configuration and metric: runs, median with a distribution-free 95% confidence
interval, interquartile range, minimum and maximum. For every comparison: the change in medians
by the plan's formulas, with a bootstrap 95% confidence interval. Then the pre-registered success
criteria. Uses only the standard library, so anyone can check the numbers.

    python3 scripts/analyze.py results/raw/<machine>/<date> [--out results/summaries/<machine>-<date>]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20261116
MIB = 1024 * 1024


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    lower_is_better: bool
    unit: str
    scale: float = 1.0
    value: Callable[[dict], float | None] | None = None

    def of(self, values: dict) -> float | None:
        raw = self.value(values) if self.value else values.get(self.key)
        if raw is None or raw < 0:
            return None
        return raw / self.scale

    def format(self, x: float) -> str:
        if math.isnan(x):
            return "n/a"
        if self.unit == "s":
            return f"{x:.2f} s"
        if self.unit == "ms":
            return f"{x:.2f} ms"
        if self.unit == "MiB":
            return f"{x:.1f} MiB"
        if self.unit == "fps":
            return f"{x:.0f}"
        return f"{x:,.0f}"


def phase(end: str, start: str | None) -> Callable[[dict], float | None]:
    def value(values: dict) -> float | None:
        phases = values.get("phases") or {}
        stop = values.get("startToMarkMs") if end == "end" else phases.get(end)
        begin = 0 if start is None else phases.get(start)
        return None if stop is None or begin is None else stop - begin
    return value


STARTUP = [
    Metric("startToMarkMs", "Start to marker", True, "s", 1000),
    Metric("cpuTimeMs", "CPU time", True, "s", 1000),
    Metric("liveHeapBytes", "Live heap at marker", True, "MiB", MIB),
    Metric("loadedClasses", "Classes loaded", True, ""),
]
CLIENT_PHASES = [
    Metric("phaseMain", "Start → main", True, "s", 1000, phase("main", None)),
    Metric("phaseBoot", "main → resource reload", True, "s", 1000, phase("reloadStart", "main")),
    Metric("phaseReload", "Resource reload", True, "s", 1000, phase("reloadDone", "reloadStart")),
    Metric("phaseFade", "Reload done → title screen", True, "s", 1000, phase("end", "reloadDone")),
]
SERVER_PHASES = [
    Metric("phaseMain", "Start → main", True, "s", 1000, phase("main", None)),
    Metric("phaseInit", "main → initServer", True, "s", 1000, phase("initServer", "main")),
    Metric("phaseDone", "initServer → Done", True, "s", 1000, phase("end", "initServer")),
]
WORLD = [
    Metric("worldJoinMs", "Start → in the world", True, "s", 1000),
    Metric("worldLoadMs", "World load", True, "s", 1000),
    Metric("fps", "Average FPS", False, "fps"),
    Metric("onePercentLowFps", "Slowest 1% FPS", False, "fps"),
    Metric("frameMsP99", "Frame time, 99th percentile", True, "ms"),
    Metric("msptAvg", "Milliseconds per tick, mean", True, "ms"),
    Metric("msptP95", "Milliseconds per tick, 95th percentile", True, "ms"),
    Metric("cpuInWorldMs", "CPU time while playing", True, "s", 1000),
    Metric("liveHeapBytes", "Live heap after playing", True, "MiB", MIB),
]

# (candidate, baseline) pairs, compared when both ran in a session
COMPARISONS = [
    ("quench", "fabric"), ("quench", "fabric-optimized"), ("quench", "vanilla"),
    ("quench-vanilla-fade", "fabric"), ("fabric", "vanilla"), ("fabric-optimized", "vanilla"),
    ("quench-mods", "fabric-mods"), ("quench-mods", "fabric-optimized-mods"),
]


def median_ci(sorted_values: list[float]) -> tuple[float, float]:
    """A distribution-free 95% confidence interval for the median, from binomial order statistics."""
    n = len(sorted_values)
    if n < 6:
        return math.nan, math.nan  # too few runs for a 95% interval
    # The largest k with P(Binomial(n, 1/2) < k) <= 0.025; the interval is [x(k), x(n-k+1)], 1-indexed
    cumulative, k = 0.0, 0
    while True:
        next_cumulative = cumulative + math.comb(n, k) / 2 ** n
        if next_cumulative > 0.025:
            break
        cumulative, k = next_cumulative, k + 1
    k = max(k, 1)
    return sorted_values[k - 1], sorted_values[n - k]


def describe(values: list[float]) -> dict:
    ordered = sorted(values)
    if not ordered:
        return {"n": 0}
    q1, _, q3 = statistics.quantiles(ordered, n=4, method="inclusive") if len(ordered) > 1 else (ordered[0],) * 3
    low, high = median_ci(ordered)
    return {"n": len(ordered), "median": statistics.median(ordered), "ciLow": low, "ciHigh": high,
            "q1": q1, "q3": q3, "min": ordered[0], "max": ordered[-1]}


def improvement(candidate: float, baseline: float, lower_is_better: bool) -> float:
    """The plan's formulas: positive means the candidate is better."""
    if lower_is_better:
        return (baseline - candidate) / baseline * 100
    return (candidate - baseline) / baseline * 100


def compare(candidate: list[float], baseline: list[float], lower_is_better: bool, rng: random.Random) -> dict:
    point = improvement(statistics.median(candidate), statistics.median(baseline), lower_is_better)
    samples = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        c = statistics.median(rng.choices(candidate, k=len(candidate)))
        b = statistics.median(rng.choices(baseline, k=len(baseline)))
        samples.append(improvement(c, b, lower_is_better))
    samples.sort()
    low = samples[int(0.025 * BOOTSTRAP_RESAMPLES)]
    high = samples[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]
    return {"percent": point, "ciLow": low, "ciHigh": high, "clear": low > 0 or high < 0}


def load(session_dir: Path) -> dict:
    results = json.loads((session_dir / "results.json").read_text(encoding="utf-8"))
    meta_file = session_dir / "session.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.is_file() else {"name": session_dir.name, "mods": 0}
    options = results.get("session", {}).get("options", {})
    world = options.get("worldSeconds", 0) > 0
    runs: dict[str, list[dict]] = {}
    failures: dict[str, list[str]] = {}
    for run in results["runs"]:
        config = run["profile"].removesuffix("-" + run["side"])
        if "values" in run:
            runs.setdefault(config, []).append(run["values"])
        else:
            failures.setdefault(config, []).append(f"run {run['run']}: {run.get('failure')}")
    sides = {run["side"] for run in results["runs"]}
    if world:
        metrics = WORLD
    elif sides == {"server"}:
        metrics = STARTUP + SERVER_PHASES
    else:
        metrics = STARTUP + CLIENT_PHASES
    return {"dir": session_dir, "meta": meta, "results": results, "world": world, "cold": options.get("cold", False),
            "side": "client" if world else "/".join(sorted(sides)), "runs": runs, "failures": failures, "metrics": metrics}


def label(config: str, mods: int) -> str:
    return f"{config} ({mods} mods)" if config.endswith("-mods") else config


def summarize(session: dict, rng: random.Random) -> dict:
    out = {"name": session["meta"]["name"], "mods": session["meta"].get("mods", 0), "world": session["world"],
           "cold": session["cold"], "side": session["side"], "configs": {}, "comparisons": [], "failures": session["failures"]}
    for config, runs in session["runs"].items():
        out["configs"][config] = {m.key: describe([v for r in runs if (v := m.of(r)) is not None]) for m in session["metrics"]}
    for candidate, baseline in COMPARISONS:
        if candidate not in session["runs"] or baseline not in session["runs"]:
            continue
        for metric in session["metrics"]:
            c = [v for r in session["runs"][candidate] if (v := metric.of(r)) is not None]
            b = [v for r in session["runs"][baseline] if (v := metric.of(r)) is not None]
            if len(c) < 2 or len(b) < 2:
                continue
            out["comparisons"].append({"candidate": candidate, "baseline": baseline, "metric": metric.key,
                                       **compare(c, b, metric.lower_is_better, rng)})
    return out


def find(summaries: list[dict], *, world: bool, side: str, cold: bool = False, mods: int | None = None) -> list[dict]:
    return [s for s in summaries if s["world"] == world and s["side"] == side and s["cold"] == cold
            and (mods is None or s["mods"] == mods)]


def comparison(summary: dict, candidate: str, baseline: str, metric: str) -> dict | None:
    return next((c for c in summary["comparisons"]
                 if c["candidate"] == candidate and c["baseline"] == baseline and c["metric"] == metric), None)


def verdict_better(c: dict | None) -> str:
    if c is None:
        return "not measured"
    return "met" if c["ciLow"] > 0 else "not met" if c["ciHigh"] < 0 else "inconclusive"


def verdict_noise(c: dict | None) -> str:
    if c is None:
        return "not measured"
    return "met" if (c["ciLow"] <= 0 <= c["ciHigh"]) or abs(c["percent"]) < 2 else "not met"


def criteria(summaries: list[dict]) -> list[dict]:
    """The pre-registered success criteria from methodology.md."""
    rows = []
    for summary in find(summaries, world=False, side="client"):
        for config, baseline, mods in (("quench", "fabric", 0), ("quench-mods", "fabric-mods", summary["mods"])):
            stats = summary["configs"].get(config, {}).get("startToMarkMs")
            if not stats or not stats.get("n") or any(r["what"].startswith("P1") and r["mods"] == mods for r in rows):
                continue
            under = stats["median"] < 20
            faster = verdict_better(comparison(summary, config, baseline, "startToMarkMs"))
            verdict = "met" if under and faster == "met" else "not met" if not under or faster == "not met" else "inconclusive"
            rows.append({"what": "P1: title screen under 20 s and sooner than fabric", "mods": mods,
                         "detail": f"{stats['median']:.2f} s; sooner than {baseline}: {faster}", "verdict": verdict})
    for summary in find(summaries, world=True, side="client"):
        config, baseline = ("quench-mods", "fabric-mods") if summary["mods"] else ("quench", "fabric")
        c = comparison(summary, config, baseline, "liveHeapBytes")
        rows.append({"what": "P2: live heap after playing below fabric", "mods": summary["mods"],
                     "detail": fmt_change(c), "verdict": verdict_better(c)})
        if not summary["mods"]:
            c = comparison(summary, "quench", "vanilla", "msptAvg")
            rows.append({"what": "P3: mean milliseconds per tick within noise of vanilla", "mods": 0,
                         "detail": fmt_change(c), "verdict": verdict_noise(c)})
            c = comparison(summary, "quench", "vanilla", "fps")
            rows.append({"what": "P4: average FPS within noise of vanilla", "mods": 0,
                         "detail": fmt_change(c), "verdict": verdict_noise(c)})
    for summary in find(summaries, world=False, side="server"):
        c = comparison(summary, "quench", "fabric", "startToMarkMs")
        verdict = "not measured" if c is None else "met" if c["ciLow"] >= 30 else "not met" if c["ciHigh"] < 30 else "inconclusive"
        rows.append({"what": "P5: dedicated server Done at least 30% sooner than fabric", "mods": 0,
                     "detail": fmt_change(c), "verdict": verdict})
    return rows


def fmt_change(c: dict | None) -> str:
    if c is None:
        return "n/a"
    return f"{c['percent']:+.1f}% [{c['ciLow']:+.1f}, {c['ciHigh']:+.1f}]"


def markdown(summaries: list[dict], sessions: list[dict], root: Path) -> str:
    first = sessions[0]["results"]
    machine = first.get("session", {}).get("machine", {})
    gpus = ", ".join(f"{g.get('Name')} (driver {g.get('DriverVersion')})" for g in machine.get("gpus", []) if isinstance(g, dict))
    lines = [f"# Quench Benchmarks v1: {root.parent.name}, {root.name}", "",
             f"Machine: {machine.get('summary', first.get('machine'))}" + (f"; GPUs: {gpus}" if gpus else ""),
             f"OS: {machine.get('osBuild', machine.get('os', 'unknown'))}; power plan: {machine.get('powerPlan', 'unknown')}",
             f"Minecraft {first.get('minecraft')}, Java {first.get('java')}; Quench revision {first.get('session', {}).get('revision', 'unknown')}", "",
             "Generated by `scripts/analyze.py` from the raw results next to this summary's source folder. "
             "Medians with distribution-free 95% confidence intervals; changes are the plan's formulas on medians "
             f"(positive = the first configuration is better), with bootstrap 95% intervals ({BOOTSTRAP_RESAMPLES:,} resamples). "
             "A change is **clear** when its interval excludes zero.", "",
             "## Success criteria (pre-registered)", "", "| Criterion | Mods | Result | Verdict |", "| --- | --- | --- | --- |"]
    for row in criteria(summaries):
        lines.append(f"| {row['what']} | {row['mods']} | {row['detail']} | **{row['verdict']}** |")
    for summary, session in zip(summaries, sessions):
        metrics = {m.key: m for m in session["metrics"]}
        kind = (f"in the world, {session['results']['session']['options']['worldSeconds']} s" if summary["world"]
                else f"{'cold' if summary['cold'] else 'warm'} {summary['side']} start")
        runs = session["results"]["session"]["options"]["runs"]
        lines += ["", f"## {summary['name']}: {kind}, {summary['mods']} generated mods, {runs} runs per configuration", ""]
        configs = list(summary["configs"])
        lines += ["| Metric | " + " | ".join(label(c, summary["mods"]) for c in configs) + " |",
                  "| --- |" + " --- |" * len(configs)]
        for key, metric in metrics.items():
            cells = []
            for config in configs:
                s = summary["configs"][config][key]
                if not s.get("n"):
                    cells.append("n/a")
                    continue
                ci = "" if math.isnan(s["ciLow"]) else f" [{metric.format(s['ciLow'])}–{metric.format(s['ciHigh'])}]"
                cells.append(f"{metric.format(s['median'])}{ci}")
            lines.append(f"| {metric.label} | " + " | ".join(cells) + " |")
        counts = [f"{summary['configs'][c]['startToMarkMs' if not summary['world'] else 'fps']['n']}" for c in configs]
        lines.append("| Runs measured | " + " | ".join(counts) + " |")
        failed = [len(summary["failures"].get(c, [])) for c in configs]
        lines.append("| Runs failed | " + " | ".join(str(f) for f in failed) + " |")
        if summary["comparisons"]:
            lines += ["", "| Comparison | Metric | Change [95% CI] | Clear? |", "| --- | --- | --- | --- |"]
            for c in summary["comparisons"]:
                metric = metrics[c["metric"]]
                lines.append(f"| {label(c['candidate'], summary['mods'])} vs {label(c['baseline'], summary['mods'])} | {metric.label} | "
                             f"{fmt_change(c)} | {'yes' if c['clear'] else 'no'} |")
        if summary["failures"]:
            lines += ["", "Failed runs:", ""]
            for config, reasons in summary["failures"].items():
                lines += [f"- {config}, {reason}" for reason in reasons]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path, help="a results/raw/<machine>/<date> folder")
    parser.add_argument("--out", type=Path, help="writes <out>.md and <out>.json (default: results/summaries/<machine>-<date>)")
    args = parser.parse_args()
    root = args.results.resolve()
    session_dirs = sorted(d for d in root.iterdir() if (d / "results.json").is_file())
    if not session_dirs:
        raise SystemExit(f"No sessions in {root}")
    sessions = [load(d) for d in session_dirs]
    rng = random.Random(BOOTSTRAP_SEED)
    summaries = [summarize(s, rng) for s in sessions]
    out = args.out or Path(__file__).resolve().parent.parent / "results" / "summaries" / f"{root.parent.name}-{root.name}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".md").write_text(markdown(summaries, sessions, root), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps({"sessions": summaries, "criteria": criteria(summaries)}, indent=2, default=str) + "\n",
                                        encoding="utf-8")
    print(f"Wrote {out.with_suffix('.md')} and {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
