"""python -m streamer_toolbox.devtools.box_gen <spec.json> [--src <folder>] [--tests <folder>]

Writes a service's boxes from a spec (docs/PLAN_box_maker.md): answer dataclasses + actions class into --src
(default src/streamer_toolbox/connections/<service>), a fake + a test into --tests (default
tests/connections/<service>). Run from the repo root. Existing files are never overwritten."""
import argparse
import sys
from pathlib import Path

from streamer_toolbox.devtools.box_gen.box_generator import BoxGenerator
from streamer_toolbox.devtools.box_gen.service_spec import ServiceSpec


def main() -> int:
    parser = argparse.ArgumentParser(prog="box_gen", description=__doc__.split("\n\n")[1])
    parser.add_argument("spec", type=Path)
    parser.add_argument("--src", type=Path)
    parser.add_argument("--tests", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="the folder Python imports from (repo root)")
    args = parser.parse_args()
    try:
        spec = ServiceSpec.read(args.spec)
    except (OSError, ValueError, KeyError) as e:
        print(f"spec not usable: {e}", file=sys.stderr)
        return 1
    src = args.src or args.root / "src" / "streamer_toolbox" / "connections" / spec.service
    tests = args.tests or args.root / "tests" / "connections" / spec.service
    for path, written in BoxGenerator(src, tests, args.root).generate(spec).items():
        print(("wrote  " if written else "exists ") + str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
