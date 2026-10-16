# Flows > Triggers > VTube Studio

| What | Name in the code | AI checked | Works | Understandable | Usable | Last change | Note |
|---|---|---|---|---|---|---|---|
| Model loaded | `vts.model_loaded` | 2026-10-09 | yes | yes | yes | 2026-10-12 |  |
| Model moved | `vts.model_moved` | 2026-10-09 | yes | yes | - | 2026-10-12 | it needs a delay setting, or at least a setting to not use every move event. For example, only every 0.5 seconds |
| Tracking found / lost | `vts.tracking` | 2026-10-09 | yes | yes | yes | 2026-10-12 |  |
| VTS background changed | `vts.background` | 2026-10-09 | yes | yes | yes | 2026-10-12 |  |
| VTS hotkey fired | `vts.hotkey` | 2026-10-09 | yes | yes | yes | 2026-10-12 |  |
| VTS model settings changed | `vts.model_config` | 2026-10-09 | yes | yes | - | 2026-10-12 | I have no idea how that should be usable, if I only know something changed. |
