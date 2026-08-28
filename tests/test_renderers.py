import json
import unittest

from grounded_alpha.audit import audit_packet
from grounded_alpha.renderers import render_json, render_markdown, render_sarif
from tests.helpers import sample_packet


class RenderersTest(unittest.TestCase):
    def test_markdown_contains_verdict_and_receipt(self) -> None:
        report = audit_packet(sample_packet())

        output = render_markdown(report)

        self.assertIn("**PASS · 100/100**", output)
        self.assertIn(report.packet_hash, output)
        self.assertIn("Citation Coverage | 100.0%", output)

    def test_json_is_machine_readable(self) -> None:
        output = json.loads(render_json(audit_packet(sample_packet())))

        self.assertTrue(output["passed"])
        self.assertEqual(output["score"], 100)
        self.assertEqual(output["metrics"]["claim_count"], 3)

    def test_sarif_maps_findings_to_claim_lines(self) -> None:
        raw = sample_packet()
        raw["claims"][0]["source_ids"] = []
        source_text = json.dumps(raw, indent=2)
        report = audit_packet(raw)

        output = json.loads(render_sarif(report, "research.json", source_text))
        run = output["runs"][0]
        finding = next(
            result for result in run["results"] if result["ruleId"] == "uncited_claim"
        )

        self.assertEqual(output["version"], "2.1.0")
        self.assertEqual(finding["level"], "error")
        self.assertGreater(
            finding["locations"][0]["physicalLocation"]["region"]["startLine"],
            1,
        )
        self.assertEqual(run["properties"]["packetHash"], report.packet_hash)

    def test_passing_sarif_has_no_results(self) -> None:
        raw = sample_packet()
        output = json.loads(
            render_sarif(audit_packet(raw), "research.json", json.dumps(raw))
        )

        self.assertEqual(output["runs"][0]["results"], [])


if __name__ == "__main__":
    unittest.main()
