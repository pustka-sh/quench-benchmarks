# Quench Benchmarks

Public, reproducible benchmarks for [Quench](https://github.com/pustka-sh/Quench), a mod loader for Minecraft: Java Edition 26.x by [pustka](https://pustka.sh). They compare Quench with vanilla Minecraft, with Fabric Loader, and with Fabric as a player who optimizes it would set it up (Sodium, Lithium, FerriteCore).

Every number here comes with its raw per-run data, the exact conditions it was measured under, and the scripts that turn one into the other. Regressions are published alongside improvements.

> **Status: v1 is being measured.** The [methodology](methodology.md) was written and committed before the first v1 run. Results, summaries and the report will land in [`results/`](results) and [`reports/`](reports).

## What's here

| Path | What it is |
| --- | --- |
| [`methodology.md`](methodology.md) | The protocol: configurations, fixed conditions, primary metrics, success criteria, run counts, exclusion rules, statistics. Written before measuring |
| [`workloads/`](workloads) | What each benchmark does: [startup](workloads/startup), [mod loading](workloads/mod-loading), [client in-game](workloads/client-fps), [server ticks](workloads/server-ticks) |
| [`environments/`](environments) | Notes on each machine, beyond what the harness records itself |
| [`results/raw/`](results/raw) | Every session, as the harness wrote it: `results.json` with every run, each run's own JSON, the logs (`logs.zip`), and the session's report |
| [`results/summaries/`](results/summaries) | Medians, confidence intervals and comparisons, generated from the raw results by `scripts/analyze.py` |
| [`reports/`](reports) | Written reports on what the results show |
| [`scripts/`](scripts) | `run_v1.py` runs the whole protocol, `collect.py` copies a session into `results/raw`, `analyze.py` summarizes. Python 3.10+, standard library only |

## Reproduce it

You need Windows, Linux or macOS with a GPU that runs Minecraft 26.3, Git, Python 3.10 or newer, and a JDK 17+ to run Gradle (Gradle downloads Java 25 for the game if it isn't installed). The first run downloads Minecraft from Mojang. Nothing here redistributes it.

```bash
git clone https://github.com/pustka-sh/quench-benchmarks
git clone --branch v0.1.0-alpha.1 https://github.com/pustka-sh/Quench
cd quench-benchmarks
python3 scripts/run_v1.py --quench ../Quench --machine <short-name> --accept-eula --dry-run   # see the plan
python3 scripts/run_v1.py --quench ../Quench --machine <short-name> --accept-eula
python3 scripts/analyze.py results/raw/<short-name>/<date>
```

`--accept-eula` accepts the [Minecraft EULA](https://aka.ms/MinecraftEULA) for the benchmark servers. The full protocol takes about 4–5 hours. Game windows open and close the whole time, so close other applications and leave the machine alone: a keystroke that reaches a game window ends an in-game run on the pause screen. Use a high-performance power plan. `--only <session>` runs a single session, and `--startup-runs`, `--world-runs` and `--cold-runs` take smaller counts for a quicker look. Results with fewer runs than the protocol's should say so.

To contribute your results, open a pull request that adds:
- your `results/raw/<machine>/<date>` folder
- the summary `analyze.py` wrote
- a note in [`environments/`](environments), from [`TEMPLATE.md`](environments/TEMPLATE.md)

The collector replaces your home folder's path with `~` in everything it copies, but look through the files before you publish them. Results that disagree with ours are just as welcome.

## Ground rules

- Quench doesn't run Fabric mods. Comparisons with mods use [generated mods](workloads/mod-loading), built once for each loader.
- Every metric is reported on its own. Lower memory, faster startup and higher FPS are different results, and no percentages are averaged into one score.
- A difference only counts as **clear** when its 95% confidence interval excludes zero.
- Absolute times drift between sessions and days, so configurations are only compared within one session.
- One machine is one data point. The results don't generalize until other machines reproduce them.

## License

The scripts and documents in this repository are under the [MIT License](LICENSE). Minecraft is a trademark of Mojang Synergies AB. This project is not affiliated with Mojang or Microsoft, nor with the Fabric, Sodium, Lithium or FerriteCore projects.
