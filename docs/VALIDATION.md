# Validation of this reference release

Verified locally on 2026-09-17 with Python 3.10 and PyTorch 2.5.1+cpu on Windows. The tensor dependency set is pinned in `requirements-smoke.txt`; `pip check` reported no broken requirements. This report concerns software checks, not the manuscript's experiments.

| Check | Observed outcome |
|---|---|
| `python -m unittest discover -s tests -v` with the tensor runtime installed | 30 tests passed; none skipped |
| Strict pair validation | Two illustrative pairs accepted using their explicit synthetic judgments; both construction directions present |
| Offline four-role replay | Original analysis, reversal, independent flipped analysis, both answers, and final validation exercised |
| Tiny CPU optimizer exercise | Two steps passed; model, learnable direction, shortcut critic and semantic critic parameters all updated |
| Frozen reference | No reference gradients during the optimizer exercise |
| Joint annotation–response target | 2,254 supervised toy byte-token targets; prompt and padding excluded |
| Evaluation examples | Supplied synthetic judgments aggregated separately by benchmark, with provenance, support and input hash |
| JavaScript syntax | `node --check site/app.js` passed |
| Browser interactions | Three examples in both directions, all five pipeline stages, and both tables with all five metrics passed |
| Table fidelity | All 45 values in the two interactive result tables matched the manuscript audit |
| Responsive layout | No whole-page horizontal overflow at 1440, 1024, 768, 620, 390 or 320 pixel widths |
| Static/offline page | HTTP preview and direct file opening passed; no JavaScript/console errors or external resource requests observed |
| Anonymous export checks | Text screening for common secrets, email addresses, user paths and supplied identity markers passed; local HTML links resolved |
| Bundled paper | Original anonymous manuscript copied unchanged; Author/Title metadata empty, no XMP metadata or attached files; embedded URLs reviewed |

The mathematical tests include a direct asymmetric forward-KL calculation, reference detachment, causal target masking, pair-orientation invariance, squared orthogonal consistency, trainable direction, and independently verified encoder versus critic gradient weights. Pipeline tests include the strict `>0.8` threshold, each required gate failure, malformed JSON types, invalid direct dataclass construction, and JSON-native serialization. Evaluation tests cover empty support, duplicate judgments, explicit Boolean labels and an unpaired external subset.

The manuscript PDF SHA-256 is:

```text
025a5b4305893d207b44d3184a4ff32149fc471f50a97d7c355f18f684442309
```

No 7B model, 72B teacher, full training dataset, benchmark judge or GPU cluster was run. Passing these checks does not verify semantic safety of arbitrary text or reproduce the reported ASR, OR, MT-Bench, SRR or BMR values. Host-level anonymity and any future public deployment require a separate review.
