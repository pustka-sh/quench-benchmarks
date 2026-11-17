# Mod loading

Quench doesn't run Fabric mods, so real modpacks can't be run on both loaders. The mod workloads are **generated** instead, from one template mod, by `:bench:mods` in [pustka-sh/Quench](https://github.com/pustka-sh/Quench/tree/main/bench/mods).

Each generated mod has:
- 10 blocks, each with its item, blockstate, block model and a 16×16 texture
- 5 items, each with a generated item model and a texture with a transparent edge
- 40 classes it loads as it starts, as a real mod loads its registries, handlers and config
- 3 Mixins: one into every block's constructor, one into the title screen, and one into each client tick

200 mods come to 3,000 blocks and items, 3,000 textures, 9,000 classes and 600 Mixins, in 24 MB of jars. The 50-mod set is the 200-mod set's first 50, byte for byte. The same settings always write the same bytes, and each session's `results.json` records a SHA-256 for every jar.

**Quench build:** each jar has a `quench.mod.json` and an entrypoint implementing Quench's initializer.

**Fabric build:** the same classes, assets and Mixins, with a `fabric.mod.json` and an entrypoint implementing Fabric's `ModInitializer`, whose `onInitialize()` is the same. Fabric API 0.166.2+26.3 sits beside them, since almost every Fabric mod needs it and every Fabric pack has it.

**Optimized Fabric build:** the Fabric build plus Sodium, Lithium and FerriteCore.

**What it stands for:** each loader's cost to discover, read, transform and register mod content. It doesn't stand for the runtime work of any particular real mod.
