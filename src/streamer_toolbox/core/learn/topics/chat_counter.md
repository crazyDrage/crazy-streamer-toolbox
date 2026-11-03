+++
title = "A counter in chat"
section = "Examples"
order = 10
+++
**What it does:** someone writes `!lizard` in chat. The toolbox counts it and writes the new number in chat.

```
Chat message !lizard
  ↓
Math on variable     lizards + 1
  ↓
Send chat message    "Lizards so far: 7"
```

**The boxes:**

1. **Chat message** (Twitch), set to the command `!lizard`. It starts the flow.
2. **Math on variable**: the variable `lizards`, sign `+`, number `1`. A variable that doesn't exist yet starts
   at 0, and it is kept over a restart.
3. **Send chat message**: its text reads the new number from the box before (a value wire into the text).

**Try changing:** the command, the words, or `+ 1` into `+ 10`. The **Variables** page shows the count, and
you can set it back to 0 there.
