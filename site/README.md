# SafetyFlip research site

A static, anonymous research website. Open `index.html` directly in a browser, or serve this directory:

```sh
python scripts/serve.py
```

Run the command from the repository root, then visit `http://127.0.0.1:8765`.
There is no build step, dependency installation, external font, analytics service, API key, or model server. All demo data is embedded in `app.js`. The page works offline when the bundled paper is present.

## Interactive demos

- **Boundary lab:** three original, non-operational illustrative pairs. Select an example and reverse the seed/counterfactual direction. Both sides always have safe illustrative responses. These are not released training records or live generations.
- **Pipeline walkthrough:** five selectable stages, representing four paper agent roles with Analysis invoked twice. The strict validation gate is displayed as a requirement, never as fabricated scores.
- **Results explorer:** switch between exact Table 3 (p. 9) and Table 5 (p. 10) values, and five metrics. The bar chart uses zero-based axes; an accessible table includes all values. Metrics from public evaluation and the internal diagnostic are distinguished. These are paper-reported results, not reproduced experiments.

## Files and publication

- `index.html`, `styles.css`, `app.js`: page, responsive styles, local interactions.
- `assets/favicon.svg`: locally authored vector icon.
- `assets/paper.pdf`: anonymized paper, supplied by the release packaging workflow.

The only external project link is `https://anonymous.4open.science/r/SafetyFlip/`. Use hosting that does not expose an author account, deployment owner, or identifying metadata. This directory can be served as-is; no personal GitHub URL is needed. The repository URL is the canonical project link, not proof that a local draft has been uploaded.

The release section intentionally distinguishes available reference code and fixtures from forthcoming datasets, model weights, exact training settings, and full benchmark protocols. Keep those statuses synchronized with the actual release. Do not replace pending artifacts with dead download buttons or imply that the demonstrations reproduce the reported experiments.

## Manual checks

Open the page at desktop and mobile widths. Select all three pairs, reverse both directions, visit all five pipeline stages, and select all five metrics for both tables. Use the keyboard to activate controls and follow the local paper links. Respect reduced-motion preferences. No network requests should occur except navigation to the anonymous repository link.
