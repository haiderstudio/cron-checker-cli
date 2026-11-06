"""Check cron expressions are well formed.

Reads one or more files holding cron expressions — one per line,
or a whole crontab — and checks each line: five fields, numbers
in range, steps and names allowed, nothing else. Every problem
names the file and line; exits 1 on any problem, so it can fail
a CI run, and 0 when every expression is clean.

Report-only: it never writes to an input file and never touches
a crontab. Standard library only — no packages to install.
"""

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

VERSION = "1.0.0"

MONTH_NAMES = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
WEEKDAY_NAMES = {
    "SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5,
    "SAT": 6,
}

# (field name, lowest value, highest value, names or None)
FIELDS = [
    ("minute", 0, 59, None),
    ("hour", 0, 23, None),
    ("day of month", 1, 31, None),
    ("month", 1, 12, MONTH_NAMES),
    ("day of week", 0, 7, WEEKDAY_NAMES),
]

SHORTCUTS = {
    "@hourly", "@daily", "@midnight", "@weekly", "@monthly",
    "@yearly", "@annually", "@reboot",
}

ENV_LINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _value(token, spec):
    """Turn one token into a number, or None if it is not one.

    A token is a plain number, or a month/weekday name for the
    fields that have names. Names are case-insensitive.
    """
    _, _, _, names = spec
    if token.isdigit():
        return int(token)
    if names is not None:
        return names.get(token.upper())
    return None


def _check_item(item, spec):
    """Problems with one comma-separated item of one field."""
    name, low, high, names = spec
    problems = []
    parts = item.split("/")
    if len(parts) > 2:
        return [f"{name}: too many '/' in {item!r}"]
    base = parts[0]
    if len(parts) == 2:
        step = parts[1]
        if not step.isdigit():
            return [f"{name}: step {step!r} is not a number"]
        if int(step) < 1:
            return [f"{name}: step must be at least 1"]
    if base == "*":
        return problems  # every value, with or without a step
    if "-" in base:
        ends = base.split("-")
        if len(ends) != 2:
            return [f"{name}: bad range {base!r}"]
        start = _value(ends[0], spec)
        end = _value(ends[1], spec)
        if start is None or end is None:
            bad = ends[0] if start is None else ends[1]
            return [f"{name}: {bad!r} is not a number" + (
                " or a name" if names else ""
            )]
        if start < low or start > high or end < low or end > high:
            return [
                f"{name}: range {base!r} is out of range "
                f"({low}-{high})"
            ]
        if start > end:
            return [
                f"{name}: range {base!r} starts after it ends"
            ]
        return problems
    value = _value(base, spec)
    if value is None:
        return [f"{name}: {base!r} is not a number" + (
            " or a name" if names else ""
        )]
    if value < low or value > high:
        return [
            f"{name}: {value} is out of range ({low}-{high})"
        ]
    return problems


def _check_field(field, spec):
    """Problems with one of the five fields."""
    name = spec[0]
    problems = []
    for item in field.split(","):
        if item == "":
            problems.append(f"{name}: empty item in list")
        else:
            problems.extend(_check_item(item, spec))
    return problems


def check_line(line):
    """Problems with one line of a cron file.

    Returns a list of message strings; an empty list means the
    line is fine. Blank lines and `#` comments are skipped. A
    crontab env line (`NAME=value`) is skipped. An `@` shortcut
    line must be a known shortcut. Otherwise the first five
    fields are the schedule and anything after them is the
    command, which is not checked.
    """
    stripped = line.strip()
    if stripped == "" or stripped.startswith("#"):
        return []
    if ENV_LINE.match(stripped):
        return []
    fields = stripped.split()
    if fields[0].startswith("@"):
        if fields[0].lower() in SHORTCUTS:
            return []
        return [
            f"unknown schedule {fields[0]!r} — use @hourly, "
            "@daily, @weekly, @monthly, @yearly or @reboot"
        ]
    if len(fields) < 5:
        return [
            f"expected 5 fields, found {len(fields)}"
        ]
    problems = []
    for field, spec in zip(fields[:5], FIELDS):
        problems.extend(_check_field(field, spec))
    return problems


def check_file(path):
    """Check one cron file.

    Returns a list of "path:line: message" problem strings; an
    empty list means every expression in the file is well formed.
    """
    problems = []
    try:
        handle = open(path, encoding="utf-8")
    except OSError as exc:
        return [f"{path}: {exc.strerror or exc}"]
    with handle:
        try:
            lines = handle.readlines()
        except UnicodeDecodeError:
            return [f"{path}: file is not valid UTF-8"]
    for number, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n").rstrip("\r")
        for message in check_line(line):
            problems.append(f"{path}:{number}: {message}")
    return problems


def is_cron_file(path):
    """True for a file that holds cron expressions: a file named
    `crontab`, or one ending in `.cron`, `.crontab` or `.txt`."""
    name = path.name
    return (
        name == "crontab"
        or name.endswith(".cron")
        or name.endswith(".crontab")
        or name.endswith(".txt")
    )


def collect(paths, recursive, excludes):
    """Turn the named files and folders into a list of cron files.

    Returns (files, problems) where problems are fatal
    "path: message" strings for inputs that do not exist.
    """
    files = []
    problems = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            if recursive:
                found_list = sorted(path.rglob("*"))
            else:
                found_list = sorted(path.iterdir())
            for found in found_list:
                if (
                    found.is_file()
                    and ".git" not in found.parts
                    and is_cron_file(found)
                    and not _excluded(found, excludes)
                ):
                    files.append(found)
        else:
            problems.append(f"{raw}: no such file or folder")
    return files, problems


def _excluded(path, excludes):
    return any(
        fnmatch.fnmatch(path.name, pattern)
        or fnmatch.fnmatch(str(path), pattern)
        for pattern in excludes
    )


def run(argv=None):
    """Run the checker. Returns an exit code: 0 clean, 1 problems,
    2 usage error."""
    parser = argparse.ArgumentParser(
        prog="cron_checker",
        description="Check cron expressions are well formed.",
    )
    parser.add_argument(
        "paths", nargs="*", help="cron files or folders"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="do not walk folders below the top level",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="skip files matching this glob (repeatable)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the result as JSON instead of plain text",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}"
    )
    args = parser.parse_args(argv)
    if not args.paths:
        parser.error("no files or folders given")
    files, collect_problems = collect(
        args.paths, not args.no_recursive, args.exclude
    )
    results = []
    for path in files:
        found = check_file(path)
        results.append((str(path), found))
    all_problems = collect_problems + [
        problem for _, found in results for problem in found
    ]
    failed = [name for name, found in results if found]
    if args.json:
        payload = {
            "files": [
                {"file": name, "ok": not found, "problems": found}
                for name, found in results
            ],
            "summary": {
                "checked": len(results),
                "ok": len(results) - len(failed),
                "failed": len(failed),
                "problems": len(all_problems),
            },
        }
        if collect_problems:
            payload["errors"] = collect_problems
        print(json.dumps(payload, indent=2))
        print(
            f"Checked {len(results)} file(s), "
            f"{len(all_problems)} problem(s).",
            file=sys.stderr,
        )
    else:
        for problem in all_problems:
            print(f"FAIL {problem}")
        if all_problems:
            print(
                f"Checked {len(results)} file(s), "
                f"{len(all_problems)} problem(s) in "
                f"{len(failed) + len(collect_problems)} "
                f"file(s)."
            )
        else:
            print(
                f"OK — {len(results)} file(s) checked, "
                "cron expressions are well formed."
            )
    return 1 if all_problems else 0


def main(argv=None):
    try:
        return run(argv)
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
