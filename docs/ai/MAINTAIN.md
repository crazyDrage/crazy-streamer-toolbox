# Keeping the AI docs working

The AI docs are a trigger map: `llms.txt` is a small index that is always read, everything else is a file
that is read only when its row matches. An AI that only calls the API never loads the plugin or code parts.

## Rules

- **Every new file gets a row in `llms.txt`.** One line. A file without a row is never read.
- **No content in `llms.txt`.** Only the situation and the file. If you want to explain something there,
  it belongs in a file.
- **Word the row by what the reader is trying to do**, not by what the file contains.
  "I want to run something in the toolbox from my own program", not "REST reference".
- **Only `docs/ai/rules.md` is read every time.** Keep it short; a rule goes there only if it applies to
  every task.
- One file answers one situation. When a file grows past about a page, split it and give each half its
  own row.
- A file may point to another file, but must make sense on its own: the reader may have loaded only this one.
- If a part gets more files than fit the table comfortably, give that part its own small index
  (`docs/ai/<part>/INDEX.md`) and let `llms.txt` point to it.
- Describe the tool as it is. What is planned and not built doesn't go in (plans are `docs/PLAN_*.md`).
- When the code changes what a file says, change the file in the same commit.

## The three parts

| Part | Folder | Reader |
|---|---|---|
| 1. Using the toolbox | `docs/ai/use/` | an AI outside, calling the API |
| 2. Writing a plugin | `docs/PLUGINS.md`, `docs/ai/plugin/` | an AI adding a folder to `plugins/` |
| 3. Changing the toolbox | `docs/ai/code/`, `docs/ARCHITECTURE.md` | an AI working in the repository |

`docs/ai/` goes into the packed archive with `llms.txt` (see `devtools/package/packager.py`);
`docs/ARCHITECTURE.md` doesn't.
