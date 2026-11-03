+++
title = "A sound on a redeem"
section = "Examples"
order = 20
+++
**What it does:** a viewer redeems a channel point reward, and a sound plays.

```
Redeem         reward "Play a sound"
  ↓
Play sound     your sound file
```

**The boxes:**

1. **Redeem** (Twitch): pick your reward in its box. The example waits for a reward called
   "Play a sound"; change it to one you have.
2. **Play sound**: pick a sound file. It plays on this PC.

**Make it a soundboard:** one flow per sound, or one flow with an input for the file (the **Input** box) and a
button per sound on the Live page.

**Want it in OBS too?** Add **Show / hide source** or an alert box after Play sound.
