# Migration from the earlier ARG scaffold

The earlier anonymous source snapshot used an `arg` package and described several components as corresponding directly to the paper. Inspection found mathematical mismatches and incomplete execution paths. This release uses the SafetyFlip terminology and the current manuscript contracts. It is a reference reimplementation, not a claim that the earlier scaffold produced the reported results.

The legacy source references below are module paths within that earlier snapshot. They identify concrete evidence without including author identities, workstation paths, or repository-owner links.

## Mathematical and data corrections

| Legacy source | Observed behavior | Paper requirement / migration |
|---|---|---|
| `arg/losses/safety_direction.py`, `SafetyDirectionLoss.forward` | Defines `g_x=h_x-h_x_flip`, minimizes unsigned `−cos(v,g_x)`, and adds an extra `alpha` separation term. | Eq. 5 (p. 6) uses **signed** `1−cos(g(x)(h_x−h_x_flip),v)`, with `g(x)` a ±1 safety label. Preserve direction labels; remove the unsupported extra term. |
| `arg/losses/representation_cons.py`, `RepresentationConsistencyLoss.forward` | Penalizes `sum((h_y−h_y_flip)^2)` over the full representation. | Eq. 6 (p. 6) applies the squared norm after projecting both response states orthogonal to the learned safety direction. |
| `arg/losses/kl_sft.py`, `KLSFTLoss.forward` | Calls `F.kl_div(log_probs_policy, probs_ref)`. This evaluates `KL(reference || policy)`, despite the comment naming the other direction. | Eq. 4 (p. 5) specifies forward `KL(policy || reference)`. Use the policy probabilities to weight `log_policy−log_reference`; keep the reference frozen. |
| `arg/losses/kl_sft.py`, NLL calculation | Applies cross-entropy to same-position logits and labels and reduces with the attention mask; no causal shift or annotation/response target masking is implemented here. | A causal-LM adapter must align next-token labels and explicitly mask prompts/padding. Eq. 4 supervises the annotation and response, not an unspecified raw sequence. |
| `arg/losses/mi_estimation.py`, `compute_mi_objective` | Minimizes `CE(safety_attribute)−lambda_info×CE(semantic)`. The attribute target is documented as Safe/Unsafe. | Appendix C Eq. 14 (p. 21) uses `−CE(shortcut)+lambda_info×CE(semantic)` for the encoder. Shortcut features and safety labels are distinct. Critics independently learn both targets under Eq. 13. |
| `arg/losses/mi_estimation.py`, `create_semantic_labels` | Uses `hash(text) % num_classes` as a placeholder label. | Supply explicit semantic-frame labels/provenance. Python's ordinary string hash is not a stable semantic ontology and need not assign paired frames the same label. |
| `arg/data/structures.py`, `SBCoT`; `arg/agents/prompts.py` | Uses `r_intent`, `r_harm`, `r_decision` and asks for chain-of-thought reasoning. | §3.2.2 (p. 5) defines compact `r_frame`, `r_crit`, `r_policy` annotations and expressly distinguishes them from free-form chain-of-thought. Re-annotate records; renaming keys alone does not repair their semantics. |
| `arg/agents/validation_agent.py`, `validate` and `_parse_validation` | Defaults to threshold 0.7; rejects scores only when `< threshold`; records inversion/consistency flags without requiring them jointly for `is_valid`. Missing consistency defaults to true. | A.3 (p. 15) requires preservation **>0.8** and successful inversion and consistency. Missing/false gate evidence must reject. Eq. 2 also requires safe responses on both sides. |
| `arg/agents/validation_agent.py`, Boolean parsing | Searches whole lines for `yes`/`no`. A templated `Valid (Yes/No): no` contains `yes` in the field label and can set `is_valid=True`; `Correct Flip (Yes/No): no` has the same problem. | Parse typed Boolean values or an exact value after a delimiter, never substrings of the field label. Invalid/ambiguous values must reject. |
| `arg/agents/analysis_agent.py`, `_parse_analysis` | Defaults unparseable safety labels to `Safe` and replaces missing annotation fields with nonempty placeholder strings. | Reject incomplete analysis instead of treating parser fallback strings as valid frame/critical-factor/policy evidence. |
| `arg/pipeline/reversal_pipeline.py`, `generate_reversal_pair` | Assigns `a_flip` from the requested target and retains only `generate_cot(...)` from counterfactual analysis. | Re-analyze the generated instruction and compare its observed label with the target; retain the counterfactual annotation and evidence. A requested flip is not proof of a successful flip. |

## Execution and reporting limitations

| Legacy source | Concrete limitation | Release consequence |
|---|---|---|
| `arg/training/training_loop.py`, `train_one_epoch` | The loss call, backpropagation, and optimizer stepping are commented out; the returned loss remains zero. `evaluate` also contains no evaluation computation. | Do not retain “training complete” or zero-loss output as evidence of learning. A verified full model trainer remains forthcoming. |
| `scripts/run_training.py` | Always constructs `MockLLMBackbone`; the requested data path is not loaded and `ARGDataset()` is empty. | An accepted argument is not implemented data loading or real model training. The new release distinguishes local software examples from experimental runs. |
| `arg/training/trainer.py`, `save_checkpoint` | Saves safety direction, critics, optimizers and config but not trained backbone/LoRA weights. | These files alone cannot reproduce a tuned language model. Real adapters/weights and export manifests remain forthcoming. |
| `arg/models/backbone.py`, `MockLLMBackbone` | Generates placeholder strings and random logits/hidden states; the mock class is not a trained language model. | Mock or synthetic data must be labeled as such and excluded from benchmark performance claims. |
| `arg/evaluation/eval_hooks.py` | Returns numerical zeros for HarmBench, XSTest and MT-Bench without evaluating benchmark examples. | Unrun metrics are unavailable, not 0.0. Aggregating supplied judgments is separately identified from running a benchmark. |
| `scripts/run_evaluation.py` | Uses the mock model, leaves checkpoint loading unimplemented, and runs `evaluate_all` regardless of the requested benchmark subset. | Do not treat the prior entry point as a functioning benchmark runner or a checkpoint evaluator. |
| `arg/agents/base.py`, `_generate` | Reads `temperature` and `max_tokens` from `kwargs` and then also forwards unchanged `**kwargs`. | Supplying either override can create duplicate keyword arguments. New backend adapters must consume/merge overrides exactly once. |
| `configs/default.yaml` | Sets LR `1e-5`, λ2=1.0, λ3=0.5, threshold=0.7, and fixed warmup steps; no paper LoRA configuration is supplied. | A.2/Table 8 require LR `2e-5`, λ2=0.5, λ3=0.1, preservation >0.8, 3% warmup, and the reported LoRA settings. Unreported values are not paper defaults. |

## Migrating data and results

Preserve pair IDs and both instruction/response sides, then review labels and annotations under the current schema. Supply actual non-safety frame fields, safety-critical factors, explicit policy behaviors, shortcut labels, and semantic labels. Revalidate both responses and all gate conditions. Do not infer missing evidence from a legacy `is_valid=true` flag.

Keep any old mock output, placeholder metric file, random embedding, or incomplete checkpoint separate from new measurements. Recomputing the correct loss on synthetic tensors verifies an equation implementation, not the paper's empirical results. Full data, checkpoints, original prompts, and evaluation recipes remain [forthcoming](REPRODUCIBILITY.md).
