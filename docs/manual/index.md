# streamer-toolbox

One program for the things a stream needs glued together: buttons that do something in OBS, VTube Studio,
SAMMI, Mix It Up or on Twitch, flows that run when a viewer follows, subscribes or redeems, and alerts and
widgets on stream.

This manual has three parts. Pick the one that fits you.

| You are | You want to | Part |
|---|---|---|
| a streamer | set the toolbox up and use it. No code. | [Using the toolbox](user/index.md) |
| someone who writes a bit of Python | add your own boxes, tools or pages without changing the toolbox | [Writing a plugin](plugin/index.md) |
| a developer | change the toolbox itself: a new program to talk to, a new box, a new trigger | [Working on the toolbox](dev/index.md) |

AI agents: read `llms.txt` instead. It leads to the same knowledge in small files.

```{toctree}
:hidden:
:maxdepth: 2

user/index
plugin/index
dev/index
```
