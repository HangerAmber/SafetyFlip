"""Strict, versioned data contracts for compact boundary annotations.

This is a documented reference serialization of c=(r_frame,r_crit,r_policy),
not the unavailable original training serialization. Labels describe requests;
responses on BOTH sides must be safe. Schema checks cannot judge text safety.
Semantic/safety judgments must come from a disclosed validator or human audit.
"""

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any


class SchemaError(ValueError):
    """Malformed data, rather than a failed semantic validation gate."""


def _object(value: Any, fields: set[str], path: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise SchemaError(f"{path}: expected exactly {sorted(fields)}")
    return value


def _text(value: Any, path: str, limit: int = 10000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise SchemaError(f"{path}: expected nonempty string of at most {limit} characters")
    return value


def _texts(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise SchemaError(f"{path}: expected a string array")
    return tuple(_text(item, path, 300) for item in value)


def _choice(value: Any, choices: tuple[str, ...], path: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise SchemaError(f"{path}: expected one of {choices}")
    return value


def _bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise SchemaError(f"{path}: expected a JSON boolean")
    return value


@dataclass(frozen=True)
class Frame:
    domain: str
    entities: tuple[str, ...]
    task_form: str
    style: str
    constraints: tuple[str, ...]
    benign_utility: str

    @classmethod
    def from_dict(cls, obj: dict) -> "Frame":
        _object(obj, set(cls.__annotations__), "r_frame")
        return cls(_text(obj["domain"], "domain", 200),
                   _texts(obj["entities"], "entities"),
                   _text(obj["task_form"], "task_form", 300),
                   _text(obj["style"], "style", 200),
                   _texts(obj["constraints"], "constraints"),
                   _text(obj["benign_utility"], "benign_utility", 600))


@dataclass(frozen=True)
class Annotation:
    r_frame: Frame
    r_crit: str
    r_policy: str

    @classmethod
    def from_dict(cls, obj: dict) -> "Annotation":
        _object(obj, set(cls.__annotations__), "annotation")
        return cls(Frame.from_dict(obj["r_frame"]),
                   _text(obj["r_crit"], "r_crit", 600),
                   _choice(obj["r_policy"], ("Comply", "Refuse", "Pivot"), "r_policy"))


@dataclass(frozen=True)
class Analysis:
    label: str
    annotation: Annotation

    @classmethod
    def from_dict(cls, obj: dict) -> "Analysis":
        _object(obj, set(cls.__annotations__), "analysis")
        return cls(_choice(obj["label"], ("Safe", "Unsafe"), "label"),
                   Annotation.from_dict(obj["annotation"]))


@dataclass(frozen=True)
class Response:
    text: str
    behavior: str

    @classmethod
    def from_dict(cls, obj: dict) -> "Response":
        _object(obj, set(cls.__annotations__), "response")
        return cls(_text(obj["text"], "response.text"),
                   _choice(obj["behavior"], ("Comply", "Refuse", "Pivot"), "response.behavior"))


@dataclass(frozen=True)
class Side:
    instruction: str
    analysis: Analysis
    response: Response

    @classmethod
    def from_dict(cls, obj: dict) -> "Side":
        _object(obj, set(cls.__annotations__), "side")
        return cls(_text(obj["instruction"], "instruction"),
                   Analysis.from_dict(obj["analysis"]), Response.from_dict(obj["response"]))


@dataclass(frozen=True)
class Validation:
    preservation_score: float
    label_inversion: bool
    annotation_response_consistent: bool
    original_response_safe: bool
    flipped_response_safe: bool
    source: str
    notes: str

    @classmethod
    def from_dict(cls, obj: dict) -> "Validation":
        _object(obj, set(cls.__annotations__), "validation")
        score = obj["preservation_score"]
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            raise SchemaError("preservation_score: expected finite number in [0,1]")
        return cls(float(score), *(_bool(obj[key], key) for key in (
            "label_inversion", "annotation_response_consistent", "original_response_safe",
            "flipped_response_safe")),
            _choice(obj["source"], ("synthetic_fixture", "human_audit", "teacher_validator"), "source"),
            _text(obj["notes"], "validation.notes", 2000))


@dataclass(frozen=True)
class Candidate:
    pair_id: str
    original: Side
    flipped: Side


@dataclass(frozen=True)
class Pair:
    schema_version: str
    pair_id: str
    provenance: str
    semantic_frame_id: str
    original: Side
    flipped: Side
    validation: Validation

    @classmethod
    def from_dict(cls, obj: dict) -> "Pair":
        _object(obj, set(cls.__annotations__), "pair")
        if obj["schema_version"] != "1.0":
            raise SchemaError("schema_version must be 1.0")
        return cls("1.0", _text(obj["pair_id"], "pair_id", 200),
                   _choice(obj["provenance"], ("illustrative_fixture", "generated", "human_curated"), "provenance"),
                   _text(obj["semantic_frame_id"], "semantic_frame_id", 200),
                   Side.from_dict(obj["original"]), Side.from_dict(obj["flipped"]),
                   Validation.from_dict(obj["validation"]))

    @property
    def direction(self) -> str:
        return f"{self.original.analysis.label}->{self.flipped.analysis.label}"

    def to_dict(self) -> dict:
        # Return JSON-native arrays too, so from_dict(to_dict()) is a valid
        # strict-schema roundtrip without exposing immutable internal tuples.
        return json.loads(json.dumps(asdict(self)))


def gate_reasons(pair: Pair | Candidate, validation: Validation | None = None,
                 threshold: float = 0.8) -> list[str]:
    """Strict >0.8 is A.3's default. Reports are judgments, not proof of safety."""
    if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 <= threshold < 1:
        raise ValueError("threshold must be a finite number in [0,1)")
    report = validation if validation is not None else getattr(pair, "validation", None)
    if not isinstance(report, Validation):
        raise SchemaError("a validator report is required")
    if not isinstance(pair, (Pair, Candidate)):
        raise SchemaError("a Pair or Candidate is required")
    if isinstance(pair, Pair):
        pair = Pair.from_dict(json.loads(json.dumps(pair.to_dict())))
    # Dataclass type hints are not runtime validation. Check direct API inputs as
    # strictly as loaded JSON, so NaN/inf or truthy strings cannot bypass a gate.
    report = Validation.from_dict(json.loads(json.dumps(asdict(report))))
    original = Side.from_dict(json.loads(json.dumps(asdict(pair.original))))
    flipped = Side.from_dict(json.loads(json.dumps(asdict(pair.flipped))))
    reasons = []
    if not report.preservation_score > threshold:
        reasons.append(f"frame preservation must be > {threshold}")
    if original.analysis.label == flipped.analysis.label or not report.label_inversion:
        reasons.append("instruction labels did not invert")
    for name, side in (("original", original), ("flipped", flipped)):
        policy = side.analysis.annotation.r_policy
        if side.analysis.label == "Safe" and policy != "Comply":
            reasons.append(f"{name}: safe instruction requires Comply")
        if side.analysis.label == "Unsafe" and policy not in ("Refuse", "Pivot"):
            reasons.append(f"{name}: unsafe instruction requires Refuse or Pivot")
        if side.response.behavior != policy:
            reasons.append(f"{name}: response behavior differs from annotation")
    if not report.annotation_response_consistent:
        reasons.append("validator rejected annotation-response consistency")
    if not report.original_response_safe or not report.flipped_response_safe:
        reasons.append("both responses must be judged safe")
    if isinstance(pair, Pair) and pair.provenance != "illustrative_fixture" and report.source == "synthetic_fixture":
        reasons.append("synthetic judgments are only valid for illustrative fixtures")
    return reasons


def load_pairs(path: str | Path, require_accepted: bool = True) -> list[Pair]:
    """Read JSONL; fail with a line number, preserve pair membership, reject duplicate IDs."""
    pairs, seen = [], set()
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                pair = Pair.from_dict(json.loads(line))
                if pair.pair_id in seen:
                    raise SchemaError(f"duplicate pair_id: {pair.pair_id}")
                reasons = gate_reasons(pair)
                if require_accepted and reasons:
                    raise SchemaError("gate rejected: " + "; ".join(reasons))
                seen.add(pair.pair_id)
                pairs.append(pair)
            except (ValueError, TypeError, KeyError) as exc:
                raise SchemaError(f"line {line_number}: {exc}") from exc
    if not pairs:
        raise SchemaError("dataset contains no pairs")
    return pairs


def serialize_target(side: Side) -> str:
    """Reference c+y target. Exact original template/annotation-free export is forthcoming.

    Tokenize prompt separately, then this target; supervise every annotation and
    response token and mask prompt/padding. No hidden free-form reasoning is stored.
    """
    return json.dumps({"annotation": asdict(side.analysis.annotation), "response": side.response.text},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))
