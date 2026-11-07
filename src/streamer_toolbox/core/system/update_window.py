import logging
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)
CLOSE_AFTER_MS = 6000  # after the new version is started: its own window opens a few seconds later


class UpdateWindow:
    """A small window while the update puts the new files in (his v0.4.0-dev.2 try, 2026-11-07: "with no visual
    update bar and information, the user will try to open the toolbox again"). It says what happens, has a
    moving bar, and closes a few seconds after the new version is started. `work` runs in a thread of its own
    and gives what the window says at the end. Without a screen or tkinter, `work` just runs."""

    def __init__(self, version: str) -> None:
        self._version = version

    def run(self, work: Callable[[], str]) -> None:
        try:
            import tkinter as tk
            from tkinter import ttk
            root = tk.Tk()
        except Exception as e:  # no tkinter, no screen (a Linux server): the update runs without a window
            log.info("no update window: %s", e)
            work()
            return
        root.title("crazy-streamer-toolbox update")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.protocol("WM_DELETE_WINDOW", lambda: None)  # closing it wouldn't stop the update, only hide it
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"Updating to {self._version} ...", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        said = ttk.Label(frame, text="The toolbox starts again by itself in a minute or two.\n"
                                     "Please don't start it yourself until then.", justify="left")
        said.pack(anchor="w", pady=(8, 12))
        bar = ttk.Progressbar(frame, mode="indeterminate", length=360)
        bar.pack(fill="x")
        bar.start(12)
        root.update_idletasks()
        x = (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2
        y = (root.winfo_screenheight() - root.winfo_reqheight()) // 3
        root.geometry(f"+{x}+{y}")
        ended: list[str] = []

        def in_thread() -> None:
            try:
                ended.append(work())
            except Exception as e:  # work writes its own result; this only keeps the window from waiting forever
                log.exception("the update failed")
                ended.append(f"The update stopped: {e}")

        def look() -> None:
            if not ended:
                root.after(200, look)
                return
            bar.stop()
            bar.configure(mode="determinate", value=100)
            said.configure(text=ended[0])
            root.after(CLOSE_AFTER_MS, root.destroy)

        threading.Thread(target=in_thread, daemon=True).start()
        root.after(200, look)
        root.mainloop()
