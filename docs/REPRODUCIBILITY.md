# Reproducibility and release status

This release provides inspectable method components, local examples, documentation, and an anonymous website. **The paper's experiments have not been reproduced by this release.** Mathematical checks and example runs verify software behavior, not the reported benchmark scores.

## What the release makes reviewable

| Item | Current scope |
|---|---|
| Paper alignment | Equations, reported settings, limitations, and migration notes are documented. |
| Paired data | `safetyflip/schema.py` and `data/examples.jsonl` provide a structured pair contract and small illustrative records. They are not the 8,000-pair training release. |
| Construction logic | `safetyflip/pipeline.py` provides sequential role contracts, a separate analysis of the counterfactual, strict validation, and an explicitly labeled fixture replay provider. This is not the original teacher run. |
| BCFT components | `safetyflip/losses.py` provides reference objective components that can be inspected and checked independently. Their presence is not a complete, verified large-model training recipe. |
| CPU optimization example | `safetyflip/smoke.py` exercises real optimizer updates on a tiny token model. Its vocabulary, data and settings are toy choices; it does not train Qwen or measure a benchmark. |
| Evaluation | Aggregation of supplied judgments is distinguishable from generating and judging actual benchmark responses. Synthetic examples are not experimental results. |
| Project website | Paper cases, method explanations, and attributed paper-result visualizations. It is not a hosted SafetyFlip model endpoint. |

Use the commands in the [README](../README.md) for the available local checks. A successful smoke run means only that the exercised code path works with the supplied inputs. It does not mean a teacher, checkpoint, GPU training job, or benchmark judge was run.

`configs/paper.json` records reported values and leaves unreleased experimental choices unspecified. `configs/smoke.json` supplies explicitly illustrative settings for the CPU example. Do not use the latter as a claimed paper training recipe.

## Forthcoming artifacts

These artifacts are not supplied as verified experimental releases:

1. **Data:** the full 8,000 accepted training pairs, original seed sources and licenses, 24,000 candidate records, accepted/rejected provenance, deduplication rules, and train/validation manifests.
2. **Internal and external diagnostics:** the 500-pair SafetyFlip-Test manifest, the exact BeaverTails subset, and reviewed redirection-applicability labels.
3. **Teacher recipe:** exact Qwen2.5-72B-Instruct revision; original prompts, safety taxonomy and scoring rubric; generation settings; retries and candidate-selection policy.
4. **Training:** verified full training/export entry point, model/adapters, checkpoint revisions, reference KL settings, auxiliary-label ontology, critic architecture and optimizer schedule, loss/token reductions, pooling, seeds, precision, and software lockfile from the experiments.
5. **Evaluation:** exact benchmark revisions, attack configurations, classifiers and judge snapshots, generation settings, multi-turn templates, baseline recipes, per-example generations and judgments, and three-seed run manifests.
6. **Deployment and figures:** the verified final-response-only inference recipe and raw category/scaling/embedding data behind the figures.

“Forthcoming” describes material intended for a later release; no release date or currently working download is implied. Unreported experimental choices also require author clarification: this list identifies reproduction requirements, not a guarantee that every missing field or original artifact can be recovered. A full training command must not silently fill these gaps and label its output a reproduction.

## What a documented experimental run needs

Record an immutable model/tokenizer revision, dataset IDs and checksums, pair split IDs, every configuration value, all random seeds, runtime/dependency versions, hardware, commands, checkpoints, and per-example outputs. Keep both sides of a pair in the same split. Check seed/source overlap and near-duplicates before claiming an OOD evaluation.

The paper reports LoRA rank 8, alpha 16, dropout 0.1 on query/value projections, AdamW at `2e-5`, cosine decay, 3% warmup, global batch 64, three epochs, and SCR weights `(1.0, 0.5, 0.1)`. These values alone are insufficient to reproduce the run. In particular, `beta` and `lambda_info` were not reported; choosing values for them creates a documented implementation variant.

The reported 16 × A100 80 GB training configuration and approximately 48 GPU-hours of teacher generation are manuscript facts. They are not a measured local resource estimate or a minimum hardware guarantee.

## Evaluation denominators

- **ASR:** unsafe compliance / evaluated attack prompts under a specified HarmBench protocol.
- **OR:** refused safe requests / evaluated safe XSTest requests.
- **SRR:** successful refusal-plus-relevant-safe-pivot / prompts for which safe redirection is applicable. Applicability must come from an explicit annotation or judge, not be inferred from a response merely containing a refusal phrase.
- **BMR:** combined safe-over-refusal and unsafe-compliance errors. The paper does not specify exact weighting; an aggregator's pooled or balanced convention must be declared separately.
- **MT-Bench:** scores from a specified multi-turn judging protocol, not inferred from output length or a keyword score.

Report numerator, denominator, units, and the source of every judgment. Empty support means unavailable, not 0% success or failure. Do not substitute a keyword classifier for the paper's missing judge protocol. Internal SafetyFlip-Test metrics and external BeaverTails metrics need separate dataset labels; their SRR values are distribution-dependent.

## Claims and demonstrations

Keep paper-reported results separate from new measurements. Table 2's single-run values and three-seed values are different report types. The meaning of its ± statistic remains unspecified. Repeated rendering of a published number is not an independent replication.

Paper examples can be replayed with attribution. Additional frames, annotations, or responses written for the interface must be called illustrative. Simulated geometry is a concept visualization, not a measured embedding. The website must not claim live inference, validation confidence, or latency when no model was run.

Before releasing any run artifact, apply the [anonymous export checklist](ANONYMITY.md). Reproducibility metadata should identify datasets, configurations and model versions without revealing author identities or workstation paths.
