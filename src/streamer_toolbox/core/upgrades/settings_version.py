"""The number of the settings folder's shape (his next release plan, part 3: "add version to exports and
settings somewhere"). It goes up by one with every SettingsUpgrade; exports carry the number they were made at,
so an old export is upgraded the same way when it is imported."""

SETTINGS_VERSION = 1  # 1: round 78, widgets and alerts get event types (EventsUpgrade)
VERSION_KEY = "settings_version"  # in toolbox.toml's [toolbox] table, and in every export
