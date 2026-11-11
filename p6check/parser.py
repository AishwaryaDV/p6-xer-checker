"""Minimal parser for Primavera P6 .xer files.

An .xer file is plain tab-delimited text with a simple table structure:

    ERMHDR  <version>  <date>  ...          <- one header line
    %T  TABLE_NAME                          <- starts a table
    %F  field1  field2  field3  ...         <- column names for that table
    %R  value1  value2  value3  ...         <- one data row (repeated)
    %T  NEXT_TABLE
    ...
    %E                                      <- end of file

P6 writes these files in Windows-1252 (cp1252) encoding, not UTF-8, so we
decode with cp1252 and fall back to a lenient decode if anything is off.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Table:
    """One table from the .xer file (e.g. TASK, TASKPRED)."""

    name: str
    fields: list[str] = field(default_factory=list)
    # Each row is kept both as a raw value list and (for valid rows) a dict.
    rows: list[dict[str, str]] = field(default_factory=list)
    # Rows whose column count does not match the header ("broken" rows).
    broken: list["BrokenRow"] = field(default_factory=list)


@dataclass
class BrokenRow:
    table: str
    line_no: int
    reason: str
    expected_cols: int
    actual_cols: int
    raw: str


@dataclass
class XerFile:
    path: str
    header: list[str] = field(default_factory=list)
    tables: dict[str, Table] = field(default_factory=dict)

    @property
    def broken_rows(self) -> list[BrokenRow]:
        out: list[BrokenRow] = []
        for t in self.tables.values():
            out.extend(t.broken)
        return out

    def table(self, name: str) -> Table | None:
        return self.tables.get(name)


def _read_text(path: str) -> str:
    with open(path, "rb") as fh:
        raw = fh.read()
    # P6 exports are cp1252; fall back to latin-1 which never raises.
    for enc in ("cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_xer(path: str) -> XerFile:
    """Parse an .xer file into an XerFile with typed tables and broken rows."""
    xer = XerFile(path=path)
    current: Table | None = None

    text = _read_text(path)
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        parts = line.split("\t")
        tag = parts[0]

        if tag == "ERMHDR":
            xer.header = parts[1:]
        elif tag == "%T":
            name = parts[1] if len(parts) > 1 else ""
            current = Table(name=name)
            xer.tables[name] = current
        elif tag == "%F":
            if current is not None:
                current.fields = parts[1:]
        elif tag == "%R":
            if current is None:
                continue
            values = parts[1:]
            if len(values) != len(current.fields):
                current.broken.append(
                    BrokenRow(
                        table=current.name,
                        line_no=line_no,
                        reason=(
                            "column count mismatch: "
                            f"{len(values)} values vs {len(current.fields)} fields"
                        ),
                        expected_cols=len(current.fields),
                        actual_cols=len(values),
                        raw=line[:200],
                    )
                )
                continue
            current.rows.append(dict(zip(current.fields, values)))
        elif tag == "%E":
            break
        # Any other leading token (rare: wrapped memo text) is ignored.

    return xer
