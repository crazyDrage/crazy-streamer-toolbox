import unittest

from streamer_toolbox.gui.components.flow_editor.animation_input import AnimationInput

STEP = {"x": 0.1, "y": 0.0, "rotation": 0.0, "size": 0.0, "seconds": 1.0, "wait": 0.5}


class TestAnimationInput(unittest.TestCase):
    def test_short_text_for_the_box(self) -> None:
        self.assertEqual(AnimationInput.text({"relative": True, "steps": [STEP, STEP]}),
                         "2 steps · 3 s · from where the model is")
        self.assertEqual(AnimationInput.text({"relative": False, "steps": [STEP]}), "1 step · 1.5 s · fixed spots")
        self.assertTrue(AnimationInput.text({}).startswith("No steps yet"))
        self.assertEqual(AnimationInput.text({"steps": [{"x": 1}]}), "⚠ can't read it")
