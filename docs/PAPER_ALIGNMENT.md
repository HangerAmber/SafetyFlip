# Alignment with the paper

This release is a reference implementation and an anonymous project website for **SafetyFlip: Learning LLM Safety Boundaries from Bidirectional Counterfactual Instructions**. It does not certify reproduction of the paper's experimental results. Page numbers below refer to the 27-page review manuscript.

## Method contracts

| Component | Paper | Required behavior |
|---|---|---|
| Counterfactual pair | §3.1, Eq. 1, pp. 3–4 | Preserve the non-safety frame while changing the safety-critical factor and instruction label. Both Safe→Unsafe and Unsafe→Safe directions matter. |
| Response policy | Eq. 2, p. 4 | Both responses must be safe: comply with a safe instruction; refuse or offer a safe pivot for an unsafe instruction. An unsafe instruction is never an unsafe-response training target. |
| Annotation | §3.2.2, Eq. 3, p. 5 | Use `r_frame`, `r_crit`, `r_policy`. The policy is `Comply`, `Refuse`, or `Pivot`. These are compact, non-operational annotations, not free-form chain-of-thought. |
| Pipeline | §3.2.1, pp. 4–5 | Analyze the seed, reverse its critical factor, analyze the counterfactual, answer both sides, then validate. All paper roles use Qwen2.5-72B-Instruct (A.3, p. 15). |
| Validation | A.3, p. 15 | Require a frame-preservation score **strictly greater than 0.8**, successful safety inversion, and annotation/response consistency. Eq. 2 additionally requires safe responses on both sides. Missing or contradictory validation evidence must not pass. |
| Annotation supervision | Eq. 3–4, p. 5 | Supervise `p(c,y|x) = p(c|x) p(y|x,c)`. A response-only target implements a different training variant. |
| KL regularization | Eq. 4, p. 5 | Use forward `KL(p_policy || p_base)` with a frozen reference. |
| Safety direction | Eq. 5, p. 6 | `1 − cos(g(x) × (h(x) − h(x_flip)), v_safety)`, where `g(Safe)=+1` and `g(Unsafe)=−1`. The learned displacement always points toward the safe pole. |
| Response consistency | Eq. 6, p. 6 | Use the squared norm of the difference **after projection orthogonal to** `v_safety`. Do not make the full compliance and refusal representations equal. |
| Information separation | Eq. 7, p. 6; Eq. 12–14, p. 21 | Predict shortcut labels and semantic-frame labels with two critics. Critics learn both targets; the encoder reverses only the shortcut gradient and preserves semantic evidence. Shortcut labels are not the safe/unsafe labels. |
| Combined BCFT | Eq. 8, p. 6 | Add KL-SFT and the three SCR terms with separate nonnegative coefficients. |
| Deployment | §3.2.2, p. 5 | The paper claims final-response-only inference, without agents, critics, explicit annotation generation, or inference-time intervention. The exact verified export/decoding recipe remains forthcoming. |

For a normalized direction `v`, the projection is `P_perp(z) = z − (z·v)v`. For an unnormalized direction, divide the projected coefficient by `v·v`. The consistency penalty is `||P_perp(h(y)) − P_perp(h(y_flip))||²`.

Appendix C's encoder surrogate is `−CE(shortcut) + lambda_info × CE(semantic)`. The critics minimize `CE(shortcut) + CE(semantic)`. Reversing the shortcut critic's own optimization would not implement this contract. This surrogate is not an exact numerical mutual-information measurement.

## Reported configuration

| Setting | Paper value | Source |
|---|---|---|
| Main backbone | Qwen2.5-7B; exact checkpoint revision not supplied | §4.1, p. 7; A.2, p. 14 |
| Teacher for all four roles | Qwen2.5-72B-Instruct | A.3, p. 15 |
| LoRA targets | Query and value projections | A.2, p. 14 |
| LoRA rank / alpha / dropout | 8 / 16 / 0.1 | A.2, p. 14 |
| Optimizer / peak LR | AdamW / `2e-5` | A.2, p. 14 |
| LR schedule / warmup | Cosine / 3% | A.2, p. 14 |
| Global batch / epochs | 64 / 3 | A.2, p. 14 |
| SCR λ1 / λ2 / λ3 | 1.0 / 0.5 / 0.1 | Table 8, p. 23 |
| Validation gate | Preservation score > 0.8 | A.3, p. 15 |
| Training hardware | 16 × A100 80 GB, DeepSpeed ZeRO-2 | A.2, p. 14 |
| Data-generation resources | Approximately 48 GPU-hours on separate A100 nodes | A.2, p. 14 |

The paper does not report KL `beta`, `lambda_info`, exact critic architecture or label ontology, training pooling, maximum sequence length, seed IDs, or complete software versions. Values chosen for examples must be identified as example settings, not paper defaults. Appendix C.2's normalized last-token pooling describes the embedding visualization; it does not conclusively specify training pooling.

## Interpreting the reported results

Table 2 (p. 8) reports Qwen2.5-7B ASR **58.4%→6.5%**, XSTest OR **1.2%→2.1%**, and MT-Bench **7.61→7.85**. SafetyFlip keeps OR low; it does not lower OR relative to this base model. Table 3 (p. 9) gives Safe-RLHF lower ASR (4.2%) but higher OR (14.5%) and lower MT-Bench (7.45) than SafetyFlip. These results describe a trade-off, not superiority on every metric.

SafetyFlip-Test contains **500 pairs** and is an internal diagnostic (A.1, p. 14). SRR and BMR from this set must be distinguished from public OOD HarmBench, XSTest, and MT-Bench results. The external BeaverTails subset is a separate check. SRR is conditional on safe-redirection applicability and must not be compared directly across the two distributions (A.11, p. 20).

Table 2 reports three-seed SafetyFlip values of ASR `6.51 ± 0.12`, OR `2.10 ± 0.20`, and MT-Bench `7.85 ± 0.03`; it does not define whether ± means a standard deviation, standard error, or interval. Website examples and plots are either attributed paper values or explicitly illustrative content.
