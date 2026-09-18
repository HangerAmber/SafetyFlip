"""Convert the concept film to an inline, looping README animation.

This reuses the authored MP4; it does not generate or visualize research data.
Requires FFmpeg. No network access, account, or model is used.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--input", type=Path, default=ROOT / "site/assets/boundary-film.mp4")
    parser.add_argument("--output", type=Path, default=ROOT / "site/assets/boundary-animation.gif")
    args = parser.parse_args()
    binary = shutil.which(args.ffmpeg)
    if not binary:
        parser.error("FFmpeg was not found; install it or pass --ffmpeg")
    if not args.input.is_file():
        parser.error("Input MP4 was not found; render_boundary_film.py can rebuild it")
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must be different files")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    filters = (
        "fps=10,scale=960:-1:flags=lanczos,split[a][b];"
        "[a]palettegen=stats_mode=diff[p];"
        "[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle"
    )
    subprocess.run([
        binary, "-hide_banner", "-loglevel", "error", "-y", "-i", str(args.input),
        "-filter_complex", filters, "-an", "-loop", "0", "-map_metadata", "-1",
        str(args.output),
    ], check=True)
    print(f"README animation written: {args.output.name} ({args.output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
