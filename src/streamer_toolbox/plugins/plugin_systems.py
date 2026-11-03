"""The systems a listing can say a plugin version runs on (`os = ["windows"]`): the toolbox runs on Windows,
Linux and Android (Termux), maybe macOS. No `os` line: it runs everywhere."""
import sys

SYSTEMS = {"windows": "Windows", "linux": "Linux", "macos": "macOS", "android": "Android"}


def this_system() -> str:
    """The system the toolbox runs on, as a listing writes it."""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "android" or hasattr(sys, "getandroidapilevel"):
        return "android"
    return "linux"


def runs_here(systems: tuple[str, ...], system: str | None = None) -> bool:
    return not systems or (system or this_system()) in systems


def system_names(systems: tuple[str, ...]) -> str:
    """"Windows and Linux": for "Only for ..."."""
    names = [SYSTEMS.get(s, s) for s in systems]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
