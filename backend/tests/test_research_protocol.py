import unittest

from services.filing_reader import explicit_relationships


class PartnershipExtractionTests(unittest.TestCase):
    def test_unicode_prepositions_abbreviations_and_community_roles(self):
        source = {
            "id": "doc:p1",
            "url": "https://example.com/report.pdf",
            "title": "Report",
            "page": 1,
            "issuer_terms": ["ACME"],
        }
        for name in (
            "Centre for Development of Telematics",
            "Dassault Systèmes",
            "St. Jude Foundation",
        ):
            with self.subTest(name=name):
                nodes = explicit_relationships(
                    f"ACME partnered with {name}, expanding services.", source
                )
                self.assertEqual(nodes[0]["name"], name)
        nodes = explicit_relationships(
            "Our CSR programme partnered with Smile Foundation to support community health.", source
        )
        self.assertEqual(nodes[0]["category"], "Community / CSR partner")
        self.assertFalse(
            explicit_relationships("Our programme works in partnership with NGO partners.", source)
        )

    def test_sourcing_heading_does_not_hide_explicit_issuer_subject(self):
        source = {
            "id": "doc:p1",
            "url": "https://example.com/report.pdf",
            "title": "Report",
            "page": 1,
        }
        nodes = explicit_relationships(
            "Procurement Process As of March 31, our procurement process involves sourcing products from established brands including Alpha and Bravo as well as our private brands.",
            source,
        )
        self.assertEqual([n["name"] for n in nodes], ["Alpha", "Bravo"])

    def test_partner_name_keeps_ampersand_and_drops_trailing_conjunction(self):
        source = {
            "id": "doc:p1",
            "url": "https://example.com/report.pdf",
            "title": "Report",
            "page": 1,
        }
        nodes = explicit_relationships(
            "We expanded our partnership with Marks & Spencer, and announced a partnership with Example and expanded delivery.",
            source,
        )
        self.assertEqual([node["name"] for node in nodes], ["Marks & Spencer", "Example"])

    def test_explicit_issuer_partnership_without_legal_suffix(self):
        source = {
            "id": "doc:p1",
            "url": "https://example.com/report.pdf",
            "title": "Report",
            "page": 1,
            "issuer_terms": ["ACME"],
        }
        nodes = explicit_relationships(
            "ACME announced a strategic partnership with Example Cloud, enabling its customers to use new services.",
            source,
        )
        self.assertEqual(nodes[0]["name"], "Example Cloud")
        self.assertEqual(nodes[0]["direction"], "partners")
        self.assertEqual(nodes[0]["category"], "Disclosed collaboration")

    def test_unanchored_third_party_partnership_not_attached_to_issuer(self):
        source = {
            "id": "doc:p1",
            "url": "https://example.com/report.pdf",
            "title": "Report",
            "page": 1,
            "issuer_terms": ["ACME"],
        }
        self.assertEqual(
            explicit_relationships(
                "Other Business announced a partnership with Example Cloud, expanding its own operations.",
                source,
            ),
            [],
        )
