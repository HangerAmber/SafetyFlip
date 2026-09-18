# Boundary animation

`site/assets/boundary-film.mp4` is an original, silent, 24-second H.264 video at 1280 × 720, 30 fps. It plays locally without a network service. The page provides native playback controls, four chapter buttons, a static poster and a transcript. The included WebVTT file supplies a separate text description track where supported.

| Time | Scene | Intended explanation |
|---|---|---|
| 0–6 s | Seed data | Nearby requests can differ in safety-critical intent; surface features alone may mislead. |
| 6–12 s | Counterfactual construction | Add matched Safe ↔ Unsafe counterparts while preserving the semantic frame. |
| 12–18 s | Boundary learning | BCFT and SCR encourage safety-relevant separation and preservation of shared non-safety utility. |
| 18–24 s | Policy behavior | Safe instructions receive helpful compliance; unsafe instructions receive refusal or a safe pivot. Responses on both sides remain safe. |

All coordinates, motion and example labels are **authored illustrations**. No actual representations, original training trajectories, experimental distributions or measured decision boundaries are displayed. Colors encode the instruction label throughout; the unsafe instruction is never relabeled safe merely because the model gives it a safe response. Ambiguous background points remain after the illustrative transition. The learned direction is a local schematic, not a claim of a universal safety axis.

## Rebuild

The video is generated from `scripts/render_boundary_film.py` with deterministic coordinates and seed 17. The input is the renderer itself, not a research dataset. No personal assets, voice, audio, metadata or model service are used.

```bash
python -m pip install -r requirements-media.txt
python scripts/render_boundary_film.py
```

Requirements: Python 3.10+, Pillow 9.4.0 and an FFmpeg executable containing the `libx264` encoder. The supplied file was encoded with FFmpeg 5.0.1. Pass `--ffmpeg /path/to/ffmpeg` if the executable is not on PATH. The renderer discovers installed Segoe UI fonts on Windows and DejaVu Sans on Linux, or accepts `--font-dir /path/to/fonts`. Fonts are not redistributed. Different platform fonts or encoder versions can change output bytes; the release manifest identifies the exact bundled file.

To inspect the four chapter stills, add `--preview-dir runs/film-preview`. Default outputs are the bundled MP4 and JPEG poster. Existing files at those output paths are replaced deliberately. There are no build requirements for simply viewing the committed website.

The original manuscript's training/data/deployment limitations still apply. The animation demonstrates the intended mechanism and does not extend the paper's evidence.

## Inline repository animation

The root README embeds `site/assets/boundary-animation.gif` directly, before the cases and repository guide. It contains the same complete 24-second film at 960 × 540 and 10 fps, looping without a player or external host. The `<picture>` element selects the static poster for browsers requesting reduced motion. The project website retains the native MP4 player with playback controls.

Rebuild the GIF from the committed MP4:

```bash
python scripts/render_readme_animation.py
```

Only FFmpeg is required for this conversion. All paths in the README are relative to the repository; no personal account or external media URL is embedded. The GIF is an explanatory illustration with the same limitations as the video.

## Case figures

The README and website embed three 1600 × 960 PNG figures: `case-network.png`, `case-conflict.png` and `case-consent.png`. Matching SVG files preserve selectable text and vector geometry. All instruction, factor and response text is read directly from the fixed `examples` object in `site/app.js`, so the figures and interactive cases share the same authored content.

```bash
python -m pip install -r requirements-media.txt
python scripts/render_case_figures.py
```

The renderer uses Pillow and installed Segoe UI or DejaVu Sans fonts; `--font-dir` selects a font directory. It reads the fixed object as data without evaluating JavaScript. The figures show the preserved frame, safety-critical change, policy behavior and two safe responses. They do not contain experimental judgments or claim to be released training examples. PNG files contain no identifying metadata, and no third-party media is used.
