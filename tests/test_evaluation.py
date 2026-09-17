import unittest
from safetyflip.evaluation import aggregate


def row(benchmark="safetyflip_test", **overrides):
    value = dict(benchmark=benchmark, example_id="safe-1", pair_id="pair-1",
                 model_id="fixture", protocol_id="reference-v1", dataset_revision="fixture-v1",
                 judge_id="fixture-author", is_fixture=True, instruction_label="Safe", refusal=False)
    value.update(overrides)
    return value


class EvaluationTests(unittest.TestCase):
    def test_denominators_and_zero_eligible(self):
        values = [row(refusal=True), row(example_id="unsafe-1", instruction_label="Unsafe",
                    unsafe_compliance=False, redirection_applicable=False, soft_refusal=False)]
        metrics = aggregate(values)["groups"][0]["metrics"]
        self.assertEqual(metrics["BMR"], {"value": 50.0, "unit": "percent", "numerator": 1, "denominator": 2})
        self.assertIsNone(metrics["SRR"]["value"])
        self.assertEqual(metrics["SRR"]["denominator"], 0)

    def test_no_accidental_dataset_model_judge_pooling(self):
        rows = [row("xstest"), row("xstest", model_id="second", refusal=True),
                row("xstest", judge_id="another", refusal=True)]
        result = aggregate(rows)
        self.assertEqual(len(result["groups"]), 3)

    def test_duplicates_and_missing_pair_rejected(self):
        with self.assertRaises(ValueError):
            aggregate([row("xstest"), row("xstest")])
        with self.assertRaises(ValueError):
            aggregate([row()])

    def test_invalid_judgments_do_not_become_zero(self):
        for r in [row("xstest", refusal="false"), row("mt_bench", score=float("nan")),
                  row("harmbench", unsafe_compliance=False), row("mt_bench", score=True)]:
            with self.assertRaises(ValueError):
                aggregate([r])

    def test_empty_has_no_perfect_scores(self):
        self.assertEqual(aggregate([])["groups"], [])

    def test_fixture_status_is_not_measured(self):
        result = aggregate([row("xstest")])
        self.assertEqual(result["groups"][0]["provenance"], "synthetic_fixture")

    def test_external_subset_does_not_require_counterfactual_pairs(self):
        value = row("beavertails")
        value.pop("pair_id")
        self.assertEqual(aggregate([value])["groups"][0]["metrics"]["BMR"]["denominator"], 1)


if __name__ == "__main__":
    unittest.main()
