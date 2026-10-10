# Tokens, permissions, and calling from another PC

Who may call the API is decided in `config/toolbox.toml`, by the streamer. You can prepare the lines; adding
them, and anything that opens the toolbox to the network, needs their yes. A change needs a restart.

## A caller

```toml
[callers.my_agent]
token = "a-long-random-string"     # at least 16 characters
allow = ["flow.*", "trigger.fire"]
```

- `token`: sent as `Authorization: Bearer <token>` or `X-Toolbox-Token`. Make one with
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`, or in the dashboard: Connections → Toolbox →
  New token.
- `local = true` instead of a token: calls from this PC without a token are this caller.
- `allow`: action names or patterns. `"obs.*"` = every OBS action, `"*"` = everything. Ask for what you need,
  not `"*"`.
- Once the file has any `[callers...]` table, only the callers written there exist. Without any, there is one
  local caller that may run everything.

## Why an action is missing from GET /actions

1. It isn't on your `allow` list.
2. It comes from a plugin that isn't enabled (`[plugins] enabled`), or it is a flow that doesn't exist (yet).
3. It is a flow-only box (If, Wait, Run program, Write text file). These can't be run over the API, on purpose:
   no caller can write files or start programs on the streamer's PC. Put them in a flow and run the flow.

## From another PC or device

By default the toolbox listens on `127.0.0.1` only: nothing outside this PC reaches it.

- `[api] host = "0.0.0.0"` lets other devices in the network connect. Do this only when every caller has a
  token (no `local = true` caller with a wide `allow`).
- API calls from another device always need a token.
- The dashboard pages then ask other devices for a password (`[access]`, set in Settings → Other devices).
  That password is for people; the API uses tokens.

Never write a token into a file that is shared or tracked by git, and never print one.
