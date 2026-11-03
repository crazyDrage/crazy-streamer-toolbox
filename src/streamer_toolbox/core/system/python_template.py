import json

HEAD = '''"""A Python box of streamer-toolbox (Run Python).

The toolbox calls {function}() with the box's inputs, by their names.
What {function}() gives back goes to the box's outputs: a dict with one key per output.
print() goes to the box's "printed" output.

You can add imports and more functions; only {function}() is called.
The toolbox's own Python has only its own libraries: for others, set the box's Python to a .venv's python.
"""


'''


def python_template(function: str, inputs: list[str], outputs: list[str]) -> str:
    """The text of a new file for the box: `function` with its inputs as parameters and a return of its
    outputs. A name that can't be a Python name (it has a space, a dash, ...) arrives in `values` instead."""
    params = [f"{name}=None" for name in inputs if name.isidentifier()]
    if len(params) < len(inputs):
        params.append("**values")
    body = [f"    {name} = None  # work it out here" for name in outputs if name.isidentifier()]
    gives = ", ".join(f"{json.dumps(name)}: {name if name.isidentifier() else 'None'}" for name in outputs)
    return HEAD.format(function=function) + f"def {function}({', '.join(params)}):\n" \
        + ("\n".join(body) + "\n" if body else "") + f"    return {{{gives}}}\n"
