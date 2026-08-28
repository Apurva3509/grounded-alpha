import json
import unittest

from grounded_alpha.audit import audit_packet
from grounded_alpha.renderers import render_json, render_markdown
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


if __name__ == "__main__":
    unittest.main()
