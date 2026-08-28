import unittest

from grounded_alpha.parser import PacketValidationError, parse_packet
from tests.helpers import sample_packet


class ParsePacketTest(unittest.TestCase):
    def test_parses_complete_packet(self) -> None:
        packet = parse_packet(sample_packet())

        self.assertEqual(packet.subject, "Northstar Semiconductor")
        self.assertEqual(len(packet.claims), 3)
        self.assertEqual(packet.claims[0].value, 0.18)

    def test_rejects_duplicate_claim_ids(self) -> None:
        raw = sample_packet()
        raw["claims"][1]["id"] = raw["claims"][0]["id"]

        with self.assertRaisesRegex(PacketValidationError, "duplicate claim ids"):
            parse_packet(raw)

    def test_rejects_out_of_range_confidence(self) -> None:
        raw = sample_packet()
        raw["claims"][0]["confidence"] = 1.2

        with self.assertRaisesRegex(PacketValidationError, "between 0 and 1"):
            parse_packet(raw)

    def test_rejects_non_http_source_url(self) -> None:
        raw = sample_packet()
        raw["sources"][0]["url"] = "file:///tmp/filing.pdf"

        with self.assertRaisesRegex(PacketValidationError, "must use http or https"):
            parse_packet(raw)

    def test_rejects_invalid_dates(self) -> None:
        raw = sample_packet()
        raw["as_of"] = "August 20"

        with self.assertRaisesRegex(PacketValidationError, "must be an ISO date"):
            parse_packet(raw)


if __name__ == "__main__":
    unittest.main()
