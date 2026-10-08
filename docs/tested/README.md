# What was tested

The record of what was tried by hand in streamer-toolbox, sorted like the toolbox's side menu, so it can be
gone through one tab after another: one folder per main tab, and in it what is reached from that tab.

- `<tab>/page.md`: the tab's own page and the pages below it in the menu
- `flows/triggers/<program>.md`: the triggers, as the Add trigger window groups them
- `flows/boxes/<category>/<group>.md`: the boxes, as the Add box window sorts them
- `tools/<tool>.md` and `connections/<program>.md`

Every row has three checks. **Works**: it does what it says, on the real program. **Understandable**: its
name, help line and fields tell you what it does. **Usable**: you can set it up and use it without a detour.
A row counts as tested with all three. "Last change" is the day a check of that row was last set or taken back.

**AI checked** comes before those: the day Hex (the AI that builds the toolbox) last tried that thing in the
running toolbox, or `-` when it never did. It is not one of the three checks and opens nothing in a build.
For a page that means: it was opened, it drew and showed no error; not that every button on it was pressed.

A build of the toolbox only offers what is tested here: an untested page is not in its menu, an untested
trigger, box, tool or connection is not there. In the project folder everything is on.

Tick the checks in the **test window**, a small window of its own next to the toolbox (it stays open while
the toolbox is restarted, and writes the row's file at once):

    test-window.bat          (Linux: ./test-window.sh)

You can also write `yes` or `-` into a file by hand, and anything into "Note" (not the sign `|`); press
Reload in the test window after that. The toolbox reads the files when it starts.

The files and folders are made by a script of their own, which also adds what is new, moves what was sorted
anew and renews the table below (ticks, days and notes stay):

    $env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m streamer_toolbox.devtools.tested

## How far it is

| Where | Tested | Of |
|---|---|---|
| **[live](live/)** | **0** | **1** |
| [live/page](live/page.md) | 0 | 1 |
| **[flows](flows/)** | **0** | **310** |
| [flows/page](flows/page.md) | 0 | 2 |
| [flows/triggers/any_platform](flows/triggers/any_platform.md) | 0 | 10 |
| [flows/triggers/crowdcontrol](flows/triggers/crowdcontrol.md) | 0 | 1 |
| [flows/triggers/example](flows/triggers/example.md) | 0 | 1 |
| [flows/triggers/heart_rate](flows/triggers/heart_rate.md) | 0 | 1 |
| [flows/triggers/keyboard](flows/triggers/keyboard.md) | 0 | 1 |
| [flows/triggers/lumia](flows/triggers/lumia.md) | 0 | 1 |
| [flows/triggers/rumble](flows/triggers/rumble.md) | 0 | 7 |
| [flows/triggers/streamelements](flows/triggers/streamelements.md) | 0 | 1 |
| [flows/triggers/streamerbot](flows/triggers/streamerbot.md) | 0 | 1 |
| [flows/triggers/streamlabs](flows/triggers/streamlabs.md) | 0 | 1 |
| [flows/triggers/streamsocket](flows/triggers/streamsocket.md) | 0 | 1 |
| [flows/triggers/tiltify](flows/triggers/tiltify.md) | 0 | 1 |
| [flows/triggers/tits](flows/triggers/tits.md) | 0 | 3 |
| [flows/triggers/toolbox](flows/triggers/toolbox.md) | 0 | 3 |
| [flows/triggers/twitch](flows/triggers/twitch.md) | 0 | 12 |
| [flows/triggers/veadotube](flows/triggers/veadotube.md) | 0 | 1 |
| [flows/triggers/vtube_studio](flows/triggers/vtube_studio.md) | 0 | 6 |
| [flows/triggers/youtube](flows/triggers/youtube.md) | 0 | 8 |
| [flows/boxes/alert/alerts](flows/boxes/alert/alerts.md) | 0 | 2 |
| [flows/boxes/data/split](flows/boxes/data/split.md) | 0 | 1 |
| [flows/boxes/discord/general](flows/boxes/discord/general.md) | 0 | 1 |
| [flows/boxes/example/effects](flows/boxes/example/effects.md) | 0 | 1 |
| [flows/boxes/example/general](flows/boxes/example/general.md) | 0 | 5 |
| [flows/boxes/file/text_files](flows/boxes/file/text_files.md) | 0 | 2 |
| [flows/boxes/firebot/counters](flows/boxes/firebot/counters.md) | 0 | 2 |
| [flows/boxes/firebot/general](flows/boxes/firebot/general.md) | 0 | 1 |
| [flows/boxes/firebot/variables](flows/boxes/firebot/variables.md) | 0 | 2 |
| [flows/boxes/heartrate/general](flows/boxes/heartrate/general.md) | 0 | 1 |
| [flows/boxes/hello/general](flows/boxes/hello/general.md) | 0 | 2 |
| [flows/boxes/history/history](flows/boxes/history/history.md) | 0 | 2 |
| [flows/boxes/json/json](flows/boxes/json/json.md) | 0 | 2 |
| [flows/boxes/list/change](flows/boxes/list/change.md) | 0 | 2 |
| [flows/boxes/list/new_list](flows/boxes/list/new_list.md) | 0 | 4 |
| [flows/boxes/list/read](flows/boxes/list/read.md) | 0 | 5 |
| [flows/boxes/logic/flow](flows/boxes/logic/flow.md) | 0 | 3 |
| [flows/boxes/logic/if](flows/boxes/logic/if.md) | 0 | 2 |
| [flows/boxes/logic/math](flows/boxes/logic/math.md) | 0 | 3 |
| [flows/boxes/logic/random](flows/boxes/logic/random.md) | 0 | 1 |
| [flows/boxes/logic/repeat](flows/boxes/logic/repeat.md) | 0 | 3 |
| [flows/boxes/logic/wait](flows/boxes/logic/wait.md) | 0 | 2 |
| [flows/boxes/lumia/general](flows/boxes/lumia/general.md) | 0 | 4 |
| [flows/boxes/mixitup/chat](flows/boxes/mixitup/chat.md) | 0 | 2 |
| [flows/boxes/mixitup/commands](flows/boxes/mixitup/commands.md) | 0 | 2 |
| [flows/boxes/mixitup/counters](flows/boxes/mixitup/counters.md) | 0 | 4 |
| [flows/boxes/mixitup/currency](flows/boxes/mixitup/currency.md) | 0 | 3 |
| [flows/boxes/mixitup/inventory](flows/boxes/mixitup/inventory.md) | 0 | 3 |
| [flows/boxes/mixitup/viewers](flows/boxes/mixitup/viewers.md) | 0 | 1 |
| [flows/boxes/object/change](flows/boxes/object/change.md) | 0 | 3 |
| [flows/boxes/object/read](flows/boxes/object/read.md) | 0 | 4 |
| [flows/boxes/obs/advanced](flows/boxes/obs/advanced.md) | 0 | 5 |
| [flows/boxes/obs/audio](flows/boxes/obs/audio.md) | 0 | 8 |
| [flows/boxes/obs/filters](flows/boxes/obs/filters.md) | 0 | 2 |
| [flows/boxes/obs/media](flows/boxes/obs/media.md) | 0 | 7 |
| [flows/boxes/obs/recording_streaming](flows/boxes/obs/recording_streaming.md) | 0 | 8 |
| [flows/boxes/obs/scenes](flows/boxes/obs/scenes.md) | 0 | 5 |
| [flows/boxes/obs/sources](flows/boxes/obs/sources.md) | 0 | 12 |
| [flows/boxes/obs/studio_mode](flows/boxes/obs/studio_mode.md) | 0 | 3 |
| [flows/boxes/obs/windows](flows/boxes/obs/windows.md) | 0 | 4 |
| [flows/boxes/points/points](flows/boxes/points/points.md) | 0 | 6 |
| [flows/boxes/popup/popups](flows/boxes/popup/popups.md) | 0 | 2 |
| [flows/boxes/sammi/buttons](flows/boxes/sammi/buttons.md) | 0 | 3 |
| [flows/boxes/sammi/decks](flows/boxes/sammi/decks.md) | 0 | 3 |
| [flows/boxes/sammi/messages](flows/boxes/sammi/messages.md) | 0 | 3 |
| [flows/boxes/sammi/variables](flows/boxes/sammi/variables.md) | 0 | 2 |
| [flows/boxes/sound/play](flows/boxes/sound/play.md) | 0 | 2 |
| [flows/boxes/streamerbot/general](flows/boxes/streamerbot/general.md) | 0 | 4 |
| [flows/boxes/system/programs](flows/boxes/system/programs.md) | 0 | 1 |
| [flows/boxes/text/text](flows/boxes/text/text.md) | 0 | 6 |
| [flows/boxes/time/time](flows/boxes/time/time.md) | 0 | 2 |
| [flows/boxes/tip/tips](flows/boxes/tip/tips.md) | 0 | 1 |
| [flows/boxes/tits/general](flows/boxes/tits/general.md) | 0 | 2 |
| [flows/boxes/trigger/custom_triggers](flows/boxes/trigger/custom_triggers.md) | 0 | 1 |
| [flows/boxes/twitch/channel_points](flows/boxes/twitch/channel_points.md) | 0 | 5 |
| [flows/boxes/twitch/chat](flows/boxes/twitch/chat.md) | 0 | 5 |
| [flows/boxes/twitch/polls_and_predictions](flows/boxes/twitch/polls_and_predictions.md) | 0 | 4 |
| [flows/boxes/twitch/stream](flows/boxes/twitch/stream.md) | 0 | 10 |
| [flows/boxes/twitch/viewers](flows/boxes/twitch/viewers.md) | 0 | 4 |
| [flows/boxes/var/variables](flows/boxes/var/variables.md) | 0 | 3 |
| [flows/boxes/veadotube/general](flows/boxes/veadotube/general.md) | 0 | 3 |
| [flows/boxes/veadotube/stack](flows/boxes/veadotube/stack.md) | 0 | 3 |
| [flows/boxes/video/video](flows/boxes/video/video.md) | 0 | 1 |
| [flows/boxes/viewer/per_viewer](flows/boxes/viewer/per_viewer.md) | 0 | 4 |
| [flows/boxes/vnyan/general](flows/boxes/vnyan/general.md) | 0 | 2 |
| [flows/boxes/voicemod/general](flows/boxes/voicemod/general.md) | 0 | 3 |
| [flows/boxes/voicemod/soundboard](flows/boxes/voicemod/soundboard.md) | 0 | 2 |
| [flows/boxes/vtube_studio/expressions](flows/boxes/vtube_studio/expressions.md) | 0 | 2 |
| [flows/boxes/vtube_studio/hotkeys](flows/boxes/vtube_studio/hotkeys.md) | 0 | 1 |
| [flows/boxes/vtube_studio/items](flows/boxes/vtube_studio/items.md) | 0 | 4 |
| [flows/boxes/vtube_studio/look](flows/boxes/vtube_studio/look.md) | 0 | 3 |
| [flows/boxes/vtube_studio/model](flows/boxes/vtube_studio/model.md) | 0 | 4 |
| [flows/boxes/vtube_studio/model_position](flows/boxes/vtube_studio/model_position.md) | 0 | 8 |
| [flows/boxes/vtube_studio/parameters](flows/boxes/vtube_studio/parameters.md) | 0 | 2 |
| [flows/boxes/vtube_studio/visual_effects](flows/boxes/vtube_studio/visual_effects.md) | 0 | 4 |
| [flows/boxes/warudo/general](flows/boxes/warudo/general.md) | 0 | 1 |
| [flows/boxes/web/request](flows/boxes/web/request.md) | 0 | 1 |
| [flows/boxes/widget/widgets](flows/boxes/widget/widgets.md) | 0 | 1 |
| [flows/boxes/youtube/chat](flows/boxes/youtube/chat.md) | 0 | 1 |
| **[triggers](triggers/)** | **0** | **1** |
| [triggers/page](triggers/page.md) | 0 | 1 |
| **[variables](variables/)** | **0** | **1** |
| [variables/page](variables/page.md) | 0 | 1 |
| **[overlay](overlay/)** | **0** | **3** |
| [overlay/page](overlay/page.md) | 0 | 3 |
| **[tools](tools/)** | **0** | **6** |
| [tools/page](tools/page.md) | 0 | 1 |
| [tools/twitch](tools/twitch.md) | 0 | 1 |
| [tools/points](tools/points.md) | 0 | 1 |
| [tools/example_lamp](tools/example_lamp.md) | 0 | 1 |
| [tools/hello](tools/hello.md) | 0 | 1 |
| [tools/sammi_decks](tools/sammi_decks.md) | 0 | 1 |
| **[connections](connections/)** | **0** | **27** |
| [connections/page](connections/page.md) | 0 | 2 |
| [connections/obs](connections/obs.md) | 0 | 1 |
| [connections/sammi](connections/sammi.md) | 0 | 1 |
| [connections/mixitup](connections/mixitup.md) | 0 | 1 |
| [connections/vtube_studio](connections/vtube_studio.md) | 0 | 1 |
| [connections/twitch](connections/twitch.md) | 0 | 1 |
| [connections/keyboard](connections/keyboard.md) | 0 | 1 |
| [connections/streamelements](connections/streamelements.md) | 0 | 1 |
| [connections/streamlabs](connections/streamlabs.md) | 0 | 1 |
| [connections/rumble](connections/rumble.md) | 0 | 1 |
| [connections/youtube](connections/youtube.md) | 0 | 1 |
| [connections/streamsocket](connections/streamsocket.md) | 0 | 1 |
| [connections/vnyan](connections/vnyan.md) | 0 | 1 |
| [connections/warudo](connections/warudo.md) | 0 | 1 |
| [connections/veadotube](connections/veadotube.md) | 0 | 1 |
| [connections/tits](connections/tits.md) | 0 | 1 |
| [connections/streamerbot](connections/streamerbot.md) | 0 | 1 |
| [connections/firebot](connections/firebot.md) | 0 | 1 |
| [connections/lumia](connections/lumia.md) | 0 | 1 |
| [connections/voicemod](connections/voicemod.md) | 0 | 1 |
| [connections/pulsoid](connections/pulsoid.md) | 0 | 1 |
| [connections/hyperate](connections/hyperate.md) | 0 | 1 |
| [connections/discord](connections/discord.md) | 0 | 1 |
| [connections/tiltify](connections/tiltify.md) | 0 | 1 |
| [connections/crowdcontrol](connections/crowdcontrol.md) | 0 | 1 |
| [connections/example](connections/example.md) | 0 | 1 |
| **[plugins](plugins/)** | **0** | **3** |
| [plugins/page](plugins/page.md) | 0 | 3 |
| **[settings](settings/)** | **0** | **4** |
| [settings/page](settings/page.md) | 0 | 4 |
| **All** | **0** | **356** |
