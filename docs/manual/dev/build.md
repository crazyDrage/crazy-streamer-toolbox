# Building the downloads

Two downloads are built, both into `build/` (not tracked by git).

## The toolbox

```
$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m streamer_toolbox.devtools.package
```

Gives `build/streamer-toolbox.zip`: the toolbox, its own Python and every library from `requirements.txt`,
two start scripts, the short guide as `README.md`. Nothing has to be installed on the other PC (Windows,
64 bit).

Only files git tracks go in, and of those only the code, the plugins, the example settings and the listed
docs. The `config/` folder (settings, logins, flows) can't get in.

## The docs

```
.venv\Scripts\python.exe -m pip install -r requirements-docs.txt
$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m streamer_toolbox.devtools.package docs
```

Gives `build/streamer-toolbox-docs.zip`:

- `manual/`: this manual as web pages. Open `manual/index.html`.
- `for-ai/`: `llms.txt` and the small Markdown files it leads to, for AI agents.

The manual's source is `docs/manual/`. Most pages take their text from the Markdown files in `docs/`
(`USER_GUIDE.md`, `WIDGETS.md`, `PLUGINS.md`, `ARCHITECTURE.md`, `docs/ai/`), so a text is changed in one
place. A page that takes one section of `USER_GUIDE.md` names the headings it starts and ends at: when you
rename a heading there, the docs build fails and names the page.

Sphinx and its theme are only needed for building the docs. They are in `requirements-docs.txt`, not in
`requirements.txt`, so they don't end up in the toolbox download.
