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
Send chat message    ← Build text  "Lizards so far: {count}"  (count ← Math on variable)
```

**The boxes:**

1. **Chat message** (Twitch), set to the command `!lizard`. It starts the flow.
2. **Math on variable**: the variable `lizards`, sign `+`, number `1`. A variable that doesn't exist yet starts
   at 0, and it is kept over a restart.
3. **Build text**: the words `Lizards so far: {count}`, and its value `count` wired from Math on variable (the
   new number). `{count}` in the words is where the number goes.
4. **Send chat message**: its text is a value wire from Build text.

**Try changing:** the command, the words, or `+ 1` into `+ 10`. The **Variables** page shows the count, and
you can set it back to 0 there.
