OK — 1 file(s) checked, cron expressions are well formed.
OK — 1 file(s) checked, cron expressions are well formed.
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
