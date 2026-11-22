from pathlib import Path

from streamer_toolbox.core.testing.test_item import KIND_TITLES, TestItem

CHECK_TITLES = (("works", "Works"), ("understandable", "Understandable"), ("usable", "Usable"))


class TriedPage:
    """The public list of what crazyDrage has tried (his 11-21: "set it in the doc, too. As an public list"):
    docs/manual/user/tried.md, made from the test record (docs/tested/) each time the tested tool runs, so it
    never says more than the record. Only rows with at least one of his checks; grouped like the record."""

    def __init__(self, file: Path) -> None:
        self._file = file

    def write(self, items: list[TestItem], checks_of) -> int:
        """Writes the page; gives how many things are on it. checks_of(key) → {"works": bool, ...}."""
        tried = [(item, checks_of(item.key)) for item in items if any(checks_of(item.key).values())]
        lines = ["# What has been tried", "",
                 "Everything below was tried by hand in the running toolbox. Works: it does what it says.",
                 "Understandable: its name and help make sense. Usable: it is easy enough to use. The rest of",
                 "the toolbox is there too, but nobody has tried it by hand yet. Settings → What you see can",
                 "hide the untried parts.", "",
                 "This page is made from the test record (`docs/tested/` in the source) and is never edited by "
                 "hand.", ""]
        if not tried:
            lines.append("Nothing yet.")
        for kind, title in KIND_TITLES.items():
            rows = sorted(((item, checks) for item, checks in tried if item.kind == kind),
                          key=lambda row: (row[0].heading.casefold(), row[0].title.casefold()))
            if not rows:
                continue
            lines += [f"## {title}", "", "| What | Where | " + " | ".join(t for _, t in CHECK_TITLES) + " |",
                      "|---|---|" + "---|" * len(CHECK_TITLES)]
            for item, checks in rows:
                marks = " | ".join("yes" if checks.get(check) else "-" for check, _ in CHECK_TITLES)
                where = item.heading or item.area
                lines.append(f"| {item.title} | {where} | {marks} |")
            lines.append("")
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
        return len(tried)
