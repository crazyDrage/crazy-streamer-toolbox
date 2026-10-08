from pathlib import Path

from streamer_toolbox.devtools.box_gen.actions_class_writer import ActionsClassWriter
from streamer_toolbox.devtools.box_gen.answer_class_writer import AnswerClassWriter
from streamer_toolbox.devtools.box_gen.answer_shape import AnswerShape
from streamer_toolbox.devtools.box_gen.fake_writer import FakeWriter
from streamer_toolbox.devtools.box_gen.names import snake
from streamer_toolbox.devtools.box_gen.service_spec import ServiceSpec
from streamer_toolbox.devtools.box_gen.test_writer import TestWriter


class BoxGenerator:
    """Writes a service's files from its spec: one dataclass file per answer shape and the actions class into
    `src_dir`, a fake send and a test file into `tests_dir` (one class per file, like the rest of the repo).
    Never overwrites: a file that exists is left as it is and reported."""

    def __init__(self, src_dir: Path, tests_dir: Path, root: Path) -> None:
        """root: the folder Python imports from for both (the repo with PYTHONPATH "src;."), to make the
        module names; src_dir under root/src is imported without the "src." part."""
        self._src = src_dir
        self._tests = tests_dir
        self._root = root

    def generate(self, spec: ServiceSpec) -> dict[Path, bool]:
        """Every file it would write → True if written now, False if it was there already."""
        files: dict[Path, str] = {}
        imports: dict[str, str] = {}
        for box in spec.boxes:
            if box.has_answer_class:
                shape = AnswerShape.of(box.answer_class, box.answer_example)
                path = self._src / f"{snake(box.answer_class)}.py"
                files[path] = AnswerClassWriter().write(shape, spec.service, box.name)
                imports[box.answer_class] = self._module(path)
        actions_path = self._src / f"{snake(spec.class_name)}.py"
        files[actions_path] = ActionsClassWriter().write(spec, imports)
        fake_class = f"Fake{spec.class_name}Send"
        fake_path = self._tests / f"{snake(fake_class)}.py"
        files[fake_path] = FakeWriter().write(fake_class, spec.class_name)
        test_path = self._tests / f"test_{snake(spec.class_name)}.py"
        files[test_path] = TestWriter().write(spec, self._module(actions_path), self._module(fake_path), fake_class)
        written = {}
        for path, text in files.items():
            written[path] = not path.exists()
            if written[path]:
                self._package(path.parent)
                path.write_text(text, encoding="utf-8")
        return written

    def _module(self, path: Path) -> str:
        relative = path.resolve().relative_to(self._root.resolve()).with_suffix("")
        parts = relative.parts[1:] if relative.parts[:1] == ("src",) else relative.parts
        return ".".join(parts)

    def _package(self, folder: Path) -> None:
        """The folder and the ones above it (up to root) as packages, so the new modules can be imported."""
        folder.mkdir(parents=True, exist_ok=True)
        root = self._root.resolve()
        current = folder.resolve()
        while current != root and root in current.parents and current.name != "src":
            init = current / "__init__.py"
            if not init.exists():
                init.write_text("", encoding="utf-8")
            current = current.parent
