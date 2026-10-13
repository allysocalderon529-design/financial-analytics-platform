import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from kb import ROOT, known_flags, load_acts, load_profile, load_region  # noqa: E402
from pick import select, unknown_flags  # noqa: E402
from validate_kb import validate  # noqa: E402

TODAY = dt.date(2026, 1, 1)


def act(**over):
    base = dict(
        id="x", kind="ФЗ", number="1-ФЗ", date=dt.date(2000, 1, 1), title="t",
        domains=["corporate"], triggers=["llc"], base=False, category="law",
        verified=None, _file="f",
    )
    return {**base, **over}


class RealKbTest(unittest.TestCase):
    def test_real_kb_has_no_errors(self):
        errors, _ = validate(load_acts(), known_flags(), TODAY)
        self.assertEqual(errors, [])

    def test_example_profile_uses_known_flags(self):
        profile = load_profile(ROOT / "projects" / "_example" / "profile.yaml")
        self.assertEqual(unknown_flags(profile, known_flags()), [])

    def test_example_region_resolves(self):
        self.assertEqual(load_region("87")["region_code"], "87")
        self.assertIsNone(load_region("99999"))


class ValidateTest(unittest.TestCase):
    def test_duplicate_id(self):
        errors, _ = validate([act(), act()], {"llc"}, TODAY)
        self.assertTrue(any("дубль" in e for e in errors))

    def test_unknown_flag(self):
        errors, _ = validate([act(triggers=["nope"])], {"llc"}, TODAY)
        self.assertTrue(any("флаги не из анкеты" in e for e in errors))

    def test_unreachable_act(self):
        errors, _ = validate([act(triggers=[], base=False)], {"llc"}, TODAY)
        self.assertTrue(any("никогда не подберётся" in e for e in errors))

    def test_stale_and_unverified_are_warnings(self):
        acts = [act(id="a"), act(id="b", verified=dt.date(2025, 1, 1)), act(id="c", verified=TODAY)]
        errors, warnings = validate(acts, {"llc"}, TODAY)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 2)


class SelectTest(unittest.TestCase):
    def test_flag_match(self):
        picked = select([act()], {"flags": ["llc"], "domains": []})
        self.assertEqual(picked[0]["matched_by"], ["llc"])

    def test_base_needs_domain(self):
        a = act(base=True, triggers=[])
        self.assertEqual(select([a], {"flags": [], "domains": ["it-ai"]}), [])
        self.assertEqual(select([a], {"flags": [], "domains": ["corporate"]})[0]["matched_by"], ["base"])

    def test_no_match(self):
        self.assertEqual(select([act()], {"flags": ["jsc"], "domains": ["it-ai"]}), [])


if __name__ == "__main__":
    unittest.main()
