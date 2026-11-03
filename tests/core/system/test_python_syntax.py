import unittest

from streamer_toolbox.core.system.python_syntax import syntax_problem


class TestPythonSyntax(unittest.TestCase):
    def test_fine_code_has_no_problem(self) -> None:
        self.assertEqual("", syntax_problem("def run():\n    return {}\n"))

    def test_a_mistake_names_its_line(self) -> None:
        self.assertRegex(syntax_problem("def run():\n    return {\n\nx = )\n"), r"^line \d+: ")

    def test_nothing_in_it_runs(self) -> None:
        self.assertEqual("", syntax_problem("raise SystemExit('must not run')\n"))


if __name__ == "__main__":
    unittest.main()
