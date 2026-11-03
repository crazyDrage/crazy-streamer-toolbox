import unittest

from streamer_toolbox.core.system.python_template import python_template


class TestPythonTemplate(unittest.TestCase):
    def run_template(self, text: str, function: str, **inputs) -> object:
        space: dict = {}
        exec(compile(text, "template.py", "exec"), space)
        return space[function](**inputs)

    def test_inputs_are_parameters_and_outputs_are_given_back(self) -> None:
        text = python_template("run", ["name", "amount"], ["text", "count"])
        self.assertIn("def run(name=None, amount=None):", text)
        self.assertEqual({"text": None, "count": None}, self.run_template(text, "run", name="Kit", amount=5))

    def test_names_that_cant_be_python_names(self) -> None:
        text = python_template("work", ["user name"], ["my text"])
        self.assertIn("def work(**values):", text)
        self.assertEqual({"my text": None}, self.run_template(text, "work", **{"user name": "Kit"}))

    def test_no_inputs_no_outputs(self) -> None:
        self.assertEqual({}, self.run_template(python_template("run", [], []), "run"))


if __name__ == "__main__":
    unittest.main()
