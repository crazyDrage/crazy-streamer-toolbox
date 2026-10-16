from nicegui import ui

from streamer_toolbox.core.events.event_recording import KEEP_DAYS, EventRecording


class EventRecordingPanel:
    """Settings → Event recording: the switch for writing every event into a file per day (EventRecording),
    where the files are and how much is there."""

    def __init__(self, recording: EventRecording) -> None:
        self._recording = recording

    @ui.refreshable_method
    def build(self) -> None:
        recording = self._recording
        ui.label("Event recording").classes("text-lg font-semibold")
        ui.label("Writes every event (chat, redeems, follows, heart rate, VTube Studio, ...) into a file, one "
                 "line each, one file per day. For looking at a stream afterwards and as test data. Timer ticks "
                 "are left out.").classes("text-sm opacity-80")
        ui.switch("Record every event", value=recording.on, on_change=lambda e: self._set(e.value))
        ui.label("Recording now." if recording.on else "Off: nothing is written.") \
            .classes("text-sm font-medium" + (" text-positive" if recording.on else " opacity-80"))
        files, size = recording.size()
        ui.label(f"{files} day file(s), {size / 1024 / 1024:.1f} MB, in:").classes("text-sm")
        ui.label(str(recording.folder)).classes("text-sm font-mono break-all")
        ui.label(f"The files stay on this PC, and your viewers' chat messages are in them. A day's file is "
                 f"removed after {KEEP_DAYS} days, when the toolbox starts. The switch counts at once, no "
                 f"restart.").classes("text-xs opacity-60")

    def _set(self, on: bool) -> None:
        self._recording.set_on(on)
        self.build.refresh()
