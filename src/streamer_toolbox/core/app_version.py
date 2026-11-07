# the toolbox's own version: the public release's tag without the "v" (his next release plan, part 1). Raised in
# the release commit; the packager stops a release build whose tag says something else (Packager.build)
APP_VERSION = "0.4.0-dev.4"

# test versions between releases (his answer of 2026-11-01): 0.5.0-dev.1 < -alpha.1 < -beta.1 < -rc.1 < 0.5.0.
# Any step may be skipped. A tag with a "-" is a pre-release on GitHub (ci.yml): never "latest"
STAGES = ("dev", "alpha", "beta", "rc")
RELEASE = len(STAGES)  # a real release comes after all of them


def version_numbers(version: str) -> tuple[int, ...]:
    """"v0.3.0" → (0, 3, 0, 4, 0); "0.5.0-beta.2" → (0, 5, 0, 2, 2), so versions sort by it; () when it isn't
    one ("nightly", "0.5.0-gamma.1")."""
    main, _, test = version.strip().removeprefix("v").partition("-")
    parts = main.split(".")
    if not all(p.isdigit() for p in parts):
        return ()
    if not test:
        return (*map(int, parts), RELEASE, 0)
    stage, _, number = test.partition(".")
    if stage not in STAGES or not (number.isdigit() or number == ""):
        return ()
    return (*map(int, parts), STAGES.index(stage), int(number or 0))


def stage(version: str) -> str:
    """"dev" / "alpha" / "beta" / "rc", or "release"; "" when it isn't a version."""
    numbers = version_numbers(version)
    return "" if not numbers else (STAGES + ("release",))[numbers[-2]]


CHANNEL_ORDER = ("release", "rc", "beta", "alpha", "dev")  # Settings → General → Which versions, fewest first


def channel_takes(channel: str, version: str) -> bool:
    """A version of a stage the channel takes: "release" only releases, "beta" also rc and beta, ... (an
    unknown channel counts as "release"). Used for the toolbox's update and for plugins from listings."""
    found = stage(version)
    channel = channel if channel in CHANNEL_ORDER else "release"
    return bool(found) and CHANNEL_ORDER.index(found) <= CHANNEL_ORDER.index(channel)


def is_newer(version: str, than: str = APP_VERSION) -> bool:
    new, old = version_numbers(version), version_numbers(than)
    return bool(new) and bool(old) and new > old
