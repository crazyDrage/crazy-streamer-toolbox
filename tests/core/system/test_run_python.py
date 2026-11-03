import sys
import tempfile
import unittest
from pathlib import Path

from streamer_toolbox.core.system.boxes.run_python import RunPython

GREET = '''
import helper


def run(name=None, amount=None):
    print("working on", name)
    return {"text": helper.shout(f"{name} gave {amount}"), "count": amount * 2}


if __name__ == "__main__":
    raise SystemExit("must not run as the main file")
'''


class TestRunPython(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.box = RunPython(self.root / "boxes" / "python")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, name: str, text: str) -> Path:
        path = self.root / "boxes" / "python" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    async def test_a_new_name_gets_the_template_and_runs(self) -> None:
        result = await self.box.run("lizard", outputs="text, count", name="Kit", amount=3)
        self.assertEqual({"text": None, "count": None, "printed": ""}, result)
        made = (self.root / "boxes" / "python" / "lizard.py").read_text(encoding="utf-8")
        self.assertIn("def run(name=None, amount=None):", made)

    async def test_inputs_by_name_outputs_printed_and_its_own_imports(self) -> None:
        self.write("helper.py", "def shout(text):\n    return text.upper() + '!'\n")
        self.write("greet.py", GREET)
        result = await self.box.run("greet", outputs="text, count", name="Kit", amount=21)
        self.assertEqual({"text": "KIT GAVE 21!", "count": 42, "printed": "working on Kit"}, result)

    async def test_a_file_anywhere_and_another_function(self) -> None:
        path = self.root / "elsewhere" / "tool.py"
        path.parent.mkdir()
        path.write_text("async def other(word=''):\n    return word[::-1]\n", encoding="utf-8")
        self.assertEqual({"value": "olleh", "printed": ""},
                         await self.box.run(str(path), function="other", word="hello"))

    async def test_a_python_of_its_own(self) -> None:
        self.write("which.py", "import sys\n\ndef run():\n    return {'python': sys.executable}\n")
        result = await self.box.run("which", python=sys.executable)
        self.assertEqual(Path(sys.executable).resolve(), Path(result["python"]).resolve())
        with self.assertRaisesRegex(FileNotFoundError, "no Python"):
            await self.box.run("which", python=str(self.root / "nope.exe"))

    async def test_an_error_in_the_file_says_what_went_wrong(self) -> None:
        self.write("broken.py", "def run():\n    return 1 / 0\n")
        with self.assertRaisesRegex(RuntimeError, "ZeroDivisionError"):
            await self.box.run("broken")
        self.write("other.py", "def something():\n    pass\n")
        with self.assertRaisesRegex(RuntimeError, r"has no function run\(\)"):
            await self.box.run("other")

    async def test_too_slow_is_stopped(self) -> None:
        self.write("slow.py", "import time\n\ndef run():\n    time.sleep(10)\n")
        with self.assertRaisesRegex(TimeoutError, "within 0.5 s"):
            await self.box.run("slow", seconds=0.5)

    def test_the_template_for_a_boxs_values(self) -> None:
        """What the code window shows for a file that isn't there yet: the box's own fields are no inputs."""
        text = RunPython.template({"file": "lizard", "function": "work", "outputs": "text", "seconds": 5,
                                   "name": "${box.n2.user}", "amount": 3})
        self.assertIn("def work(name=None, amount=None):", text)
        self.assertIn('return {"text": text}', text)
        self.assertIn("def run():", RunPython.template({}))

    async def test_a_name_stays_inside_its_folder(self) -> None:
        with self.assertRaisesRegex(ValueError, "stays inside"):
            await self.box.run("../../outside")
        with self.assertRaisesRegex(ValueError, "can't be a Python function"):
            await self.box.run("x", function="no way")


if __name__ == "__main__":
    unittest.main()
