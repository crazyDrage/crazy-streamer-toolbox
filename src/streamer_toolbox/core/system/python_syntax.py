def syntax_problem(text: str) -> str:
    """What is wrong with Python code before it runs ("line 3: invalid syntax"), or "" when it reads fine. Only
    the writing is checked: nothing in it runs."""
    try:
        compile(text, "code", "exec")
    except SyntaxError as e:
        return f"line {e.lineno}: {e.msg}"
    return ""
