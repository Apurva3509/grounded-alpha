import tempfile
import unittest
from pathlib import Path

from grounded_alpha.policy import load_policy


class LoadPolicyTest(unittest.TestCase):
    def test_loads_policy_table(self) -> None:
        path = self._write("[policy]\nfail_below = 90\nmax_source_age_days = 30\n")

        policy = load_policy(path)

        self.assertEqual(policy.fail_below, 90)
        self.assertEqual(policy.max_source_age_days, 30)

    def test_rejects_unknown_settings(self) -> None:
        path = self._write("[policy]\nmagic = true\n")

        with self.assertRaisesRegex(ValueError, "unknown policy settings"):
            load_policy(path)

    def test_rejects_invalid_thresholds(self) -> None:
        path = self._write("[policy]\nfail_below = 101\n")

        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            load_policy(path)

    def test_rejects_non_numeric_settings(self) -> None:
        path = self._write('[policy]\nfail_below = "high"\n')

        with self.assertRaisesRegex(ValueError, "must be numeric"):
            load_policy(path)

    def _write(self, content: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "policy.toml"
        path.write_text(content, encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
