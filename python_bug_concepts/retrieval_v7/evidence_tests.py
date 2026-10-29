"""Engineering checks of conditional evidence integrity; no target code runs."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from . import concept_evidence as evidence
from .corpus import cards


class ConceptEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(evidence.OVERLAY_PATH.read_text())
        cls.overlay = evidence.load_overlay()
        cls.cards = {card["id"]: card for card in cards()}

    def test_pinned_citations_validate_without_promoting_requirements(self):
        self.assertEqual(len(self.overlay), 8)
        self.assertEqual(len({row["family"] for row in self.overlay.values()}), 7)
        for row in self.overlay.values():
            self.assertEqual(row["evidence_status"], "curated_conditional_template")
            for requirement in row["requirements"]:
                self.assertEqual(requirement["binding_status"], "unknown_requires_target_evidence")
            for citation in row["citations"]:
                self.assertEqual(len(citation["provenance"]["sha256"]), 64)
                self.assertIn("supports", citation)

    def test_forged_or_out_of_span_quotes_are_rejected(self):
        for quote in ("this is a fabricated citation", "ValueError: Exceeds the limit"):
            with self.subTest(quote=quote):
                payload = deepcopy(self.payload)
                payload["records"][0]["citations"][0]["quote"] = quote
                with self.assertRaisesRegex(ValueError, "Quote absent"):
                    evidence.validate_overlay(payload)

    def test_unknown_pattern_and_target_truth_claim_are_rejected(self):
        payload = deepcopy(self.payload)
        payload["records"][0]["citations"][0]["pattern_id"] = "unknown:source"
        with self.assertRaisesRegex(ValueError, "Unknown source pattern"):
            evidence.validate_overlay(payload)
        payload = deepcopy(self.payload)
        payload["records"][0]["requirements"][0]["satisfied"] = True
        with self.assertRaisesRegex(ValueError, "Invalid requirement fields"):
            evidence.validate_overlay(payload)
        payload = deepcopy(self.payload)
        payload["records"][0]["evidence_status"] = "verified_bug"
        with self.assertRaisesRegex(ValueError, "cannot promote"):
            evidence.validate_overlay(payload)

    def test_manifest_and_actual_hash_are_checked(self):
        registry = evidence._source_registry()
        record, inventory = registry["v2python:sets"]
        ref = record["provenance"]
        record["provenance"]["sha256"] = "0" * 64
        with patch.object(evidence, "_source_registry", return_value=registry):
            with self.assertRaisesRegex(ValueError, "manifest mismatch"):
                evidence.validate_overlay(self.payload)
        inventory[ref["path"]] = ("0" * 64, ref["revision"])
        with patch.object(evidence, "_source_registry", return_value=registry):
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                evidence.validate_overlay(self.payload)

    def test_original_and_uncovered_views_do_not_change(self):
        for cid, card in self.cards.items():
            original = evidence.feature_views(card)
            self.assertEqual(set(original), {"contract", "mechanism", "trigger"})
            self.assertTrue(all(isinstance(value, str) and value for value in original.values()))
            if cid not in self.overlay:
                self.assertEqual(original, evidence.feature_views(card, True, overlay=self.overlay))
        with patch.object(evidence, "load_overlay", side_effect=AssertionError("unexpected overlay read")):
            evidence.feature_views(self.cards["py.mutable-default"])

    def test_negative_evidence_is_separate_from_positive_dense_views(self):
        overlay = deepcopy(self.overlay)
        row = overlay["py.mutable-default"]
        row["exclusions"] = ["EXCLUSION_PRIVATE_CHANNEL"]
        row["benign_contrast"] = "BENIGN_PRIVATE_CHANNEL"
        row["citations"][0]["quote"] = "CITATION_PRIVATE_CHANNEL"
        row["requirements"][0]["required_evidence"] = "OBLIGATION_PRIVATE_CHANNEL"
        combined = " ".join(evidence.feature_views(self.cards["py.mutable-default"], True, overlay=overlay).values())
        for marker in ("EXCLUSION", "BENIGN", "CITATION", "OBLIGATION"):
            self.assertNotIn(marker + "_PRIVATE_CHANNEL", combined)

    def test_family_grouping_and_no_input_mutation(self):
        original_card = deepcopy(self.cards["py.set-loses-multiplicity"])
        original_overlay = deepcopy(self.overlay)
        self.assertEqual(
            evidence.family_for(original_card, overlay=self.overlay),
            evidence.family_for("py.presence-frequency-confusion", overlay=self.overlay),
        )
        self.assertEqual(evidence.family_for("py.set-order-loss", overlay=self.overlay), "py.set-order-loss")
        evidence.feature_views(original_card, True, overlay=self.overlay)
        self.assertEqual(original_card, self.cards["py.set-loses-multiplicity"])
        self.assertEqual(self.overlay, original_overlay)

    def test_duplicate_records_and_missing_roles_are_rejected(self):
        payload = deepcopy(self.payload)
        payload["records"].append(deepcopy(payload["records"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate concept"):
            evidence.validate_overlay(payload)
        payload = deepcopy(self.payload)
        payload["records"][0]["requirements"] = payload["records"][0]["requirements"][:1]
        with self.assertRaisesRegex(ValueError, "all needed"):
            evidence.validate_overlay(payload)


if __name__ == "__main__":
    unittest.main()
