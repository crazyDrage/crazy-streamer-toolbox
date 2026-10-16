from nicegui import ui

# Quasar sends "blur" when the focus leaves the whole field (a click on one of its choices doesn't count): the
# text still in its input comes along
TYPED_ON_BLUR = "(e) => emit(e && e.target && 'value' in e.target ? e.target.value : null)"


def keep_typed(select: ui.select) -> ui.select:
    """A dropdown you can also type into (new_value_mode) takes typed text only on Enter; a click somewhere else
    threw it away (his round 52: "Name will reset the value if I don't push enter"). With this, leaving the
    field takes it too. Text that is the chosen choice's own name (fill-input shows it) changes nothing."""

    def left(e) -> None:
        text = (e.args or "").strip() if isinstance(e.args, str) else ""
        if not text or text == _label(select):
            return
        if isinstance(select.options, dict):
            key = next((k for k, v in select.options.items() if v == text), text)
            select.options.setdefault(key, text)
        else:
            key = text
            if text not in select.options:
                select.options.append(text)
        select.update()
        select.set_value(key)

    select.on("blur", left, js_handler=TYPED_ON_BLUR)
    return select


def _label(select: ui.select) -> str:
    value = select.value
    if isinstance(select.options, dict):
        return str(select.options.get(value, value or ""))
    return "" if value is None else str(value)
