"""Sphinx settings for the manual. Build it with: python -m streamer_toolbox.devtools.package docs"""
project = "streamer-toolbox"
author = "crazyDrage"
copyright = "crazyDrage. Apache License 2.0"

extensions = ["myst_parser"]
source_suffix = {".md": "markdown"}
exclude_patterns = ["_build"]
# pages take sections out of other Markdown files; those start below their own first heading
suppress_warnings = ["myst.header"]
myst_heading_anchors = 3

html_theme = "furo"
html_title = "streamer-toolbox"
html_show_sourcelink = False
