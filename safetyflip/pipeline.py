"""Offline construction: Analysis, Reversal, flipped re-analysis, Answer, Validation.

Each role has an explicit provider interface. No network adapter or keyword-based
safety judge is supplied. Qwen2.5-72B-Instruct is the paper teacher for every role;
the default replay provider is a fixture mechanism and never model inference.
"""

from dataclasses import dataclass
import json
from typing import Protocol

from .schema import Analysis, Annotation, Candidate, Frame, Pair, Response, Side, Validation, gate_reasons


class Provider(Protocol):
    identity: str
    provenance: str

    def analyze(self, instruction: str) -> Analysis: ...
    def reverse(self, instruction: str, frame: Frame, target_label: str) -> str: ...
    def answer(self, instruction: str, annotation: Annotation) -> Response: ...
    def validate(self, candidate: Candidate) -> Validation: ...


@dataclass(frozen=True)
class PipelineResult:
    pair: Pair
    accepted: bool
    rejection_reasons: tuple[str, ...]
    trace: tuple[str, ...]


class SafetyFlipPipeline:
    def __init__(self, provider: Provider, threshold: float = 0.8):
        self.provider = provider
        self.threshold = threshold

    def run(self, instruction: str, pair_id: str, semantic_frame_id: str) -> PipelineResult:
        trace = []
        original_analysis = self.provider.analyze(instruction)
        trace.append("analysis:original")
        target = "Unsafe" if original_analysis.label == "Safe" else "Safe"
        flipped_instruction = self.provider.reverse(instruction, original_analysis.annotation.r_frame, target)
        trace.append("reversal")
        # Independently obtain the flipped label and annotation; never assign target as its result.
        flipped_analysis = self.provider.analyze(flipped_instruction)
        trace.append("analysis:flipped")
        original_response = self.provider.answer(instruction, original_analysis.annotation)
        trace.append("answer:original")
        flipped_response = self.provider.answer(flipped_instruction, flipped_analysis.annotation)
        trace.append("answer:flipped")
        candidate = Candidate(pair_id, Side(instruction, original_analysis, original_response),
                              Side(flipped_instruction, flipped_analysis, flipped_response))
        validation = self.provider.validate(candidate)
        trace.append("validation")
        pair = Pair("1.0", pair_id, self.provider.provenance, semantic_frame_id,
                    candidate.original, candidate.flipped, validation)
        # Roundtrip revalidates typed provider output too; malformed output is a visible error.
        pair = Pair.from_dict(json.loads(json.dumps(pair.to_dict())))
        reasons = gate_reasons(pair, threshold=self.threshold)
        return PipelineResult(pair, not reasons, tuple(reasons), tuple(trace))


class FixtureReplayProvider:
    """Replay only exact prewritten fixtures; no scoring, inference, or free-text generation.

    Fixture scores/labels are authored test inputs. They do not measure any
    teacher or model. Unknown inputs fail explicitly, never fall back to a scorer.
    """

    identity = "local-fixture-replay (not a model)"
    provenance = "illustrative_fixture"

    def __init__(self, pair: Pair):
        if pair.provenance != "illustrative_fixture" or pair.validation.source != "synthetic_fixture":
            raise ValueError("replay accepts only explicitly synthetic illustrative fixtures")
        self.pair = pair

    def _side(self, instruction: str) -> Side:
        for side in (self.pair.original, self.pair.flipped):
            if side.instruction == instruction:
                return side
        raise ValueError("instruction is not an exact replay fixture")

    def analyze(self, instruction: str) -> Analysis:
        return self._side(instruction).analysis

    def reverse(self, instruction: str, frame: Frame, target_label: str) -> str:
        seed = self._side(instruction)
        other = self.pair.flipped if seed is self.pair.original else self.pair.original
        if frame != seed.analysis.annotation.r_frame or target_label != other.analysis.label:
            raise ValueError("reversal conditioning differs from replay fixture")
        return other.instruction

    def answer(self, instruction: str, annotation: Annotation) -> Response:
        side = self._side(instruction)
        if annotation != side.analysis.annotation:
            raise ValueError("answer requires this instruction's boundary annotation")
        return side.response

    def validate(self, candidate: Candidate) -> Validation:
        sides = (candidate.original, candidate.flipped)
        if sides not in ((self.pair.original, self.pair.flipped), (self.pair.flipped, self.pair.original)):
            raise ValueError("candidate differs from the replay fixture; cannot judge new text")
        report = self.pair.validation
        if candidate.original == self.pair.flipped:
            from dataclasses import replace
            return replace(report, original_response_safe=report.flipped_response_safe,
                           flipped_response_safe=report.original_response_safe)
        return report
