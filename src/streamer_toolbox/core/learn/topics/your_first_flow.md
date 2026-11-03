+++
title = "Your first flow"
section = "First steps"
order = 10
+++
A **flow** is what the toolbox does when something happens: boxes joined by wires.

1. **Flows → New flow.** It starts with a **Start** box wired to an **End** box.
2. **Add box** lists everything your connected programs can do: switch a scene, play a sound, write in chat,
   wait, if / else, variables, ...
3. Drag from a box's round dot on the right to the next box's round dot on the left. That is a **run wire**:
   "when this box is done, do that one next".
4. **Test run** tries it right away.

**When does it start?**

- **Start** is the flow's own button: on the Live page, in SAMMI, from another flow, over the API.
- **Add trigger** gives it one more way to start: a channel point reward, a follow, a chat command, a key, a
  timer, ... Each trigger is a Start box of its own. Its orange dots are what happened: who followed, what they
  typed.

**Tip:** a new flow you're still trying out can stay switched off (the switch at the top of the editor). Its
Test run still works.
