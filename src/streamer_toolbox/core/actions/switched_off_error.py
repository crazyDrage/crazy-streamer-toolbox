class SwitchedOffError(RuntimeError):
    """Raised when an action can't run because what it belongs to is switched off (a plugin, on the Plugins
    page). The text says what and where to switch it on."""
