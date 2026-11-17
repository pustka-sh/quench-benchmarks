# Client in-game

Each run starts the client straight into the benchmark world with quick play, in a 1280×720 window, and plays **30 seconds** from the moment the world loading screen closes. Meanwhile the camera turns one full circle along the horizon, so every run renders the same views. Then the game quits the way a player does, which saves the world.

**The world:** generated once by a 60-second run from a fixed seed, with the time of day fixed at noon, the weather clear and mob spawning off. That keeps the same 127–130 entities in every configuration's copy. Every configuration starts each session from a copy of this world, at the same spot.

**Settings:** no frame cap, no VSync, view and simulation distance 12, music off, no pausing or slowing down when the window loses focus.

**Per run:**
- **Average FPS:** frames rendered ÷ seconds played.
- **Slowest 1% FPS:** 1000 ÷ the mean frame time, in milliseconds, of the slowest 1% of that run's frames.
- **99th-percentile frame time.**
- **Start → in the world**, and the **world load**: from quick play to the loading screen closing.
- **CPU time while playing.**
- **Live heap after playing:** what a full GC leaves, from a class histogram.

Frame times are the time between consecutive frames in the client's render loop, measured inside the game. v1 uses no external capture tool such as PresentMon or CapFrameX. Each run's statistics are computed first, and runs, not frames, are the samples compared across configurations.
