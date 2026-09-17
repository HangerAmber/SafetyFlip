# SafetyFlip research site

A static, anonymous research website. Open `site/index.html` directly in a browser, or run this command from the repository root:

```sh
python scripts/serve.py
```

Then visit `http://127.0.0.1:8765`. Serving the page also enables the separate WebVTT caption track on browsers that restrict local-file captions.

There is no build step, dependency installation, external font, analytics service, API key, or model server for viewing the site. All interactions use local data in `app.js`; the bundled paper and video work offline.

## Page sequence

1. **Boundary film:** an original 24-second, silent animation showing ambiguous seed data, matched counterfactual instructions, conceptual BCFT boundary learning, and safe policy behavior. Native controls, four chapter seek buttons, a poster, an MP4 download, and a written description are included. Playback starts only after user action. Coordinates and motion are illustrative, not measured embeddings or training trajectories; no universal safety axis is claimed.
2. **Reversal cases:** three visible overview cards cover network authorization, conflict intent, and location consent. Inspect a pair and reverse the seed/counterfactual direction. Both sides have safe illustrative responses. These are original, non-operational examples, not released training records or live generations.
3. **Code explorer:** select `schema.py`, `pipeline.py`, `losses.py`, `smoke.py`, or `evaluation.py` to inspect their actual reference functionality and limits. A repository map and copyable standard-library quickstart connect the explanation to runnable commands. The PyTorch smoke remains explicitly separate from full model training.
4. **Method walkthrough:** five selectable stages represent four paper roles, with Analysis invoked twice. The strict acceptance gate is shown as a requirement, never fabricated scores.
5. **Results explorer:** exact Table 3 (p. 9) and Table 5 (p. 10) values, across five metrics. Zero-based chart axes and a full accessible table distinguish public evaluation from internal diagnostics. All values are paper-reported, not reproduced experiments.
6. **Release scope:** available reference components and forthcoming data, checkpoints, training recipes, and benchmark protocols.

## Files

- `index.html`, `styles.css`, `app.js`: page, responsive styles, and local interactions.
- `assets/boundary-film.mp4`: silent 1280 × 720, 24-second concept film.
- `assets/boundary-poster.jpg`: static video poster.
- `assets/boundary-film.vtt`: optional English caption/description track.
- `assets/favicon.svg`: locally authored vector icon.
- `assets/paper.pdf`: anonymized paper, supplied by the release workflow.

For animation provenance and optional rebuilding, see `docs/MEDIA.md` and `scripts/render_boundary_film.py` in the repository root. No renderer dependencies are needed to play the committed MP4.

## Publication and anonymity

The only external project link is `https://anonymous.4open.science/r/SafetyFlip/`. Use hosting that does not expose an author account, deployment owner, or identifying metadata. Serve this directory as-is; no personal GitHub URL is needed. The canonical project link is not proof that a local draft has been uploaded.

The release section intentionally distinguishes reference code and fixtures from forthcoming datasets, model weights, exact training settings, and full benchmark protocols. Keep these statuses synchronized with the release. Do not substitute dead download links or imply that the demos reproduce the reported experiments.

## Manual verification

Check desktop and mobile widths, native video playback, all four chapter seeks, the film description, all three cases in both directions, all five code modules, command copying (and manual selection fallback), five pipeline stages, and every metric in both tables. Use the keyboard to activate controls and follow local paper links. The page does not autoplay, and scroll/transition effects respect reduced-motion preferences. No network service is contacted by the site; external navigation occurs only when following the anonymous repository link.
