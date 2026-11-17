# Methodology: Quench Benchmarks v1

**Written 2026-11-16, before any v1 measurement was taken.** The metrics, success criteria, run counts and exclusion rules below were fixed first and committed before the runs. Anything changed after measuring is listed under [Changes after measuring](#changes-after-measuring), with the reason.

## What is compared

| Configuration | What it is |
| --- | --- |
| `vanilla` | Minecraft 26.3, unmodified, started the way the official launcher starts it |
| `quench` | The same game started through Quench, with no mods |
| `quench-vanilla-fade` | `quench` with vanilla's 2-second loading-screen fade (`-Dquench.loadingScreen=vanilla`) instead of Quench's 0.3 s. It only changes the fade, and shows how much of Quench's startup lead is the shorter fade |
| `fabric` | The same game started through Fabric Loader 0.20.1, set up the way Fabric's installer sets it up, with no mods |
| `fabric-optimized` | `fabric` with the optimization mods a Fabric player most often installs: Fabric API 0.166.2+26.3, Sodium 0.9.3-beta.5, Lithium 0.26.3 and FerriteCore 9.0.0 |
| `quench-mods` | `quench` with N generated test mods (see [Workloads](#workloads)) |
| `fabric-mods` | `fabric` with the same N generated mods built for Fabric, plus Fabric API, which Fabric mods need for their assets and data to load |
| `fabric-optimized-mods` | `fabric-mods` plus Sodium, Lithium and FerriteCore |

Every optimization mod is pinned to an exact version and checked against the SHA-512 that Modrinth lists for it before every session. ModernFix, which often appears on Fabric optimization lists, has no build for 26.3 and isn't included.

**Quench does not run Fabric mods.** It is a separate loader with its own mod format (`quench.mod.json`). Real Fabric modpacks therefore can't be run on both loaders, so the mod workloads are generated: the same classes, assets and Mixins, packaged once for each loader. See [Known differences](#known-differences-between-configurations).

## Fixed conditions

These are the same for every configuration within a session, and are recorded in each session's `results.json`:

- **Hardware and OS:** one machine per results folder; CPU, RAM, GPUs with driver versions, display mode, OS build and the active power plan are recorded automatically.
- **Minecraft and Java:** Minecraft 26.3; the same Java 25 runtime for every configuration.
- **JVM arguments:** the client gets the official launcher's arguments for 26.3 (`-Xms2G -Xmx4G -XX:+UseZGC`, compact object headers, pre-touched heap, string deduplication). The dedicated server gets no heap or GC flags, so it uses the JVM's defaults (G1). Each profile's exact command is recorded.
- **Loader builds:** Quench is built from a tagged commit, and the commit is recorded. A SHA-256 of every jar on each profile's classpath and in its mods folder is recorded too.
- **Network:** Mojang's online services are made unreachable, so the offline test account's lookups fail at once instead of adding 0–3 seconds at random. A real player with an account also waits on these lookups.
- **In-game settings:** a 1280×720 window, no frame cap, no VSync, view and simulation distance 12, music off, no pausing when the window loses focus.
- **World:** one world with a fixed seed. It is generated once, with the time of day, weather and mob spawning frozen, and every configuration starts each session from a copy of it, at the same spot. During every in-game run the camera turns one full circle along the horizon, so every run renders the same views.
- **Machine state:** high-performance power plan, no other applications open, and nobody using the machine while the benchmark runs.

## Workloads

- **Startup:** process start to the title screen, the moment the loading overlay is gone (client), or to the server's "Done" line (dedicated server).
- **Generated mods:** each mod has 10 blocks (each with an item, blockstate, model and texture), 5 items with textures, 40 classes it loads as it starts, and 3 Mixins (one into every block's constructor, one into the title screen, one into each client tick). The 50-mod set is the first 50 of the 200-mod set, byte for byte. Details: [workloads/mod-loading](workloads/mod-loading).
- **In-game:** the client starts straight into the benchmark world with quick play and plays 30 seconds from the moment the world loading screen closes. Details: [workloads/client-fps](workloads/client-fps), [workloads/server-ticks](workloads/server-ticks).

## Primary metrics

Each primary metric compares `quench` with `fabric` and with `fabric-optimized` (or the `-mods` versions of each).

| # | Metric | Direction | Mod counts | Runs per configuration |
| --- | --- | --- | --- | --- |
| P1 | Client, warm start: time to the title screen | lower is better | 0, 50, 200 | 25 |
| P2 | Live heap after 30 s in the world (what a full GC leaves, counted from a class histogram) | lower is better | 0, 50 | 20 |
| P3 | Integrated server, milliseconds per tick over 30 s in the world: mean and 95th percentile | lower is better | 0, 50 | 20 |
| P4 | Frames per second over 30 s in the world: average, and the average of the slowest 1% of frames | higher is better | 0, 50 | 20 |
| P5 | Dedicated server, warm start: time to "Done" | lower is better | 0 | 25 |

**Secondary metrics:** cold start (Quench's and Fabric's caches deleted before every run, 10 runs); process start to in the world; world load time; CPU time; live heap at the title screen; classes loaded; the startup phases (start → Minecraft's `main` → resource reload → loading overlay gone); 99th-percentile frame time.

**Not measured in v1:** chunk-loading throughput; ticks on the dedicated server; the dedicated server with mods; frame times from an external capture tool such as PresentMon. Frame rate comes from the time between consecutive frames in the client's render loop, measured inside the game.

## Success criteria

Fixed before measuring, taken from Quench's design goals:

1. **P1:** Quench reaches the title screen in under 20 seconds at 0, 50 and 200 mods, and sooner than `fabric` at every count.
2. **P2:** Quench's live heap after playing is lower than `fabric`'s at 0 and 50 mods.
3. **P3:** Quench's mean milliseconds per tick are within measurement noise of `vanilla`'s at 0 mods. That means the 95% confidence interval of the difference includes zero, or the difference is under 2%.
4. **P4:** Quench's average FPS is within measurement noise of `vanilla`'s at 0 mods, by the same test.
5. **P5:** Quench's dedicated server reaches "Done" at least 30% sooner than `fabric`'s.

Each criterion is reported as **met**, **not met** or **inconclusive**. Inconclusive means the confidence interval doesn't settle it. Results against `fabric-optimized` are reported in full, but they have no pass mark. They answer a different question: is Quench still ahead of what an optimizing player would actually run?

## Procedure

1. Build every configuration from the recorded Quench commit. The optimization mods are checked against their pinned hashes.
2. Before each session, run every configuration once as a warm-up, unmeasured. This fills the OS file cache and the loaders' own caches, and creates the server worlds.
3. Measured runs go in rounds of one run per configuration. **Within each round the order is shuffled**, from a seed that is recorded, so no configuration always runs first or always follows the same other one.
4. Warm and cold startup are separate sessions. Cold runs delete `.quench` and `.fabric` in the game directory before every run; the OS file cache stays warm.
5. Session order on the reference machine:
   1. Client startup, warm, 25 runs: `vanilla`, `quench`, `quench-vanilla-fade`, `fabric`, `fabric-optimized`, plus `quench-mods`, `fabric-mods` and `fabric-optimized-mods` with 50 mods.
   2. Dedicated server startup, warm, 25 runs: `vanilla`, `quench`, `fabric`, `fabric-optimized`. This also creates the world the in-game sessions start from.
   3. In-game, 30 s, 20 runs: `vanilla`, `quench`, `fabric`, `fabric-optimized`. If the benchmark world doesn't exist yet, `vanilla` generates it first.
   4. In-game, 30 s, 20 runs: the three `-mods` configurations with 50 mods. Their warm-up run also lets Quench record the world's new mod list, so no measured run makes Anneal's one-time backup.
   5. Client startup, warm, 25 runs: the three `-mods` configurations with 200 mods.
   6. Client startup, cold, 10 runs: `quench`, `fabric`, `fabric-optimized` and the three `-mods` configurations with 200 mods.

   [`scripts/run_v1.py`](scripts/run_v1.py) runs exactly this list.
6. Keep every run, including failures, with its log.

## Exclusion rules

- A run is excluded only if it **failed**: it crashed, timed out after 300 s, ended on a screen other than the title screen (startup), or ended on any screen while it was supposed to be in the world (in-game, such as the pause screen when a keystroke reached the window).
- Every failed run is listed with its reason in the session's report and kept in `results.json` and the run logs.
- **No outliers are removed.** Slow runs that succeeded stay in.
- If a configuration has more than 10% failed runs in a session, the session is re-run and both sessions are published.

## Statistics

- **The unit is one run.** Frame and tick statistics are first summarized within each run (average FPS, slowest-1% FPS, mean and 95th-percentile tick). The run-level values are then compared across runs. Thousands of frames from one run are not treated as thousands of samples.
- **Per configuration:** sample count, median, interquartile range, minimum and maximum, and a distribution-free 95% confidence interval for the median, from binomial order statistics.
- **Comparisons:** the plan's formulas, on medians:
  - lower is better: `reduction % = (Fabric − Quench) / Fabric × 100`
  - higher is better: `gain % = (Quench − Fabric) / Fabric × 100`

  The 95% confidence interval of each percentage comes from a bootstrap: 10,000 resamples of each configuration's runs, percentile method, fixed seed.
- **"Clear" difference:** one whose confidence interval doesn't include zero.
- No percentages from different metrics are averaged into one score.
- Comparisons are only made within a session. Absolute times drift by a few percent between sessions and days on the same machine.

## Known differences between configurations

- **Different mod formats:** the generated mods are the same bytecode, assets and Mixins, with a `quench.mod.json` or a `fabric.mod.json` and the matching entrypoint interface. They stand in for real mods. They measure each loader's cost for discovering, loading, transforming and registering mod content, not the behavior of any particular real mod.
- **Fabric API in the Fabric mod configurations:** almost every Fabric mod needs Fabric API, so the Fabric mod configurations include it. On its own it adds startup time and memory. The `fabric` configuration, without mods, doesn't have it.
- **Loading-screen fade:** Quench fades the loading screen out over 0.3 s; vanilla and Fabric take 2 s. Waiting through the fade is real time for a player, so it's included in P1. `quench-vanilla-fade` shows the result without that difference.
- **Rendering:** Quench has no rendering optimizations yet. Comparing FPS with `fabric-optimized` mostly compares vanilla's renderer with Sodium's.
- **Garbage collector:** the client runs ZGC, as the official launcher sets it. Earlier testing found Quench's integrated-server ticks slower than vanilla's under ZGC but not under G1; that cause is still open. v1 reports ticks as measured.
- **One machine:** v1 is measured on one machine. The results don't generalize until other machines reproduce them; see [README](README.md#reproduce-it).

## Changes after measuring

**2026-11-17: the 50-mod sessions ran with 200 mods.** `run_v1.py` generated 50 mods, then started the benchmark without passing the mod count. The benchmark's launch profiles regenerate their mods as a build dependency, with the default count of 200. So on the first machine, sessions `01-client-startup-50` and `04-in-game-50` loaded 200 generated mods. Their `results.json` lists all 200 jars, with checksums, for every `-mods` configuration. Their data is kept and published, relabeled as 200-mod data in each `session.json`, with the original plan noted. The runner now passes the count to the benchmark too, and both sessions were run again with 50 mods. The 0-mod configurations in session 1 were unaffected.

**2026-11-17: in-game session with no mods, re-run.** 11 of its 80 runs ended on the pause screen instead of in the world: `quench` 4 of 20, `fabric-optimized` 3, `vanilla` 2, `fabric` 2. All 11 started between 22:19 and 22:27 or at 22:34 local time (UTC−5), while someone was typing on the machine, and each new game window takes the keyboard focus. Two configurations exceed the 10% limit in the [exclusion rules](#exclusion-rules), so the session was run again, and both sessions are published. In-game with mods had at most 2 of 20 failures per configuration (at 22:38 and between 23:08 and 23:13, also while the machine was in use), which is within the limit.
