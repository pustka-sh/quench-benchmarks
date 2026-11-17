# Startup

**Measures:** time from process start to a defined ready state, with the same probe agent in every configuration.

- **Client:** the moment the title screen is showing and the loading overlay is gone. That's when a player can first click anything.
- **Dedicated server:** the server's `Done (…)! For help, type "help"` line.

The probe also records:
- CPU time.
- The live heap at that moment: what a full GC leaves, counted from a class histogram. The GC runs after the time is taken.
- Classes loaded.
- When Minecraft's `main`, the resource reload's start and end, and the server's `initServer` were reached.

**Warm start:** each loader keeps its caches between runs, as it would for a player launching the game again. Every configuration gets one unmeasured warm-up run per session first.

**Cold start:** `.quench` and `.fabric` are deleted from the game directory before every run, so the loader rebuilds its caches. The OS file cache stays warm, so this isn't a first launch after a reboot.

**Harness:** `:bench:benchmark`, in `bench/` of [pustka-sh/Quench](https://github.com/pustka-sh/Quench/tree/main/bench). Every configuration launches with exactly the command Tongs writes for it. Fabric's matches what Fabric's installer sets up for the official launcher.
