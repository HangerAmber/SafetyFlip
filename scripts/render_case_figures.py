"""Render original case figures from the site's exact illustrative examples.

Python 3.10+ and Pillow 9.4+; no model, network or experimental data is used.
Run from the repository root: python scripts/render_case_figures.py
Outputs: site/assets/case-{network,conflict,consent}.{svg,png}.
The SVG preserves text; the PNG is suitable for inline repository rendering.
Use --font-dir for Segoe UI or DejaVu Sans fonts. Fonts are not redistributed.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, SCALE = 1600, 960, 2
INK, PAPER, LINE = "#20372d", "#f5f4ed", "#d7dfd1"
GREEN, ORANGE, MUTED = "#17644c", "#9b542f", "#687b65"
TITLES = {
    "network": ("01", "Authorization changes the obligation."),
    "conflict": ("02", "Intent changes the obligation."),
    "consent": ("03", "Consent changes the obligation."),
}


def load_examples(path: Path) -> dict:
    """Read the fixed object literal as JSON without evaluating JavaScript."""
    source = path.read_text(encoding="utf-8")
    match = re.search(r"const examples = (\{.*?\n\});", source, re.S)
    if not match:
        raise ValueError("Cannot locate the examples object in site/app.js")
    # The example object is restricted to string values and unquoted keys.
    literal = re.sub(r"([{,]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', match[1])
    examples = json.loads(literal)
    if set(examples) != set(TITLES):
        raise ValueError("Update the figure titles for the changed example set")
    return examples


def font_paths(directory: str | None) -> tuple[Path, Path, str]:
    roots = [Path(directory)] if directory else [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")]
    for root in roots:
        for regular, bold, family in (("segoeui.ttf", "segoeuib.ttf", "Segoe UI"),
                                      ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVu Sans")):
            if (root / regular).exists() and (root / bold).exists():
                return root / regular, root / bold, family
    raise ValueError("Provide --font-dir containing Segoe UI or DejaVu Sans")


class Canvas:
    """Emit identical vector primitives and antialiased raster primitives."""

    def __init__(self, fonts, description):
        self.fonts = fonts
        self.cache = {}
        self.image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), PAPER)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
                    '<title id="title">SafetyFlip illustrative counterfactual case</title>',
                    f'<desc id="desc">{escape(description)}</desc>']
        self.rect(0, 0, WIDTH, HEIGHT, PAPER)

    def font(self, size, bold=False):
        key = size, bold
        if key not in self.cache:
            self.cache[key] = ImageFont.truetype(str(self.fonts[int(bold)]), size * SCALE)
        return self.cache[key]

    def measure(self, text, size, bold=False):
        return self.font(size, bold).getlength(text) / SCALE

    def rect(self, x, y, w, h, fill, radius=0, outline=None):
        box = (x * SCALE, y * SCALE, (x + w) * SCALE, (y + h) * SCALE)
        self.draw.rounded_rectangle(box, radius * SCALE, fill=fill, outline=outline, width=SCALE)
        border = f' stroke="{outline}"' if outline else ""
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"{border}/>')

    def line(self, x1, y1, x2, y2, fill=LINE, width=1):
        self.draw.line((x1 * SCALE, y1 * SCALE, x2 * SCALE, y2 * SCALE), fill=fill, width=width * SCALE)
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{fill}" stroke-width="{width}"/>')

    def text(self, x, baseline, text, size=26, fill=INK, bold=False):
        self.draw.text((x * SCALE, baseline * SCALE), text, font=self.font(size, bold), fill=fill, anchor="ls")
        family = escape(self.fonts[2])
        self.svg.append(f'<text x="{x:.2f}" y="{baseline:.2f}" font-family="{family},sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{fill}">{escape(text)}</text>')

    def paragraph(self, x, baseline, text, width, size=26, leading=35, fill=INK, max_lines=4):
        lines, current = [], ""
        for word in text.split():
            trial = (current + " " + word).strip()
            if self.measure(trial, size) > width and current:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        if len(lines) > max_lines:
            raise ValueError(f"Text overflows its figure area: {text}")
        for index, line in enumerate(lines):
            self.text(x, baseline + index * leading, line, size, fill)
        return len(lines)

    def instruction(self, x, baseline, data, width, accent, wash):
        # Keep the exact before / critical / after text, emphasizing only the
        # authored critical span, as in the interactive page.
        runs = [("“" + data["before"], False), (data["critical"], True), (data["after"] + "”", False)]
        cursor, row = x, 0
        for text, highlighted in runs:
            for token in re.findall(r"\S+|\s+", text):
                length = self.measure(token, 31, highlighted)
                if cursor + length > x + width and token.strip():
                    cursor, row = x, row + 1
                if cursor == x and not token.strip():
                    continue
                if row > 3:
                    raise ValueError("Instruction overflows the four-line area")
                yy = baseline + row * 43
                if highlighted:
                    self.rect(cursor - 1, yy - 31, length + 2, 40, wash, 3)
                self.text(cursor, yy, token, 31, accent if highlighted else INK, highlighted)
                cursor += length

    def save(self, base: Path):
        base.parent.mkdir(parents=True, exist_ok=True)
        base.with_suffix(".svg").write_text("\n".join(self.svg + ["</svg>\n"]), encoding="utf-8")
        self.image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(base.with_suffix(".png"), optimize=True)


def render(key, example, fonts, destination):
    number, title = TITLES[key]
    description = f"{title} Illustrative case, not a released training sample. Shared frame: {example['frame']} "
    description += " ".join(f"{side.title()} instruction: {example[side]['before']}{example[side]['critical']}{example[side]['after']} Safe response: {example[side]['response']}" for side in ("safe", "unsafe"))
    canvas = Canvas(fonts, description)
    canvas.text(48, 54, "SafetyFlip", 29, INK, True)
    canvas.text(233, 53, "/  ILLUSTRATIVE CASE", 23, MUTED)
    note = "Not a released training sample"
    canvas.text(WIDTH - 48 - canvas.measure(note, 24), 53, note, 24, MUTED)
    canvas.line(48, 78, 1552, 78)
    canvas.text(48, 136, f"{number}  {title}", 43, INK, True)
    canvas.rect(48, 164, 1504, 96, "#e9eee1", 12)
    canvas.text(72, 197, "PRESERVED SEMANTIC FRAME  /  r_frame", 21, GREEN, True)
    canvas.text(72, 239, example["frame"], 29, INK)
    # Both directions are possible. These panels do not assign a fixed seed.
    canvas.rect(48, 286, 728, 587, "#fdfef9", 15, LINE)
    canvas.rect(824, 286, 728, 587, "#fdfbf7", 15, "#e3d5c6")
    canvas.rect(755, 301, 90, 51, PAPER, 24, LINE)
    canvas.text(774, 340, "↔", 38, GREEN, True)
    for side, x, accent, wash in (("safe", 48, GREEN, "#deedde"), ("unsafe", 824, ORANGE, "#f4e2cf")):
        data = example[side]
        canvas.text(x + 27, 331, f"{side.upper()} INSTRUCTION", 25, accent, True)
        canvas.instruction(x + 27, 385, data, 674, accent, wash)
        canvas.line(x + 27, 492, x + 701, 492)
        canvas.text(x + 27, 527, "CRITICAL FACTOR  /  r_crit", 21, accent, True)
        canvas.paragraph(x + 27, 565, data["factor"], 665, 28, 36, max_lines=2)
        canvas.rect(x + 20, 625, 688, 227, "#ecf3e6" if side == "safe" else "#f7ede1", 11)
        canvas.text(x + 40, 662, "ILLUSTRATIVE SAFE RESPONSE", 21, accent, True)
        behavior = data["behavior"].upper()
        tag_w = canvas.measure(behavior, 21, True) + 24
        canvas.rect(x + 688 - tag_w, 638, tag_w, 34, wash, 7)
        canvas.text(x + 700 - tag_w, 663, behavior, 21, accent, True)
        canvas.paragraph(x + 40, 706, data["response"], 638, 28, 37, max_lines=4)
    canvas.text(48, 924, "Safe ↔ Unsafe instructions. Safe responses on both sides.", 27, GREEN, True)
    label = "Authored illustration · no model inference"
    canvas.text(WIDTH - 48 - canvas.measure(label, 23), 922, label, 23, MUTED)
    canvas.save(destination / f"case-{key}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "site/assets")
    args = parser.parse_args()
    fonts = font_paths(args.font_dir)
    for key, example in load_examples(ROOT / "site/app.js").items():
        render(key, example, fonts, args.output_dir)
        print(f"Rendered case-{key}.svg + .png ({WIDTH} × {HEIGHT}); illustrative only")


if __name__ == "__main__":
    main()
