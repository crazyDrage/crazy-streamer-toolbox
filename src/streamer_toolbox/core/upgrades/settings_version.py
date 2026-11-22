"""The number of the settings folder's shape (his next release plan, part 3: "add version to exports and
settings somewhere"). It goes up by one with every SettingsUpgrade; exports carry the number they were made at,
so an old export is upgraded the same way when it is imported."""

# what each version changed: docs/SETTINGS_CHANGES.md (every new step gets its entry there)
SETTINGS_VERSION = 8  # 1: round 78, widgets and alerts get event types (EventsUpgrade)
                      # 2: 2026-11-05, Twitch accounts + chat_deleted hears delete-messages (AccountsUpgrade)
                      # 3: 2026-11-06, YouTube accounts (YouTubeAccountsUpgrade)
                      # 4: 2026-11-06, Rumble accounts (RumbleAccountsUpgrade)
                      # 5: 2026-11-15, Twitch profile picture's user_id, Remembered value (ProfilePictureUpgrade)
                      # 6: 2026-11-16, the chat event's emoji_dict (EmojiDictUpgrade)
                      # 7: 2026-11-16, the chat event's emotes gone, emoji_dict has them (ChatEmotesUpgrade)
                      # 8: 2026-11-22, Build object's pairs become lines, start → Join objects (BuildObjectUpgrade)
VERSION_KEY = "settings_version"  # in toolbox.toml's [toolbox] table, and in every export
