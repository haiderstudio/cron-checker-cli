#!/bin/sh
# Demo: check the good file and the crontab (both pass), then the
# bad-fields file (fails, on purpose). The failing run exits 1,
# which is the expected result — the script ends with exit 0 so
# it can be run as a demo.
cd "$(dirname "$0")/.."
python3 src/cron_checker.py examples/good.cron
python3 src/cron_checker.py examples/crontab.txt
python3 src/cron_checker.py examples/bad-fields.cron || true
