+++
title = "Run wires and value wires"
section = "First steps"
order = 20
+++
A flow has two kinds of wires.

| | Run wire | Value wire |
|---|---|---|
| Looks like | round dots, solid line | square dots, orange dotted line |
| Says | "when this box is done, do that box next" | "this field takes that box's value" |
| Decides | **when** a box runs | **what** a field gets |

**A box with a run wire into it** runs once, when the wire reaches it. Every field that reads it gets that
same value.

**A box with no run wire into it** runs at the moment a field reads it, once for each field.

**Boxes without run dots** (Value, Calculate, Build text, Replace in text, ...) only work out a value, so it
doesn't matter when they run.

**Keep the run wire** on a box that asks a program (OBS, VTube Studio, ...) when its answer must be from one
moment, and on a box that does something (plays a sound, moves the model).

**The last value you see on a box** is only a preview. To keep a value, use "Save it in a variable" on the box,
or **Freeze** the box (its panel): it keeps one answer and doesn't run any more.
