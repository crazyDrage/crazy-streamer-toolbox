# Live

| What | Name in the code | AI checked | Works | Understandable | Usable | Last change | Note |
|---|---|---|---|---|---|---|---|
| Live | `/` | 2026-10-08 | - | - | - | - |  |
| Edit view: the pages in the bar, editing stays on when a page is picked in the side list | `LiveDeckView._view`, `EDIT_KEY` | 2026-11-17 | - | - | - | 2026-11-17 | His 11-17 points 1 + 2 |
| Copy a button, paste it on any page (right-click a free spot) | `LiveDeckView._copy`, `_paste` | 2026-11-17 | - | - | - | 2026-11-17 | His 11-17 point 3; the old same-page copy is now Duplicate |
| Right-click a free spot: Add button here; right-click outside edit view: Edit the buttons + the same menus | `LiveDeckView._board_menu`, `_edit_switch_item` | 2026-11-18 | - | - | - | 2026-11-18 | His 11-17 point 4 + 11-18 "at least an edit option"; on a phone a long press |
| Button menu: Cut, Move to page, Swap places | `LiveDeckView._cut`, `_move_to_page`, `_start_swap` | 2026-11-18 | - | - | - | 2026-11-18 | His 11-18 pick 3 |
| Keys while editing: Ctrl+C / X / V / Z, Delete, Escape (under the mouse); Page Up / Down | `live_deck.js`, `LiveDeckView._key` | 2026-11-18 | - | - | - | 2026-11-18 | His 11-18 pick 2 |
| Undo (button + Ctrl+Z), last 50 saves since the start | `DeckStore.undo` | 2026-11-18 | - | - | - | 2026-11-18 | His 11-18 pick 5 |
| Ask before it runs | `DeckButton.confirm` | 2026-11-18 | - | - | - | 2026-11-18 | His 11-18 pick 11 |
| Start with this page on this device (view menu) | `START_KEY` | 2026-11-18 | - | - | - | 2026-11-18 | His 11-18 pick 14 |
| State: a flow output sets the button's on look (any run of the flow) | `DeckStates`, `FlowRunner.outputs_heard` | 2026-11-18 | - | - | - | 2026-11-18 | His 11-18 picks 7 + 8 and his "flow output variable"; kept through a restart (live_states.json) |
| A deck wider than a phone starts at the left edge (was cut off) | `LiveDeckView._view` | 2026-11-18 | - | - | - | 2026-11-18 | Found while checking |
