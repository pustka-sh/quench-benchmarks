# Server ticks

v1 measures ticks on the **integrated server** during the [client in-game runs](../client-fps): how long each server tick takes, over the same 30 seconds. Each run reports its mean and 95th-percentile milliseconds per tick (MSPT).

Both loaders hold 20 TPS easily on this world, so TPS alone would show no difference. MSPT shows how much headroom each tick leaves.

**Not in v1:** ticks on the dedicated server, and chunk-loading throughput. The dedicated server's startup is in [startup](../startup).

**Known issue:** in earlier testing, Quench's integrated-server ticks were 0.1–0.4 ms slower than vanilla's under ZGC, which the client runs with. Under G1 they were equal. All of the difference was in the random-tick loop, whose compiled code is identical in both, and the cause is still open. v1 reports ticks as measured.

To log every tick of a run, add `-Pbench.jvmArgs=-Dquench.probe.ticks=true` to a harness run. That writes `<run>.json.ticks.csv`, with each tick's start time, length and the server thread's CPU cycles.
