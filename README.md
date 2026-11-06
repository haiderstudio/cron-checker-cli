# cron-checker-cli

Check cron expressions are well formed, fail CI on a bad one.

[![CI](https://github.com/haiderstudio/cron-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/cron-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`cron_checker` reads the cron files and folders you name and
checks every line is a well-formed cron expression: five fields
(minute, hour, day of month, month, day of week), numbers in
range, lists, ranges, steps, and month and weekday names
allowed. Every problem names the file and line, and says which
field broke and why. It exits 1 on any problem, so it can fail
a CI run before a broken schedule ships.

- A line may be a bare expression (`0 9 * * 1-5`) or an
  expression plus a command (`0 9 * * 1-5 /usr/bin/backup.sh`).
  Only the first five fields are checked; the command is not.
- Minute is 0–59, hour 0–23, day of month 1–31, month 1–12,
  day of week 0–7 (7 is Sunday, same as 0). Month names
  (`JAN`–`DEC`) and weekday names (`SUN`–`SAT`) work, in any
  case, in single values, lists, and ranges.
- Lists (`1,15,30`), ranges (`9-17`), steps (`*/15`,
  `9-17/2`), and combinations of them are allowed. A step must
  be a whole number of 1 or more, and a range must start at or
  before where it ends.
- Shortcut lines (`@hourly`, `@daily`, `@midnight`, `@weekly`,
  `@monthly`, `@yearly`, `@annually`, `@reboot`) are accepted.
  Any other `@` word is a problem.
- A whole crontab works too: blank lines and `#` comments are
  skipped, and env lines such as `MAILTO=ops@example.com` are
  skipped as well.
- Folders are walked recursively unless `--no-recursive` is
  given. A folder check looks at cron files: a file named
  `crontab`, or one ending in `.cron`, `.crontab`, or `.txt`.
  `.git` folders are never walked, and folder links are never
  followed. `--exclude PATTERN` skips files by glob
  (repeatable).
- `--json` prints the result as JSON instead of plain text, for
  scripts. The summary line goes to standard error, so standard
  output stays clean JSON.
- A file that cannot be read as UTF-8, or a path that does not
  exist, is reported as a problem, not skipped silently.

## What it does NOT do

- It does not check when a job will next run, or whether two
  jobs overlap. That is the job of a cron parser library, such
  as adhocore/gronx, which works out due dates.
- It does not check that the command after an expression
  exists or runs. Only the five schedule fields are checked.
- It does not install, edit, or remove a crontab. A bad line
  is reported, not repaired.
- It does not fetch files from the network. Every input is a
  local file or folder.

## Who it is for

Anyone who keeps a cron schedule in a file and wants a quick,
scriptable check that it is well formed: a developer adding a
CI step that fails the build on a broken schedule, someone
hand-editing a crontab before installing it, or anyone checking
a list of expressions before they go live. If the file is
clean, you get a plain OK line; if it is not, the report says
exactly which line broke and why.

## How this differs from similar tools

Cron checkers already exist, but none of them is this exact
tool. The exact name `cron-checker-cli` matches 0 repositories
on GitHub. The wider field is mostly libraries and websites:
adhocore/gronx (515 stars) is a Go cron expression parser
library that works out due dates and runs tasks, and
pbyrne/cron-checker (116 stars) is the source of a
cron-checker website — neither is a local file checker. The
closest real rival is wachawo/checkcrontab (62 stars), a
Python script that checks the syntax of crontab files, with
no CI gate and no per-field reasons. The biggest library in
the field, jmrozanec/cron-utils (1,212 stars), is a Java
library for parsing and validating cron expressions — a
library, not a command that checks files and fails CI. This
tool does a narrower job: a Python standard-library-only CLI
that checks expressions in plain list files as well as
crontabs, reports every problem with a file, line, and field,
and exits 1 on a bad expression for CI — no install beyond
Python, no due-date maths, no website, no network.

## Install

Python standard library only — no packages to download. You need
Python 3.8 or newer. Clone the repo and run it in place:

```
git clone https://github.com/haiderstudio/cron-checker-cli.git
cd cron-checker-cli
python3 src/cron_checker.py examples/good.cron
```

```
OK — 1 file(s) checked, cron expressions are well formed.
```

## Usage

Check one file:

```
python3 src/cron_checker.py examples/good.cron
```

Check several files at once:

```
python3 src/cron_checker.py examples/good.cron examples/bad-fields.cron
```

```
FAIL examples/bad-fields.cron:1: expected 5 fields, found 4
FAIL examples/bad-fields.cron:2: minute: 60 is out of range (0-59)
FAIL examples/bad-fields.cron:3: hour: 24 is out of range (0-23)
FAIL examples/bad-fields.cron:4: day of month: 32 is out of range (1-31)
FAIL examples/bad-fields.cron:5: month: 13 is out of range (1-12)
FAIL examples/bad-fields.cron:6: day of week: 8 is out of range (0-7)
FAIL examples/bad-fields.cron:7: minute: step must be at least 1
FAIL examples/bad-fields.cron:8: month: 'FOO' is not a number or a name
FAIL examples/bad-fields.cron:9: day of week: 'FUNDAY' is not a number or a name
FAIL examples/bad-fields.cron:10: minute: range '5-1' starts after it ends
FAIL examples/bad-fields.cron:11: minute: empty item in list
FAIL examples/bad-fields.cron:12: unknown schedule '@every' — use @hourly, @daily, @weekly, @monthly, @yearly or @reboot
Checked 2 file(s), 12 problem(s) in 1 file(s).
```

Check a whole folder:

```
python3 src/cron_checker.py examples/
```

```
FAIL examples/bad-fields.cron:1: expected 5 fields, found 4
FAIL examples/bad-fields.cron:2: minute: 60 is out of range (0-59)
FAIL examples/bad-fields.cron:3: hour: 24 is out of range (0-23)
FAIL examples/bad-fields.cron:4: day of month: 32 is out of range (1-31)
FAIL examples/bad-fields.cron:5: month: 13 is out of range (1-12)
FAIL examples/bad-fields.cron:6: day of week: 8 is out of range (0-7)
FAIL examples/bad-fields.cron:7: minute: step must be at least 1
FAIL examples/bad-fields.cron:8: month: 'FOO' is not a number or a name
FAIL examples/bad-fields.cron:9: day of week: 'FUNDAY' is not a number or a name
FAIL examples/bad-fields.cron:10: minute: range '5-1' starts after it ends
FAIL examples/bad-fields.cron:11: minute: empty item in list
FAIL examples/bad-fields.cron:12: unknown schedule '@every' — use @hourly, @daily, @weekly, @monthly, @yearly or @reboot
Checked 3 file(s), 12 problem(s) in 1 file(s).
```

Machine-readable output with `--json` (the summary goes to
standard error, so standard output is clean JSON):

```
python3 src/cron_checker.py examples/good.cron --json
```

```
{
  "files": [
    {
      "file": "examples/good.cron",
      "ok": true,
      "problems": []
    }
  ],
  "summary": {
    "checked": 1,
    "ok": 1,
    "failed": 0,
    "problems": 0
  }
}
```

Exit codes: 0 when every expression is well formed, 1 when
any file has a problem, 2 for a usage problem (no files given,
a bad flag).

## Examples

### 1. A bad file — twelve problems in twelve lines

`examples/bad-fields.cron` has one of each field problem:

```
python3 src/cron_checker.py examples/bad-fields.cron
```

```
FAIL examples/bad-fields.cron:1: expected 5 fields, found 4
FAIL examples/bad-fields.cron:2: minute: 60 is out of range (0-59)
FAIL examples/bad-fields.cron:3: hour: 24 is out of range (0-23)
FAIL examples/bad-fields.cron:4: day of month: 32 is out of range (1-31)
FAIL examples/bad-fields.cron:5: month: 13 is out of range (1-12)
FAIL examples/bad-fields.cron:6: day of week: 8 is out of range (0-7)
FAIL examples/bad-fields.cron:7: minute: step must be at least 1
FAIL examples/bad-fields.cron:8: month: 'FOO' is not a number or a name
FAIL examples/bad-fields.cron:9: day of week: 'FUNDAY' is not a number or a name
FAIL examples/bad-fields.cron:10: minute: range '5-1' starts after it ends
FAIL examples/bad-fields.cron:11: minute: empty item in list
FAIL examples/bad-fields.cron:12: unknown schedule '@every' — use @hourly, @daily, @weekly, @monthly, @yearly or @reboot
Checked 1 file(s), 12 problem(s) in 1 file(s).
```

### 2. A whole crontab

`examples/crontab.txt` is a full crontab — env lines, a
shortcut line, and commands after the schedule — and it is
clean:

```
python3 src/cron_checker.py examples/crontab.txt
```

```
OK — 1 file(s) checked, cron expressions are well formed.
```

### 3. The bundled examples, all at once

```
sh examples/run-example.sh
```

The script checks the good file and the crontab (both pass),
then the bad-fields file (fails, on purpose). Its full output
is in `examples/sample-output.md`. The failing run exits 1,
which is the expected result — the script ends with exit 0 so
it can be run as a demo.

## How it is tested

76 tests, standard library `unittest` only, no packages to install:

```
python3 tests/test_cron_checker.py
```

The tests cover: clean expressions, lists, ranges, steps,
month and weekday names (any case, in lists and ranges),
Sunday as 0 and 7, leading zeros, bare expressions and
expressions with a command, shortcut lines, crontab env lines,
comments and blank lines, wrong field counts, every field out
of range, bad steps (zero, not a number, too many slashes),
bad names, reversed ranges, ranges out of range, empty list
items, unknown shortcuts, line numbers, missing files,
non-UTF-8 files, CRLF line endings, folder walking (recursive,
`--no-recursive`, `.git` skipped, `--exclude`, only cron files
picked up), `--json` output, `--version`, input files left
unchanged, the bundled examples (sample output compared
byte-for-byte against a fresh run, and the README-quoted
outputs checked against it), and hygiene checks (no
placeholder text, no absolute paths, stdlib imports only,
`.env` first in `.gitignore`).

## Limits

- This tool checks the shape of an expression, not what it
  means: it does not work out the next run time, and it does
  not warn if a schedule runs far more often than you meant
  (such as `* * * * *`).
- Non-standard cron extras — `L` for last day, `W` for
  nearest weekday, `#` for nth weekday — are reported as bad
  values. Only the standard five-field shape is accepted.
- A six-field expression with a seconds field first is
  reported as a bad expression: the seconds field is read as
  the minute, so the fields shift and the line fails.

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The idea of
checking cron expressions is not new — the similar tools named
above (adhocore/gronx, pbyrne/cron-checker,
wachawo/checkcrontab, jmrozanec/cron-utils) are listed in "How
this differs" — but every line of code here is original, and
the tool builds on nothing but Python's standard library.
