"""The file endings a box's file field takes (actions.add(..., files={"file": MEDIA_TYPES})): what the file window
lists. ANY_FILE = every file; FOLDER = the field wants a folder, not a file."""

VIDEO_TYPES = (".mp4", ".mkv", ".mov", ".webm", ".avi", ".flv", ".m4v", ".gif")
AUDIO_TYPES = (".ogg", ".mp3", ".wav", ".flac", ".m4a", ".aac", ".opus")
IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tga")
MEDIA_TYPES = tuple(dict.fromkeys(VIDEO_TYPES + AUDIO_TYPES))  # what an OBS Media Source plays
ANY_FILE: tuple[str, ...] = ()
FOLDER = ("<folder>",)
