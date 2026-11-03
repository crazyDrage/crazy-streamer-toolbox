+++
title = "Build a chat message"
section = "Examples"
order = 30
+++
**What it does:** someone cheers Bits, and chat gets "Dragon just gave 100 Bits!" with their name and the
amount in it.

```
Cheer (bits)
  ↓
Send chat message
  text ←┄┄ Build text
           "{user} gave {bits} Bits!"
           user, bits ←┄┄ Cheer
```

(↓ = run wire, ┄┄ = value wire)

**The boxes:**

1. **Cheer (bits)** starts the flow. Its orange dots are what happened: `user`, `bits`, `message`.
2. **Build text** has a text with `{user}` and `{bits}` in it, and a line for each name (+ Add value). The
   Cheer box's dots are wired into those lines.
3. **Send chat message** reads its text from Build text (a value wire).

Build text has **no run wire**: it only works out a text, at the moment Send chat message reads it. See
"Run wires and value wires".

**Try changing:** the words, or add `{message}` with a line wired from the Cheer box's `message` dot.
