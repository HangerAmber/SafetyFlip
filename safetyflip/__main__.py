"""Local-only command line. Optional torch is imported only for smoke-losses."""

import argparse
import json
from pathlib import Path
import sys

from .pipeline import FixtureReplayProvider, SafetyFlipPipeline
from .schema import SchemaError, load_pairs


def _emit(result: dict, output: str | None) -> None:
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if output:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content + "\n", encoding="utf-8")
    print(content)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] == "evaluate":
        from .evaluation import main as evaluate_main
        return evaluate_main(arguments[1:]) or 0
    parser = argparse.ArgumentParser(description="SafetyFlip anonymous reference tools (offline by default)")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="check JSONL schema and recorded validation gate")
    validate.add_argument("data")
    demo = commands.add_parser("demo", help="replay authored fixtures, without model inference")
    demo.add_argument("--data", default="data/examples.jsonl")
    demo.add_argument("--output")
    smoke = commands.add_parser("smoke-losses", help="run a tiny torch CPU optimizer smoke")
    smoke.add_argument("--config", default="configs/smoke.json")
    smoke.add_argument("--output")
    commands.add_parser("evaluate", help="aggregate supplied evaluation judgments; see evaluate --help")
    options = parser.parse_args(arguments)
    try:
        if options.command == "validate":
            pairs = load_pairs(options.data)
            _emit({"status": "passed", "pairs": len(pairs),
                   "directions": sorted({pair.direction for pair in pairs}),
                   "note": "Schema and recorded judgments checked; text safety and preservation were not independently assessed.",
                   "provenance": sorted({pair.provenance for pair in pairs})}, None)
        elif options.command == "demo":
            pairs = load_pairs(options.data)
            replays = []
            for pair in pairs:
                provider = FixtureReplayProvider(pair)
                result = SafetyFlipPipeline(provider).run(pair.original.instruction, pair.pair_id, pair.semantic_frame_id)
                replays.append({"pair_id": pair.pair_id, "direction": pair.direction,
                                "provider": provider.identity, "trace": result.trace,
                                "gate_accepted_fixture": result.accepted,
                                "rejection_reasons": result.rejection_reasons,
                                "pair": result.pair.to_dict()})
            _emit({"kind": "illustrative authored fixture replay; no model inference",
                   "warning": "Scores and judgments are synthetic test inputs, not measured validation results.",
                   "replays": replays}, options.output)
        elif options.command == "smoke-losses":
            from .smoke import run_smoke
            _emit(run_smoke(options.config), options.output)
        return 0
    except ImportError as exc:
        if exc.name == "torch":
            parser.exit(2, "smoke-losses requires optional torch; install requirements-smoke.txt using the README instructions.\n")
        raise
    except (SchemaError, ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
