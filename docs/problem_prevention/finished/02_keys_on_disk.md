# 02 · Tokens and keys readable on disk

His design (Settings → Login): "the settings will have an option to set a login", "only the `secrets` folder
is impacted", "if the login is active, you need to login or it will not start", "should be able to
deactivate login mode, too".

## The problem

The toolbox keeps Twitch / YouTube tokens, API keys and saved logins in files. Anyone or anything that can
read the settings folder (a shared PC, malware, a backup that leaks, a folder sent along by mistake) could
use them to act as his channel.

## What prevents it now

| What | How | Code |
|---|---|---|
| The secrets live in one place | the `secrets` folder in the settings folder; nothing else holds a token | `core/connections/secrets_folder.py` |
| Login (optional, off by default) | every file in `secrets` is encrypted with a key made from his password (scrypt + Fernet) | `core/security/secret_vault.py` |
| The password and key are never written | `secrets/login.json` holds a random salt and a check value only | same |
| Locked until the password | nothing starts and nothing connects; pages go to /unlock, the API and overlays answer 423 | `StartOnce`, `SecretsLockMiddleware`, `UnlockPage` |
| Nothing is written plain by mistake | while locked, writing a secret is refused | `SecretVault.conceal` |
| Secrets are never printed | not in logs, not in answers | a project rule for every change |

## How to check it again

- Tests: `tests/core/security/test_secret_vault.py`, `tests/gui/services/test_secrets_lock_middleware.py`.
- By hand, in a throwaway toolbox: switch the login on, look at a file in `secrets` (it starts with
  `toolbox-secret:1:`), restart (locked: only /unlock), wrong and right password, switch off (files plain
  again).

## Known limits (on purpose)

- A forgotten password can't be recovered (on purpose): the `secrets` folder is deleted and the tokens are
  entered again.
- The password for other devices (Settings → Other devices) travels unencrypted: home network only.
