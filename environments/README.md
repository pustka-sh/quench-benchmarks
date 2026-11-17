# Environments

Every session records its machine automatically in `results.json`, under `session.machine`:
- CPU, threads and RAM
- OS build
- GPUs, with driver versions and display modes
- the active power plan

Under `session.profiles` it records each configuration's exact launch command, its Java runtime, and a SHA-256 of every jar it loads.

Add one file here per machine for what software can't see: cooling, BIOS settings, background software, and anything unusual. Start from [`TEMPLATE.md`](TEMPLATE.md).
