# 06 · A flow runs forever and can't be stopped

His words (2026-10-26, `loop test`): "I need a stop flow button, I have an endless loop."

## The problem

A loop without an end, or a timer that keeps starting a flow, keeps going: sounds, hotkeys or OBS changes
repeat on stream, and the only way out was restarting the toolbox.

## What prevents it now

| What | How | Code |
|---|---|---|
| Stop one flow | a red **Stop** next to Run on the Flows page (also in its right click menu) while it runs | Flows page, `core/flows/flow_runner.py` |
| Stop everything | a red **Stop all (n)** at the top of the Flows page while any flow runs | same |
| Stop from the editor | a red **Stop** next to Test run while that flow runs (test runs too) | flow editor |
| What a stop does | the runs end where they are; a stopped redeem keeps its points; a flow started by a box runs on and is stopped by its own name | `FlowRunner` |
| A loop that is started again | the Loop box chooses: **Only one** (a start that reaches it while it loops stops there) or **Another one alongside** | Loop box |

## How to check it again

- Flow runner tests: `tests/core/flows/`.
- His `loop test (Hex)` flow: run it, then Stop; the loop must end at once.
