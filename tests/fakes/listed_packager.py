from streamer_toolbox.devtools.package.packager import Packager

TRACKED = ["src/streamer_toolbox/__main__.py", "plugins/hello/main.py", "config/toolbox.example.toml",
           "requirements.txt", "docs/USER_GUIDE.md", "docs/WIDGETS.md", "docs/HANDOFF.md", "CLAUDE.md",
           "docs/ai/rules.md", "docs/manual/index.md",
           "tests/test_x.py", "start.bat"]


class ListedPackager(Packager):
    """A Packager that is told what git tracks."""

    def tracked(self) -> list[str]:
        return TRACKED
