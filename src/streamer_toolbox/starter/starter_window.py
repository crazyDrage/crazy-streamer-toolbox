import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox
from collections.abc import Callable
from tkinter import ttk

from streamer_toolbox.core.app_name import APP_NAME
from streamer_toolbox.core.system.starter_settings import OPEN_MODES
from streamer_toolbox.starter.starter_app import StarterApp


class StarterWindow:
    """The starter's small window (his round 84 layout): how the toolbox opens, Start, whether it starts like
    that next time without asking, its status with Open / Restart / Stop, and the backups. Tkinter, so it needs
    nothing the toolbox's web code needs. The tray (StarterTray) and other threads hand it work through call(),
    which runs on Tk's own thread."""

    def __init__(self, app: StarterApp, has_tray: bool = False) -> None:
        self._app = app
        self._has_tray = has_tray
        self._todo: queue.Queue[Callable[[], None]] = queue.Queue()
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        settings = app.settings
        self._mode = tk.StringVar(value=settings.open_mode)
        self._without_asking = tk.BooleanVar(value=settings.start_without_asking)
        self._close_stops = tk.BooleanVar(value=settings.close_stops)
        self._backup_on_start = tk.BooleanVar(value=settings.backup_on_start)
        self._ask_on_close = tk.BooleanVar(value=settings.ask_backup_on_close)
        self._daily = tk.IntVar(value=settings.daily)
        self._monthly = tk.IntVar(value=settings.monthly)
        self._status = tk.StringVar()
        self._last_backup = tk.StringVar()
        self.on_quit: Callable[[], None] = lambda: None
        self._build()
        self._tick()

    def _build(self) -> None:
        pad = {"padx": 12, "pady": 4}
        frame = ttk.Frame(self.root, padding=8)
        frame.grid(sticky="nsew")
        frame.columnconfigure(0, weight=1)  # the dividing lines go across
        ttk.Label(frame, text="How to open it", font=("", 10, "bold")).grid(sticky="w", **pad)
        for mode, label in OPEN_MODES.items():
            text = label + (f"  ({self._app.url})" if mode == "none" else "")
            ttk.Radiobutton(frame, text=text, value=mode, variable=self._mode, command=self._changed) \
                .grid(sticky="w", padx=24)
        ttk.Checkbutton(frame, text="Start like this next time without asking", variable=self._without_asking,
                        command=self._changed).grid(sticky="w", **pad)
        ttk.Checkbutton(frame, text="Closing the toolbox's window stops the toolbox", variable=self._close_stops,
                        command=self._changed).grid(sticky="w", padx=12)
        self._start_button = ttk.Button(frame, text="Start", command=self.start)
        self._start_button.grid(sticky="w", **pad)

        ttk.Separator(frame).grid(sticky="ew", pady=6)
        ttk.Label(frame, textvariable=self._status).grid(sticky="w", **pad)
        buttons = ttk.Frame(frame)
        buttons.grid(sticky="w", padx=12)
        self._running_buttons = [ttk.Button(buttons, text="Open", command=self._app.open),
                                 ttk.Button(buttons, text="Restart", command=self._app.restart),
                                 ttk.Button(buttons, text="Stop", command=self._app.stop)]
        for column, button in enumerate(self._running_buttons):
            button.grid(row=0, column=column, padx=(0, 6))

        ttk.Separator(frame).grid(sticky="ew", pady=6)
        ttk.Label(frame, text="Backups of the settings", font=("", 10, "bold")).grid(sticky="w", **pad)
        ttk.Checkbutton(frame, text="Back up once a day when it starts", variable=self._backup_on_start,
                        command=self._changed).grid(sticky="w", padx=12)
        ttk.Checkbutton(frame, text="Ask \"Back up now?\" when closing", variable=self._ask_on_close,
                        command=self._changed).grid(sticky="w", padx=12)
        keep = ttk.Frame(frame)
        keep.grid(sticky="w", **pad)
        ttk.Label(keep, text="Keep").grid(row=0, column=0)
        for column, (variable, label) in enumerate(((self._daily, "daily"), (self._monthly, "monthly")), 1):
            ttk.Spinbox(keep, from_=0, to=99, width=4, textvariable=variable, command=self._changed) \
                .grid(row=0, column=column * 2 - 1, padx=(6, 2))
            ttk.Label(keep, text=label).grid(row=0, column=column * 2)
        backup_row = ttk.Frame(frame)
        backup_row.grid(sticky="w", **pad)
        ttk.Button(backup_row, text="Back up now", command=self._back_up).grid(row=0, column=0)
        ttk.Label(backup_row, textvariable=self._last_backup).grid(row=0, column=1, padx=8)
        ttk.Label(frame, text=f"Settings: {self._app.settings_folder}", foreground="gray") \
            .grid(sticky="w", **pad)

    def call(self, work: Callable[[], None]) -> None:
        """Runs work on Tk's thread (from the tray or the launcher's thread)."""
        self._todo.put(work)

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self) -> None:
        self.root.withdraw()

    def _changed(self) -> None:
        settings = self._app.settings
        settings.open_mode = self._mode.get()
        settings.start_without_asking = self._without_asking.get()
        settings.close_stops = self._close_stops.get()
        settings.backup_on_start = self._backup_on_start.get()
        settings.ask_backup_on_close = self._ask_on_close.get()
        try:
            settings.daily, settings.monthly = max(0, self._daily.get()), max(0, self._monthly.get())
        except tk.TclError:  # a half-typed number: kept as it was until it is one
            return
        self._app.save()

    def start(self) -> None:
        self._changed()
        self._status.set("Starting…")
        threading.Thread(target=self._app.start, daemon=True).start()  # the daily backup may take a moment
        if self._has_tray and self._without_asking.get():
            self.hide()

    def _back_up(self) -> None:
        self._changed()
        self._last_backup.set("backing up…")

        def work() -> None:
            try:
                made = self._app.back_up()
                text = f"done: {made.name}"
            except OSError as e:
                text = f"failed: {e}"
            self.call(lambda: self._last_backup.set(text))

        threading.Thread(target=work, daemon=True).start()

    def _tick(self) -> None:
        while not self._todo.empty():
            self._todo.get_nowait()()
        running = self._app.running
        if running:
            self._status.set(f"Running · {self._app.url}")
        elif self._status.get() != "Starting…":
            self._status.set("Not running")
        self._start_button.state(["disabled"] if running else ["!disabled"])
        for button in self._running_buttons:
            button.state(["!disabled"] if running else ["disabled"])
        if not self._last_backup.get() or self._last_backup.get().startswith("last:"):
            newest = self._app.backup.all()
            self._last_backup.set("last: " + time.strftime("%Y-%m-%d %H:%M", time.localtime(
                newest[0].stat().st_mtime)) if newest else "no backup yet")
        self.root.after(500, self._tick)

    def _close(self) -> None:
        """The X: into the tray while the toolbox runs (it keeps running), else the starter ends."""
        if self._has_tray and self._app.running:
            self.hide()
        else:
            self.quit()

    def quit(self) -> None:
        """Ends the starter and the toolbox; asks "Back up now?" first (his round 84) when that is on. The
        backup is made after the toolbox stopped, so no file is caught half written."""
        back_up = self._app.settings.ask_backup_on_close and messagebox.askyesno(
            "Back up now?", "Back up the toolbox's settings before closing?", parent=self.root)
        self._app.stop()
        if back_up:
            self._app.wait_stopped(20)
            try:
                self._app.back_up()
            except OSError as e:
                messagebox.showerror("Backup failed", str(e), parent=self.root)
        self.on_quit()
        self.root.destroy()
