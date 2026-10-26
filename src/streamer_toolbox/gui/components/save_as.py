import json

from nicegui import ui

# the browser's own Save as window (Chrome / Edge: showSaveFilePicker); "fallback" = a browser without it, or one
# that refuses because the click is too long ago; "cancel" = he closed the window
_SCRIPT = """
async () => {
  if (!window.showSaveFilePicker) return "fallback";
  try {
    const handle = await window.showSaveFilePicker({suggestedName: %(name)s});
    const writable = await handle.createWritable();
    await writable.write(new Blob([%(text)s], {type: %(mime)s}));
    await writable.close();
    return "saved";
  } catch (e) {
    return e.name === "AbortError" ? "cancel" : "fallback";
  }
}
"""


class SaveAs:
    """Saves text to a file he picks in a Save as window (his round 60: Export folder should ask where). A browser
    without that window gets the file as a normal download, as before."""

    @staticmethod
    async def text(text: str, name: str, mime: str) -> bool:
        """True if the file was saved or downloaded, False if he cancelled."""
        script = _SCRIPT % {"name": json.dumps(name), "text": json.dumps(text), "mime": json.dumps(mime)}
        try:
            answer = await ui.run_javascript(f"({script})()", timeout=600)
        except TimeoutError:
            return False
        if answer == "cancel":
            return False
        if answer != "saved":
            ui.download.content(text, name, mime)
        return True
