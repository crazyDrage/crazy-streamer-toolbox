# 07 · A widget's code sends data away or takes over the page

His words (round 25, 2026-10-03): "widgets support Javascript and HTML. That would make it possible to get
data from my computer and send it somewhere (hacker, scammer, ...). Can we add a protection layer? Can you
research that this is a problem streamelement widgets have or do they have protection."

## The problem

An imported widget is someone else's code running on the streaming PC, inside OBS. It could read what the
page can reach, send it to another server, load more code from anywhere, or send the Browser source to
another site.

## What we found

StreamElements protects its Elements with a list of allowed hosts per widget (a "securityPolicy" in the
manifest, a Content Security Policy at runtime). The toolbox had nothing like it.

## What prevents it now

| What | How | Code |
|---|---|---|
| The page has no identity of its own | the widget runs in a sandboxed frame inside a small page of the toolbox; it can't read the toolbox's pages or cookies | `api/widget_router.py` (shell + page), `WidgetSandboxMiddleware` |
| It can only talk to allowed hosts | a Content Security Policy per widget; the Safety tab lists the hosts, he allows more by hand; what the browser stopped is reported there | `core/widgets/widget_safety.py` |
| It can't leave | the frame can only show the widget's page: `location.href`, `top.location`, meta refresh and the rest were tried and stay inside | shell page |
| Helper scripts come from this PC | scripts and styles the widget pulls from other servers are kept in its folder | `core/widgets/widget_helpers.py` |
| StreamElements' servers are answered locally | their addresses point at the toolbox's stand-in; "Clean out StreamElements" writes that into the widget | `core/widgets/streamelements_cleaner.py` |

Details and the steps: `docs/PLAN_widget_protection.md`.

## How to check it again

- Tests: `tests/core/widgets/test_widget_safety.py`, `tests/api/test_widget_router.py`.
- A test widget whose code tries to leave (`location.href`, `top.location`, a meta refresh) or fetch from an
  unknown host, in headless Chrome: it must stay, and the host must show under Safety → blocked.
