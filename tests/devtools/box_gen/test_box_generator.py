import importlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.devtools.box_gen.box_generator import BoxGenerator
from streamer_toolbox.devtools.box_gen.service_spec import ServiceSpec

SPEC = {"service": "demo_api", "class": "DemoApiActions", "group": "Counters", "boxes": [
    {"name": "get_counter", "label": "Get counter", "help": "A counter's value",
     "request": {"method": "GET", "path": "counters/{counter}"}, "inputs": {"counter": "text"},
     "answer_example": {"Name": "deaths", "Amount": 3, "userID": "130577", "Tags": ["a"], "Meta": {"x": 1},
                        "Note": None}},
    {"name": "add_points", "help": "Gives a viewer points " * 8, "request": {"method": "POST",
                                                                            "path": "users/{user}/points"},
     "inputs": {"user": "text", "amount": {"kind": "number", "default": 5, "hint": "how many"}, "class": "yes/no"},
     "answer_example": {"total": 42}},
    {"name": "list_items", "group": "Items", "request": {"method": "GET", "path": "items"},
     "inputs": {"page": "number"}, "answer_example": [{"id": 1}]}]}


class TestBoxGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="box_gen_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.src = self.root / "src" / "gen_pkg" / "demo_api"
        self.tests = self.root / "gen_tests" / "demo_api"
        self.generator = BoxGenerator(self.src, self.tests, self.root)

    def test_generated_code_passes_its_generated_tests(self) -> None:
        written = self.generator.generate(ServiceSpec.from_json(SPEC))
        self.assertTrue(all(written.values()))
        self.assertEqual(sorted(p.name for p in written), [
            "add_points.py", "add_points_answer.py", "demo_api_actions.py", "demo_api_box.py",
            "fake_demo_api_actions_send.py", "get_counter.py", "get_counter_answer.py", "list_items.py",
            "test_demo_api_actions.py"])
        for path in written:
            self.assertTrue(all(len(line) <= 120 for line in path.read_text(encoding="utf-8").splitlines()), path)
        sys.path[:0] = [str(self.root / "src"), str(self.root)]
        try:
            module = importlib.import_module("gen_tests.demo_api.test_demo_api_actions")
            result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
                unittest.defaultTestLoader.loadTestsFromModule(module))
        finally:
            sys.path.remove(str(self.root / "src"))
            sys.path.remove(str(self.root))
            for name in [n for n in sys.modules if n.startswith(("gen_pkg", "gen_tests"))]:
                del sys.modules[name]
        self.assertEqual((result.testsRun, len(result.failures), len(result.errors)), (3, 0, 0))

    def test_never_overwrites(self) -> None:
        actions = self.src / "demo_api_actions.py"
        self.generator.generate(ServiceSpec.from_json(SPEC))
        actions.write_text("# changed by hand\n", encoding="utf-8")
        written = self.generator.generate(ServiceSpec.from_json(SPEC))
        self.assertFalse(any(written.values()))
        self.assertEqual(actions.read_text(encoding="utf-8"), "# changed by hand\n")

    def test_spec_mistakes_are_named(self) -> None:
        def box(**changes):
            return {"service": "x", "class": "X", "boxes": [dict(SPEC["boxes"][0], **changes)]}
        with self.assertRaisesRegex(ValueError, "path field is"):
            ServiceSpec.from_json(box(request={"path": "users/{user name}"}))
        with self.assertRaisesRegex(ValueError, "path needs inputs counter"):
            ServiceSpec.from_json(box(inputs={}))
        with self.assertRaisesRegex(ValueError, "method is one of"):
            ServiceSpec.from_json(box(request={"method": "FETCH", "path": "x"}))
        with self.assertRaisesRegex(ValueError, "kind is one of"):
            ServiceSpec.from_json(box(inputs={"counter": "words"}))
        with self.assertRaisesRegex(ValueError, "two boxes with one name"):
            ServiceSpec.from_json({"service": "x", "class": "X", "boxes": SPEC["boxes"][:1] * 2})
        with self.assertRaisesRegex(ValueError, "needs 'class'"):
            ServiceSpec.from_json({"service": "x", "boxes": []})


if __name__ == "__main__":
    unittest.main()
