import shutil
import tempfile
import unittest
from pathlib import Path

from check import check

VAULT = Path(__file__).resolve().parent.parent

VALID_PROJECT = """\
---
type: project
title: Parser rewrite
created: 2026-10-01
updated: 2026-10-05
status: active
focus: now
questions: [why-slow]
---
## State
Slowdown reproduced.

## Next
- [ ] profile the large input @ada due:2026-10-09
- [ ] send the weekly report every:friday

## Log
- 2026-10-05 reproduced the slowdown

## Ideas
- try a streaming reader
"""

VALID_QUESTION = """\
---
type: question
title: Why is the parser slow?
created: 2026-10-01
updated: 2026-10-01
status: open
---
## Why it matters
Every import waits on it.

## Current answer
Unknown. See [[parser-rewrite]].
"""


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copy(VAULT / "schema.yaml", self.root / "schema.yaml")
        self.write("projects/parser-rewrite.md", VALID_PROJECT)
        self.write("questions/why-slow.md", VALID_QUESTION)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def errors(self):
        return check(self.root)

    def assertOneError(self, fragment):
        errors = self.errors()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(fragment, errors[0])

    def test_valid_vault_has_no_errors(self):
        self.assertEqual(self.errors(), [])

    def test_missing_frontmatter_is_reported(self):
        self.write("concepts/bare.md", "# no frontmatter\n")
        self.assertOneError("concepts/bare.md: missing frontmatter")

    def test_missing_required_field_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("focus: now\n", ""))
        self.assertOneError("missing field 'focus'")

    def test_missing_common_field_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("created: 2026-10-01\n", ""))
        self.assertOneError("missing field 'created'")

    def test_unknown_field_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("focus: now\n", "focus: now\npriority: high\n"))
        self.assertOneError("unknown field 'priority'")

    def test_invalid_enum_value_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("status: active", "status: started"))
        self.assertOneError("status 'started' not in")

    def test_type_in_wrong_directory_is_reported(self):
        self.write("concepts/why-slow-copy.md", VALID_QUESTION)
        self.assertOneError("type 'question' belongs in questions/")

    def test_unknown_type_is_reported(self):
        self.write("concepts/x.md", VALID_QUESTION.replace("type: question", "type: musing"))
        self.assertOneError("unknown type 'musing'")

    def test_missing_section_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("## Ideas\n- try a streaming reader\n", ""))
        self.assertOneError("missing section 'Ideas'")

    def test_conditional_field_is_required(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("status: active", "status: waiting"))
        self.assertOneError("status 'waiting' requires field 'waiting_on'")

    def test_conditional_field_satisfied(self):
        self.write("people/ada.md", "---\ntype: person\ntitle: Ada\ncreated: 2026-10-01\nupdated: 2026-10-01\n---\n")
        self.write(
            "projects/parser-rewrite.md",
            VALID_PROJECT.replace("status: active", "status: waiting\nwaiting_on: ada"),
        )
        self.assertEqual(self.errors(), [])

    def test_waiting_on_org_satisfied(self):
        self.write("orgs/lab.md", "---\ntype: org\ntitle: The Lab\ncreated: 2026-10-01\nupdated: 2026-10-01\n---\n")
        self.write(
            "projects/parser-rewrite.md",
            VALID_PROJECT.replace("status: active", "status: waiting\nwaiting_on: lab"),
        )
        self.assertEqual(self.errors(), [])

    def test_person_org_must_be_a_note(self):
        self.write("people/ada.md", "---\ntype: person\ntitle: Ada\ncreated: 2026-10-01\nupdated: 2026-10-01\norg: The Lab\n---\n")
        self.assertOneError("org: no note 'The Lab'")

    def test_waiting_task_resolves(self):
        self.write("orgs/lab.md", "---\ntype: org\ntitle: The Lab\ncreated: 2026-10-01\nupdated: 2026-10-01\n---\n")
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("due:2026-10-09", "waiting:lab"))
        self.assertEqual(self.errors(), [])

    def test_waiting_task_with_unknown_target_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("due:2026-10-09", "waiting:labb"))
        self.assertOneError("waiting: no note 'labb'")

    def test_next_takes_any_number_of_open_tasks(self):
        tasks = "".join(f"- [ ] task {i}\n" for i in range(12))
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("- [ ] send the weekly report every:friday\n", tasks))
        self.assertEqual(self.errors(), [])

    def test_broken_body_link_is_reported(self):
        self.write("questions/why-slow.md", VALID_QUESTION.replace("[[parser-rewrite]]", "[[parser-rewrit]]"))
        self.assertOneError("broken link [[parser-rewrit]]")

    def test_link_with_alias_and_heading_resolves(self):
        self.write("questions/why-slow.md", VALID_QUESTION.replace("[[parser-rewrite]]", "[[parser-rewrite#State|the project]]"))
        self.assertEqual(self.errors(), [])

    def test_broken_frontmatter_link_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("[why-slow]", "[why-slwo]"))
        self.assertOneError("questions: no note 'why-slwo'")

    def test_links_in_untyped_notes_are_checked(self):
        self.write("daily/2026-10-05.md", "# 2026-10-05\n\nWorked on [[nowhere]].\n")
        self.assertOneError("daily/2026-10-05.md: broken link [[nowhere]]")

    def test_daily_notes_resolve_as_link_targets(self):
        self.write("daily/2026-10-05.md", "# 2026-10-05\n")
        self.write("questions/why-slow.md", VALID_QUESTION.replace("[[parser-rewrite]]", "[[2026-10-05]]"))
        self.assertEqual(self.errors(), [])

    def test_duplicate_slug_is_reported(self):
        self.write("concepts/parser-rewrite.md", "---\ntype: concept\ntitle: Parser rewrite\ncreated: 2026-10-01\nupdated: 2026-10-01\n---\n")
        self.assertOneError("duplicate slug 'parser-rewrite'")

    def test_invalid_due_date_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("due:2026-10-09", "due:2026-13-09"))
        self.assertOneError("invalid due date '2026-13-09'")

    def test_invalid_recurrence_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("every:friday", "every:fortnight"))
        self.assertOneError("invalid recurrence 'fortnight'")

    def test_invalid_frontmatter_date_is_reported(self):
        self.write("projects/parser-rewrite.md", VALID_PROJECT.replace("updated: 2026-10-05", "updated: last week"))
        self.assertOneError("updated: 'last week' is not a YYYY-MM-DD date")


if __name__ == "__main__":
    unittest.main()
