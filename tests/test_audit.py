import unittest

from grounded_alpha.audit import audit_packet
from tests.helpers import sample_packet


class AuditPacketTest(unittest.TestCase):
    def test_complete_packet_passes(self) -> None:
        report = audit_packet(sample_packet())

        self.assertTrue(report.passed)
        self.assertEqual(report.score, 100)
        self.assertEqual(report.metrics["citation_coverage"], 1.0)

    def test_receipt_is_stable_across_key_order(self) -> None:
        raw = sample_packet()
        reversed_raw = dict(reversed(raw.items()))

        self.assertEqual(
            audit_packet(raw).packet_hash,
            audit_packet(reversed_raw).packet_hash,
        )

    def test_uncited_fact_fails(self) -> None:
        raw = sample_packet()
        raw["claims"][0]["source_ids"] = []

        report = audit_packet(raw)

        self.assertFalse(report.passed)
        self.assertIn("uncited_claim", self._codes(report))

    def test_unknown_source_fails(self) -> None:
        raw = sample_packet()
        raw["claims"][0]["source_ids"] = ["missing-source"]

        report = audit_packet(raw)

        self.assertFalse(report.passed)
        self.assertIn("unknown_source", self._codes(report))

    def test_future_source_fails(self) -> None:
        raw = sample_packet()
        raw["sources"][0]["published_at"] = "2026-08-21"

        report = audit_packet(raw)

        self.assertIn("future_source", self._codes(report))

    def test_look_ahead_access_fails(self) -> None:
        raw = sample_packet()
        raw["sources"][0]["accessed_at"] = "2026-08-21"

        report = audit_packet(raw)

        self.assertIn("look_ahead_access", self._codes(report))

    def test_access_before_publication_fails(self) -> None:
        raw = sample_packet()
        raw["sources"][0]["accessed_at"] = "2026-07-31"

        report = audit_packet(raw)

        self.assertIn("access_before_publication", self._codes(report))

    def test_high_confidence_claim_requires_independent_domains(self) -> None:
        raw = sample_packet()
        raw["sources"][1]["url"] = "https://filings.example/northstar/call"

        report = audit_packet(raw)

        self.assertIn("weak_high_confidence_support", self._codes(report))

    def test_high_confidence_claim_requires_counterevidence(self) -> None:
        raw = sample_packet()
        del raw["claims"][0]["counterevidence"]

        report = audit_packet(raw)

        self.assertIn("missing_counterevidence", self._codes(report))

    def test_conflicting_numeric_claims_fail(self) -> None:
        raw = sample_packet()
        conflict = dict(raw["claims"][0])
        conflict["id"] = "revenue-growth-conflict"
        conflict["value"] = 0.12
        raw["claims"].append(conflict)

        report = audit_packet(raw)

        self.assertFalse(report.passed)
        self.assertIn("numeric_conflict", self._codes(report))

    def test_value_without_metric_metadata_is_incomplete(self) -> None:
        raw = sample_packet()
        raw["claims"][2]["value"] = 3

        report = audit_packet(raw)

        self.assertIn("incomplete_metric", self._codes(report))

    def test_unused_source_is_informational(self) -> None:
        raw = sample_packet()
        raw["sources"].append(
            {
                "id": "unused",
                "title": "Unused source",
                "url": "https://unused.example/report",
                "published_at": "2026-08-01",
                "accessed_at": "2026-08-20",
                "quote": "This excerpt is not connected to any claim.",
                "type": "research",
            }
        )

        report = audit_packet(raw)

        self.assertIn("unused_source", self._codes(report))
        self.assertEqual(report.score, 99)

    @staticmethod
    def _codes(report: object) -> set[str]:
        return {finding.code for finding in report.findings}


if __name__ == "__main__":
    unittest.main()
