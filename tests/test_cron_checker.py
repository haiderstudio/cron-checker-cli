"""Tests for cron_checker — standard library unittest only."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import cron_checker  # noqa: E402


def write(tmp, name, text, encoding="utf-8"):
    path = Path(tmp) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    return path


def run_cli(*args, cwd=None):
    argv = [sys.executable, str(SRC / "cron_checker.py"), *args]
    return subprocess.run(
        argv, capture_output=True, text=True, cwd=cwd or ROOT
    )


class TestCheckFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def check(self, text):
        path = write(self.tmp.name, "jobs.cron", text)
        return cron_checker.check_file(path)

    def test_clean_expression(self):
        self.assertEqual(self.check("0 9 * * 1-5\n"), [])

    def test_all_stars(self):
        self.assertEqual(self.check("* * * * *\n"), [])

    def test_expression_with_command(self):
        self.assertEqual(
            self.check("0 9 * * 1-5 /usr/bin/backup.sh\n"), []
        )

    def test_command_with_equals_is_not_env_line(self):
        # The first token is a number, so this is a schedule
        # line, not an env assignment.
        self.assertEqual(
            self.check("0 9 * * * FOO=bar /usr/bin/run.sh\n"), []
        )

    def test_lists(self):
        self.assertEqual(
            self.check("0,15,30,45 * * * *\n"), []
        )

    def test_ranges(self):
        self.assertEqual(self.check("0 9-17 * * *\n"), [])

    def test_steps(self):
        self.assertEqual(self.check("*/15 * * * *\n"), [])

    def test_range_with_step(self):
        self.assertEqual(self.check("0 9-17/2 * * *\n"), [])

    def test_value_with_step(self):
        self.assertEqual(self.check("0 2/3 * * *\n"), [])

    def test_month_names(self):
        self.assertEqual(self.check("0 0 1 JAN *\n"), [])

    def test_month_names_lowercase(self):
        self.assertEqual(self.check("0 0 1 jan *\n"), [])

    def test_month_name_range(self):
        self.assertEqual(self.check("0 0 * JAN-MAR *\n"), [])

    def test_weekday_names(self):
        self.assertEqual(self.check("0 12 * * MON-FRI\n"), [])

    def test_weekday_names_lowercase(self):
        self.assertEqual(self.check("0 12 * * mon-fri\n"), [])

    def test_sunday_as_zero(self):
        self.assertEqual(self.check("0 0 * * 0\n"), [])

    def test_sunday_as_seven(self):
        self.assertEqual(self.check("0 0 * * 7\n"), [])

    def test_leading_zeros(self):
        self.assertEqual(self.check("09 08 * * *\n"), [])

    def test_comments_and_blank_lines_skipped(self):
        self.assertEqual(
            self.check(
                "# a comment\n\n  # indented comment\n0 9 * * *\n\n"
            ),
            [],
        )

    def test_file_with_only_comments_is_clean(self):
        self.assertEqual(
            self.check("# nothing but a comment\n"), []
        )

    def test_empty_file_is_clean(self):
        self.assertEqual(self.check(""), [])

    def test_shortcut_daily(self):
        self.assertEqual(self.check("@daily /usr/bin/cleanup.sh\n"), [])

    def test_shortcut_weekly(self):
        self.assertEqual(self.check("@weekly /usr/bin/report.sh\n"), [])

    def test_shortcut_reboot(self):
        self.assertEqual(self.check("@reboot /usr/bin/start.sh\n"), [])

    def test_shortcut_midnight(self):
        self.assertEqual(self.check("@midnight /usr/bin/job.sh\n"), [])

    def test_shortcut_case_insensitive(self):
        self.assertEqual(self.check("@DAILY /usr/bin/job.sh\n"), [])

    def test_env_line_skipped(self):
        self.assertEqual(
            self.check("MAILTO=ops@example.com\n"), []
        )

    def test_env_line_with_path(self):
        self.assertEqual(
            self.check("SHELL=/bin/sh\n0 9 * * *\n"), []
        )

    def test_too_few_fields(self):
        problems = self.check("0 9 * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("expected 5 fields, found 4", problems[0])
        self.assertIn(":1:", problems[0])

    def test_one_field_only(self):
        problems = self.check("hello\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("expected 5 fields, found 1", problems[0])

    def test_minute_out_of_range(self):
        problems = self.check("60 * * * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("minute: 60 is out of range (0-59)",
                      problems[0])

    def test_hour_out_of_range(self):
        problems = self.check("0 24 * * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("hour: 24 is out of range (0-23)", problems[0])

    def test_day_of_month_out_of_range(self):
        problems = self.check("0 0 32 * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("day of month: 32 is out of range (1-31)",
                      problems[0])

    def test_day_of_month_zero(self):
        problems = self.check("0 0 0 * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("day of month: 0 is out of range (1-31)",
                      problems[0])

    def test_month_out_of_range(self):
        problems = self.check("0 0 * 13 *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("month: 13 is out of range (1-12)",
                      problems[0])

    def test_weekday_out_of_range(self):
        problems = self.check("0 0 * * 8\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("day of week: 8 is out of range (0-7)",
                      problems[0])

    def test_bad_month_name(self):
        problems = self.check("0 0 * FOO *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("month: 'FOO' is not a number or a name",
                      problems[0])

    def test_bad_weekday_name(self):
        problems = self.check("0 0 * * FUNDAY\n")
        self.assertEqual(len(problems), 1)
        self.assertIn(
            "day of week: 'FUNDAY' is not a number or a name",
            problems[0],
        )

    def test_step_zero(self):
        problems = self.check("*/0 * * * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("minute: step must be at least 1", problems[0])

    def test_step_not_a_number(self):
        problems = self.check("*/x * * * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("minute: step 'x' is not a number", problems[0])

    def test_too_many_slashes(self):
        problems = self.check("1/2/3 * * * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("minute: too many '/'", problems[0])

    def test_reversed_range(self):
        problems = self.check("5-1 * * * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn(
            "minute: range '5-1' starts after it ends", problems[0]
        )

    def test_range_out_of_range(self):
        problems = self.check("0 0 * * 6-9\n")
        self.assertEqual(len(problems), 1)
        self.assertIn(
            "day of week: range '6-9' is out of range (0-7)",
            problems[0],
        )

    def test_range_with_bad_name(self):
        problems = self.check("0 0 * JAN-FOO *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("month: 'FOO' is not a number or a name",
                      problems[0])

    def test_empty_list_item(self):
        problems = self.check("1,,2 * * * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("minute: empty item in list", problems[0])

    def test_trailing_comma(self):
        problems = self.check("1, * * * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("minute: empty item in list", problems[0])

    def test_unknown_shortcut(self):
        problems = self.check("@every 1h\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("unknown schedule '@every'", problems[0])

    def test_nonstandard_l_flagged(self):
        # L, W and # are not standard cron — they fail here.
        problems = self.check("0 0 L * *\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("day of month: 'L' is not a number",
                      problems[0])

    def test_line_numbers_point_at_the_bad_line(self):
        problems = self.check(
            "0 9 * * *\n0 24 * * *\n0 9 * * *\n"
        )
        self.assertEqual(len(problems), 1)
        self.assertIn(":2:", problems[0])

    def test_missing_file(self):
        problems = cron_checker.check_file(
            Path(self.tmp.name) / "jobs.cron"
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("jobs.cron", problems[0])

    def test_non_utf8_file(self):
        path = Path(self.tmp.name) / "jobs.cron"
        path.write_bytes(b"0 9 * * *\nBAD=\xff\xfe\n")
        problems = cron_checker.check_file(path)
        self.assertEqual(len(problems), 1)
        self.assertIn("UTF-8", problems[0])

    def test_crlf_line_endings(self):
        self.assertEqual(
            self.check("0 9 * * *\r\n0 10 * * *\r\n"), []
        )


class TestCollect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_single_file(self):
        path = write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        files, problems = cron_checker.collect(
            [str(path)], True, []
        )
        self.assertEqual(files, [path])
        self.assertEqual(problems, [])

    def test_named_file_need_not_be_cron_named(self):
        path = write(self.tmp.name, "settings.txt", "0 9 * * *\n")
        files, _ = cron_checker.collect([str(path)], True, [])
        self.assertEqual(files, [path])

    def test_folder_picks_cron_files_only(self):
        write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        write(self.tmp.name, "crontab", "0 9 * * *\n")
        write(self.tmp.name, "notes.txt", "0 9 * * *\n")
        write(self.tmp.name, "app.py", "0 9 * * *\n")
        write(self.tmp.name, "list.crontab", "0 9 * * *\n")
        files, problems = cron_checker.collect(
            [self.tmp.name], True, []
        )
        self.assertEqual(
            sorted(f.name for f in files),
            ["crontab", "jobs.cron", "list.crontab", "notes.txt"],
        )
        self.assertEqual(problems, [])

    def test_folder_recursive(self):
        write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        write(self.tmp.name, "sub/jobs.cron", "0 9 * * *\n")
        files, _ = cron_checker.collect([self.tmp.name], True, [])
        self.assertEqual(len(files), 2)

    def test_folder_no_recursive(self):
        write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        write(self.tmp.name, "sub/jobs.cron", "0 9 * * *\n")
        files, _ = cron_checker.collect(
            [self.tmp.name], False, []
        )
        self.assertEqual(len(files), 1)

    def test_git_folder_skipped(self):
        write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        write(self.tmp.name, ".git/jobs.cron", "0 9 * * *\n")
        files, _ = cron_checker.collect([self.tmp.name], True, [])
        self.assertEqual(len(files), 1)

    def test_exclude_pattern(self):
        write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        write(self.tmp.name, "old.cron", "0 9 * * *\n")
        files, _ = cron_checker.collect(
            [self.tmp.name], True, ["old.cron"]
        )
        self.assertEqual([f.name for f in files], ["jobs.cron"])

    def test_missing_path(self):
        files, problems = cron_checker.collect(
            [str(Path(self.tmp.name) / "jobs.cron")], True, []
        )
        self.assertEqual(files, [])
        self.assertEqual(len(problems), 1)
        self.assertIn("no such file or folder", problems[0])


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_clean_exit_0(self):
        path = write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK — 1 file(s) checked", result.stdout)
        self.assertIn("cron expressions are well formed",
                      result.stdout)

    def test_bad_exit_1(self):
        path = write(self.tmp.name, "jobs.cron", "60 * * * *\n")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stdout)
        self.assertIn("out of range", result.stdout)

    def test_no_args_exit_2(self):
        result = run_cli()
        self.assertEqual(result.returncode, 2)

    def test_bad_flag_exit_2(self):
        result = run_cli("--nope")
        self.assertEqual(result.returncode, 2)

    def test_version(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("1.0.0", result.stdout)

    def test_json_output(self):
        path = write(self.tmp.name, "jobs.cron", "60 * * * *\n")
        result = run_cli(str(path), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["checked"], 1)
        self.assertEqual(payload["summary"]["problems"], 1)
        self.assertIn("out of range",
                      payload["files"][0]["problems"][0])
        # The summary line goes to stderr, stdout stays clean JSON.
        self.assertIn("Checked 1 file(s)", result.stderr)

    def test_json_clean(self):
        path = write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        result = run_cli(str(path), "--json")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["problems"], 0)

    def test_input_files_unchanged(self):
        text = "60 * * * *\n"
        path = write(self.tmp.name, "jobs.cron", text)
        run_cli(str(path))
        self.assertEqual(path.read_text(), text)

    def test_folder_argument(self):
        write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        write(self.tmp.name, "bad.cron", "60 * * * *\n")
        result = run_cli(self.tmp.name)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Checked 2 file(s)", result.stdout)

    def test_exclude_flag(self):
        write(self.tmp.name, "jobs.cron", "0 9 * * *\n")
        write(self.tmp.name, "bad.cron", "60 * * * *\n")
        result = run_cli(self.tmp.name, "--exclude", "bad.cron")
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK — 1 file(s) checked", result.stdout)


class TestExamples(unittest.TestCase):
    def test_sample_output_matches_fresh_run(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)
        expected = (ROOT / "examples" / "sample-output.md").read_text()
        self.assertEqual(result.stdout, expected)

    def test_readme_quoted_outputs(self):
        readme = (ROOT / "README.md").read_text()
        good = run_cli("examples/good.cron")
        self.assertEqual(good.returncode, 0)
        self.assertIn(
            "OK — 1 file(s) checked, cron expressions are well "
            "formed.",
            readme,
        )
        bad = run_cli("examples/bad-fields.cron")
        self.assertEqual(bad.returncode, 1)
        for line in bad.stdout.strip().splitlines():
            self.assertIn(line, readme)
        crontab = run_cli("examples/crontab.txt")
        self.assertEqual(crontab.returncode, 0)
        folder = run_cli("examples/")
        self.assertEqual(folder.returncode, 1)
        for line in folder.stdout.strip().splitlines():
            self.assertIn(line, readme)


class TestHygiene(unittest.TestCase):
    def test_stdlib_only(self):
        import ast

        allowed = {
            "argparse", "fnmatch", "json", "re", "sys", "pathlib",
        }
        test_allowed = allowed | {
            "ast", "subprocess", "tempfile", "unittest",
            "cron_checker",  # the module under test
        }
        for path, names in [
            (SRC / "cron_checker.py", allowed),
            (HERE / "test_cron_checker.py", test_allowed),
        ]:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split(".")[0], names)
                elif isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module.split(".")[0], names)

    def test_no_placeholder_or_secrets(self):
        banned = ["TODO", "FIXME", "coming soon", "lorem",
                  "API_KEY", "api_key", "password="]
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if HERE in path.parents:
                continue  # the test file's own word lists
            if path.suffix == ".pyc":
                continue
            text = path.read_text(errors="ignore")
            for word in banned:
                self.assertNotIn(
                    word, text, f"{word} found in {path}"
                )

    def test_no_absolute_paths(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if HERE in path.parents:
                continue  # the test file's own "/tmp/" literals
            if path.suffix in {".pyc", ".env"}:
                continue
            text = path.read_text(errors="ignore")
            self.assertNotIn("/home/", text, f"absolute path in {path}")
            self.assertNotIn("/tmp/", text, f"absolute path in {path}")

    def test_gitignore_has_env_first(self):
        lines = (ROOT / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_fake_git_hooks_todo_does_not_break_scan(self):
        # The Day 21 lesson: a scan that walks .git hits GitHub's own
        # sample hooks containing "TODO". Our scans exclude .git.
        with tempfile.TemporaryDirectory() as tmp:
            hooks = Path(tmp) / ".git" / "hooks"
            hooks.mkdir(parents=True)
            (hooks / "sendemail-validate.sample").write_text(
                "# TODO: fix this\n"
            )
            found = []
            for path in Path(tmp).rglob("*"):
                if not path.is_file():
                    continue
                if ".git" in path.parts or "__pycache__" in path.parts:
                    continue
                if "TODO" in path.read_text(errors="ignore"):
                    found.append(path)
            self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
