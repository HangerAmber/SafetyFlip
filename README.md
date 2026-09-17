<p align="center"><strong>SafetyFlip</strong><br>Learning LLM Safety Boundaries from Bidirectional Counterfactual Instructions</p>
<p align="center">Anonymous authors · ICLR 2027 submission under review</p>

<p align="center"><a href="site/assets/paper.pdf">Paper</a> · <a href="site/index.html">Interactive project page</a> · <a href="https://anonymous.4open.science/r/SafetyFlip/">Anonymous repository</a> · <a href="docs/REPRODUCIBILITY.md">Reproducibility status</a></p>

SafetyFlip constructs matched **Safe ↔ Unsafe instruction pairs** that preserve the non-safety semantic frame while changing the safety-critical factor. Both sides receive safe, policy-consistent responses: helpful compliance for safe requests, refusal or a relevant safe pivot for unsafe requests. Boundary-Constrained Fine-Tuning (BCFT) combines joint structured annotation–response supervision, a base-policy KL penalty, and Safety Contrastive Regularization (SCR).

**Release status:** this repository provides executable **reference components**, transparent offline fixtures and an interactive explanatory website. The full experimental datasets, trained checkpoints, exact teacher prompts, end-to-end distributed training/deployment recipe and benchmark generations/judges are **forthcoming**. The included CPU smoke run does not reproduce the reported model results. See the [paper alignment map](docs/PAPER_ALIGNMENT.md) for equation-level scope and implementation choices.

## Start here

Python **3.10+**. The schema, fixture pipeline, evaluation aggregation and website use the standard library; no model, API key or GPU is needed.

Download the anonymous source archive, extract it and run these commands from its `SafetyFlip` directory:

```bash
python -m safetyflip validate data/examples.jsonl
python -m safetyflip demo --data data/examples.jsonl
python -m safetyflip.evaluation data/evaluation_example.jsonl
python scripts/serve.py
```

Open **http://127.0.0.1:8765** for the website. You can also open `site/index.html` directly. The page includes a boundary-pair explorer, an offline construction walkthrough, and a metric/ablation explorer. Every response example is labeled illustrative; every experimental score is labeled paper-reported. No inference service is connected.

## Check the BCFT objective on CPU

The pinned smoke environment targets **Python 3.10, Windows/Linux x86-64, CPU**. Use a fresh environment. Activation on Linux is `source .venv/bin/activate`; on Windows PowerShell it is `.venv\Scripts\Activate.ps1`. Other platforms can use the standard-library components, but their tensor environment has not been verified here.

```bash
python -m venv .venv
# Activate the environment, then:
python -m pip install --upgrade pip
python -m pip install -r requirements-smoke.txt
python -m unittest discover -s tests -v
python -m safetyflip smoke-losses --config configs/smoke.json
```

This tiny, deterministic optimizer exercise checks gradient flow through the objective, critics and learned direction. It is **not an LLM training run**. The smoke configuration's vocabulary, representations, seed, β and λ_info are explicit toy choices. They are not recovered experimental hyperparameters.

The reference loss implementation includes:

- masked joint annotation–response cross-entropy and **forward** `KL(policy || reference)`;
- signed counterfactual displacement with `Safe=+1`, `Unsafe=-1` (Eq. 5);
- squared response consistency **orthogonal** to the learned safety direction (Eq. 6);
- shortcut-adversarial and semantic-cooperative encoder gradients, with predictive critic updates (Appendix C, Eqs. 13–14).

`configs/paper.json` records reported settings separately from unresolved values. Unreported settings remain `null`. It is a provenance/configuration record, **not a complete launch recipe**. No command in this release claims to train the published Qwen model.

## What the paper reports

The following are **transcribed single-run values from Table 3, p. 9**, not results obtained by this repository's tests. All rows in this table use the Qwen2.5-7B backbone.

| Method | HarmBench ASR ↓ | XSTest OR ↓ | MT-Bench ↑ | Internal SRR ↑ | Internal BMR ↓ |
|---|---:|---:|---:|---:|---:|
| Base | 58.4% | 1.2% | 7.61 | 5.8% | 22.5% |
| Sample-matched SFT | 12.4% | 5.8% | 7.72 | 6.9% | 13.9% |
| Safe-RLHF | 4.2% | 14.5% | 7.45 | 6.0% | 11.6% |
| SafetyFlip | 6.5% | 2.1% | 7.85 | 8.1% | 7.8% |

Relative to the base, SafetyFlip reduces ASR by **51.9 percentage points** and increases MT-Bench by **0.24**. OR **increases from 1.2% to 2.1%** while remaining low. Safe-RLHF has lower ASR in this comparison. These results describe a trade-off; they do not establish that every metric or every model comparison is best.

HarmBench, XSTest and MT-Bench are public OOD evaluations. SRR/BMR above use the internal **500-pair SafetyFlip-Test** diagnostic. SRR's denominator is prompts where safe redirection applies, so its absolute values must not be compared across datasets with different applicability distributions. See [evaluation contracts](docs/EVALUATION.md).

## Available and forthcoming

| Artifact | Current status |
|---|---|
| Pair schema, strict gate and four-role pipeline contract | Included; replay provider is offline and uses fixtures |
| BCFT/SCR reference mathematics and gradient tests | Included; CPU toy optimization only |
| Explicit-judgment metric aggregation | Included; does not run benchmark judges |
| Three interactive website demos and local paper | Included; explanatory/static data |
| Full 8,000 accepted training pairs and source manifests | Forthcoming |
| 500-pair SafetyFlip-Test and external evaluation subset IDs | Forthcoming |
| Exact teacher prompts, decoding and score-calibration protocol | Forthcoming |
| Qwen fine-tuning checkpoints and verified distributed launch recipe | Forthcoming |
| Exact annotation-free deployment/export recipe | Forthcoming |
| Raw benchmark outputs, judge configurations and seed manifests | Forthcoming |

The manuscript describes annotation supervision during training and final-response-only decoding at deployment, but does not give the complete transition mechanism. This reference release does not silently implement annotation generation and hide its cost. See [reproducibility limitations](docs/REPRODUCIBILITY.md).

## Anonymous release

The website uses only local assets, with no analytics, author profiles, institution identifiers, personal account links or remote font services. The supplied PDF has blank author/title metadata; its embedded external links are scholarly references and the anonymous project link. Its original content is preserved.

```bash
python scripts/check_release.py
python scripts/check_release.py --manifest --zip ../SafetyFlip-anonymous.zip
```

The exporter omits Git history, environments, caches and local run outputs and includes file hashes. The automated checks are heuristic, not a guarantee of anonymity. A private development repository is **not an anonymous public host**: publish only the audited export via the anonymous service. Review [the anonymity guide](docs/ANONYMITY.md) before release.

## Repository map

```text
safetyflip/     strict records, pipeline contracts, losses, CPU smoke, evaluation
configs/        reported paper settings and separate toy settings
data/           clearly labeled illustrative fixtures
tests/          mathematical, parsing, gate and aggregation checks
site/           standalone responsive project page and local paper
docs/           equation alignment, reproduction gaps, migration and anonymity
scripts/        local preview and anonymous export checks
```

The [migration notes](docs/MIGRATION.md) document why the older ARG/SB-CoT interfaces were replaced. This implementation uses the current paper's **structured boundary annotations**, which are compact fields rather than free-form chain-of-thought.

## Citation and licensing

Use the anonymous paper title and author designation in [CITATION.cff](CITATION.cff) during review. The manuscript remains under review; no acceptance is implied. Software and dataset redistribution licenses have not been specified by the authors in the supplied source materials. License selection and data-source permissions remain pending; this release does not invent a grant of rights for unreleased data or third-party assets.
