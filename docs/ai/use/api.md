# Calling the toolbox: the HTTP API

Base address: `http://127.0.0.1:8850` (port: `[api] port` in `config/toolbox.toml`). Two requests, that is
the whole API.

## Who you are

Every request needs a known caller. Either:

- a token, as `Authorization: Bearer <token>` or `X-Toolbox-Token: <token>`, or
- no token, from the same PC, if the settings have a caller with `local = true` (the default without a
  settings file).

A caller only sees and runs the actions on its `allow` list. Getting a token: `docs/ai/use/access.md`.

## List what you may run

```
GET /actions
```

```json
[{"name": "hello.greet", "label": "Say hello", "description": "Counts greetings",
  "params": [{"name": "name", "required": false}]}]
```

Read this list instead of guessing names: it is exactly what your caller may run right now, and it differs
per toolbox (plugins, the streamer's own flows). Boxes that only make sense inside a flow (If, Wait, Run
program, Write text file) are not in it.

## Run one

```
POST /action/<name>
{"name": "chat"}
```

The body is a JSON object of parameters, or empty. It is read as JSON whatever the Content-Type says.

```json
{"action": "hello.greet", "result": "hello chat (#1)"}
```

With curl: `curl -X POST http://127.0.0.1:8850/action/hello.greet -H "Authorization: Bearer <token>" -d '{"name": "chat"}'`

## From a terminal

`toolbox.bat` (Linux: `./toolbox.sh`) in the project folder makes the same two requests:

```
toolbox list obs.*
toolbox info hello.greet
toolbox run hello.greet name=chat
toolbox run hello.greet --json "{\"name\": \"chat\"}"
```

`name=value` is sent as text, `--json` keeps the values' kinds. Another address or a token: `--url` /
`--token` before the command, or the variables `TOOLBOX_URL` / `TOOLBOX_TOKEN`. It prints the result and
ends with exit code 0, or prints the reason and ends with 1.

## When it fails

| Status | Meaning | What to do |
|---|---|---|
| 401 `unknown caller` | no token and not a local caller, or the token is wrong | check the token; a wrong token is never treated as local |
| 403 `browser requests need a token` | the request has an `Origin` header and no token | send a token (pages in a browser can't use the local caller) |
| 404 `unknown action <name>` | the action doesn't exist, **or** your caller isn't allowed to run it (same answer on purpose) | `GET /actions`; if it's missing there, see `docs/ai/use/access.md` |
| 422 `bad parameters for <name>: ...` | a required parameter is missing or a name is wrong | compare with `params` from `GET /actions` |
| 422 `body must be a JSON object` | the body isn't `{...}` | send an object or nothing |
| 500 `{"action": ..., "error": "..."}` | the action ran and failed | read `error`: it usually names the cause ("OBS is switched off under Connections → OBS") |

A 500 is the action's own failure (a program not running, a name that doesn't exist there). Don't retry it
blindly; tell the streamer what `error` says.

## Good to know

- An action runs when you call it. There is no dry run: `obs.switch_scene` switches the scene on stream.
- Values are plain JSON. Parameters have no types in `GET /actions`; the description says what is expected.
- A plugin may add routes of its own under `/api/plugins/<plugin id>/...`.
- `/overlay/...` addresses are the pages OBS shows (alerts, widgets), not an API for you.
