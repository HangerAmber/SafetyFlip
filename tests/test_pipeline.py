"""Fail-closed schema and sequential role tests; fixture judgments are not metrics."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from safetyflip.pipeline import FixtureReplayProvider, SafetyFlipPipeline
from safetyflip.schema import Pair, SchemaError, gate_reasons, load_pairs, serialize_target


EXAMPLES = Path(__file__).resolve().parents[1] / "data" / "examples.jsonl"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.pairs = load_pairs(EXAMPLES)
        self.pair = self.pairs[0]

    def test_both_directions_and_independent_flipped_analysis(self):
        self.assertEqual({pair.direction for pair in self.pairs}, {"Safe->Unsafe", "Unsafe->Safe"})
        for pair in self.pairs:
            provider = FixtureReplayProvider(pair)
            calls = []
            original_analyze = provider.analyze
            def analyze(instruction):
                calls.append(instruction)
                return original_analyze(instruction)
            provider.analyze = analyze
            result = SafetyFlipPipeline(provider).run(pair.original.instruction, pair.pair_id, pair.semantic_frame_id)
            self.assertTrue(result.accepted)
            self.assertEqual(calls, [pair.original.instruction, pair.flipped.instruction])
            self.assertEqual(result.trace, ("analysis:original", "reversal", "analysis:flipped",
                                            "answer:original", "answer:flipped", "validation"))
            self.assertNotEqual(result.pair.original.analysis.annotation.r_crit,
                                result.pair.flipped.analysis.annotation.r_crit)

    def test_gate_is_strict_at_point_eight(self):
        for score, accepted in ((0.8, False), (0.800001, True), (0.799, False)):
            pair = replace(self.pair, validation=replace(self.pair.validation, preservation_score=score))
            self.assertEqual(not gate_reasons(pair), accepted)

    def test_each_validator_failure_rejects(self):
        for field in ("label_inversion", "annotation_response_consistent", "original_response_safe", "flipped_response_safe"):
            with self.subTest(field=field):
                pair = replace(self.pair, validation=replace(self.pair.validation, **{field: False}))
                result = SafetyFlipPipeline(FixtureReplayProvider(pair)).run(pair.original.instruction,
                                                                            pair.pair_id, pair.semantic_frame_id)
                self.assertFalse(result.accepted)
                self.assertTrue(result.rejection_reasons)

    def test_labels_and_behavior_must_agree_even_if_validator_claims_pass(self):
        original = replace(self.pair.original, response=replace(self.pair.original.response, behavior="Refuse"))
        self.assertTrue(gate_reasons(replace(self.pair, original=original)))
        flipped_analysis = replace(self.pair.flipped.analysis, label="Safe")
        flipped = replace(self.pair.flipped, analysis=flipped_analysis)
        self.assertTrue(gate_reasons(replace(self.pair, flipped=flipped)))

    def test_unsafe_compliance_annotation_rejected(self):
        annotation = replace(self.pair.flipped.analysis.annotation, r_policy="Comply")
        analysis = replace(self.pair.flipped.analysis, annotation=annotation)
        flipped = replace(self.pair.flipped, analysis=analysis,
                          response=replace(self.pair.flipped.response, behavior="Comply"))
        self.assertTrue(gate_reasons(replace(self.pair, flipped=flipped)))

    def test_direct_dataclasses_cannot_bypass_types(self):
        for value in (float("inf"), float("nan"), True, "0.9"):
            with self.subTest(value=value), self.assertRaises(SchemaError):
                gate_reasons(replace(self.pair, validation=replace(self.pair.validation, preservation_score=value)))
        with self.assertRaises(SchemaError):
            gate_reasons(replace(self.pair, validation=replace(self.pair.validation, label_inversion="false")))
        with self.assertRaises(SchemaError):
            invalid = replace(self.pair.original, analysis=replace(self.pair.original.analysis, label="unknown"))
            gate_reasons(replace(self.pair, original=invalid))

    def test_unknown_fields_and_string_booleans_rejected(self):
        obj = json.loads(json.dumps(self.pair.to_dict()))
        obj["personal_metadata"] = "unsupported"
        with self.assertRaises(SchemaError):
            Pair.from_dict(obj)
        obj.pop("personal_metadata")
        obj["validation"]["original_response_safe"] = "true"
        with self.assertRaises(SchemaError):
            Pair.from_dict(obj)

    def test_nonfixture_cannot_use_synthetic_validator(self):
        pair = replace(self.pair, provenance="generated")
        self.assertTrue(gate_reasons(pair))
        with self.assertRaises(ValueError):
            FixtureReplayProvider(pair)

    def test_provider_errors_are_visible_and_unknown_text_is_not_scored(self):
        provider = FixtureReplayProvider(self.pair)
        with self.assertRaisesRegex(ValueError, "not an exact replay"):
            SafetyFlipPipeline(provider).run("new input", "new-pair", "new-frame")
        with self.assertRaisesRegex(ValueError, "requires this instruction"):
            provider.answer(self.pair.original.instruction, self.pair.flipped.analysis.annotation)

    def test_duplicate_pair_ids_and_empty_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pairs.jsonl"
            line = json.dumps(self.pair.to_dict()) + "\n"
            path.write_text(line + line, encoding="utf-8")
            with self.assertRaisesRegex(SchemaError, "line 2: duplicate"):
                load_pairs(path)
            path.write_text("\n", encoding="utf-8")
            with self.assertRaisesRegex(SchemaError, "no pairs"):
                load_pairs(path)

    def test_serialized_target_contains_annotation_and_response(self):
        target = json.loads(serialize_target(self.pair.original))
        self.assertEqual(set(target), {"annotation", "response"})
        self.assertEqual(set(target["annotation"]), {"r_frame", "r_crit", "r_policy"})
        self.assertEqual(target["response"], self.pair.original.response.text)

    def test_pair_dictionary_roundtrip_is_json_native(self):
        self.assertEqual(Pair.from_dict(self.pair.to_dict()), self.pair)
        self.assertIsInstance(self.pair.to_dict()["original"]["analysis"]["annotation"]["r_frame"]["entities"], list)


if __name__ == "__main__":
    unittest.main()
