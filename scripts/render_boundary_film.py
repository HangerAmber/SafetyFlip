"""Render a deterministic explanatory film, never empirical model embeddings.

Optional media build: Python 3.10+, Pillow 9.4+, and FFmpeg with libx264.
Example: python scripts/render_boundary_film.py --font-dir /path/to/fonts
The supplied frames use authored coordinates, not training or benchmark data.
No audio, network, model, author metadata, or external assets are used.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import random
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SECONDS = 1280, 720, 30, 24
INK = (18, 40, 35)
WHITE = (239, 244, 231)
MUTED = (148, 175, 161)
GREEN = (116, 227, 184)
ORANGE = (240, 164, 122)
GRID = (35, 61, 51)
ROOT = Path(__file__).resolve().parents[1]


def ease(value):
    x = max(0., min(1., value))
    return x * x * (3 - 2 * x)


def lerp(a, b, value):
    return a + (b - a) * value


def color(a, b, value):
    return tuple(round(lerp(x, y, value)) for x, y in zip(a, b))


def font_paths(directory):
    roots = [Path(directory)] if directory else [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")]
    for root in roots:
        for regular, bold, mono in (("segoeui.ttf", "seguisb.ttf", "consola.ttf"),
                                    ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSansMono.ttf")):
            paths = tuple(root / item for item in (regular, bold, mono))
            if all(path.exists() for path in paths):
                return paths
    raise ValueError("Supply --font-dir containing Segoe UI or DejaVu Sans font files")


class Film:
    def __init__(self, fonts):
        self.fonts = fonts
        self.cache = {}
        rng = random.Random(17)
        self.points = [(rng.uniform(.2, .8), rng.uniform(.10, .88), index % 2)
                       for index in range(34)]

    def font(self, size, family=0):
        key = size, family
        if key not in self.cache:
            self.cache[key] = ImageFont.truetype(str(self.fonts[family]), size=size)
        return self.cache[key]

    def text(self, draw, xy, text, size=24, fill=WHITE, family=0):
        draw.text(xy, text, fill=fill, font=self.font(size, family))

    def round(self, draw, box, radius=12, fill=GRID, outline=None, width=1):
        draw.rounded_rectangle(tuple(round(x) for x in box), radius, fill=fill, outline=outline, width=width)

    def circle(self, draw, x, y, r, fill, outline=None, width=1):
        draw.ellipse((round(x-r), round(y-r), round(x+r), round(y+r)), fill=fill, outline=outline, width=width)

    def arrow(self, draw, start, end, fill, width=2, head=9):
        draw.line((start, end), fill=fill, width=width)
        angle = math.atan2(end[1]-start[1], end[0]-start[0])
        points = [end] + [(end[0]-head*math.cos(angle+a), end[1]-head*math.sin(angle+a)) for a in (-.48,.48)]
        draw.polygon(points, fill=fill)

    def frame(self, t):
        im = Image.new("RGB", (W,H), INK)
        d = ImageDraw.Draw(im)
        # Distinctive editorial title and a persistent provenance label.
        self.text(d, (48, 33), "SafetyFlip", 25, WHITE, 1)
        self.text(d, (198, 39), "/  THE BOUNDARY IN MOTION", 14, MUTED, 2)
        self.text(d, (811, 39), "CONCEPTUAL FILM / NOT MEASURED EMBEDDINGS", 13, MUTED, 2)
        d.line((48,84,1232,84), fill=GRID, width=1)
        chapter = min(3, int(t//6))
        headings = [("The boundary", "is ambiguous."), ("Flip the factor.", "Keep the frame."),
                    ("Learn a sharper", "local boundary."), ("Different intent.", "Safe responses.")]
        descriptions = [
            ["Surface cues can obscure", "the difference between", "legitimate and unsafe intent."],
            ["Add matched counterfactuals", "in both directions:", "Safe ↔ Unsafe."],
            ["BCFT uses paired supervision", "and SCR to encourage", "safety-relevant separation."],
            ["Help with safe requests.", "Refuse or safely redirect", "unsafe requests."]
        ]
        self.text(d, (48,130), f"0{chapter+1} / {['SEED DATA','COUNTERFACTUALS','BOUNDARY LEARNING','POLICY BEHAVIOR'][chapter]}", 14, GREEN, 2)
        self.text(d, (46,183), headings[chapter][0], 35, WHITE, 1)
        self.text(d, (46,227), headings[chapter][1], 35, GREEN, 1)
        for i, line in enumerate(descriptions[chapter]):
            self.text(d, (48,309+32*i), line, 21, MUTED)
        # A separate note prevents the cartoon from implying measured guarantees.
        for i, line in enumerate(["Authored geometry.", "No model or benchmark is run."]):
            self.text(d, (48,521+24*i), line, 14, MUTED)
        x0,x1,y0,y1 = 440,1230,150,550
        self.round(d, (414,116,1232,580), 18, (22,47,40), (50,74,59))
        for x in range(440,1230,28):
            for y in range(143,565,28):
                self.circle(d,x,y,1,GRID)
        self.text(d, (450,132), "SAFE INSTRUCTION", 13, GREEN, 2)
        self.text(d, (1013,132), "UNSAFE INSTRUCTION", 13, ORANGE, 2)
        learn = ease((t-12.3)/4.6)
        add = ease((t-6.2)/3.5)
        # Background instruction locations are synthetic, animated only to explain the objective.
        for i,(x,y,side) in enumerate(self.points):
            desired = (.20 + .15*(i%6)/5) if side == 0 else (.68+.16*(i%7)/6)
            # Retain ambiguous background points: the schematic makes no claim
            # of universal or perfect separation after training.
            if i == 6: desired = .565
            if i == 19: desired = .49
            xx = x0 + lerp(x,desired,learn)*(x1-x0)
            yy = y0+y*(y1-y0) + math.sin(t*.8+i)*2*(1-learn)
            tone = color(INK, GREEN if side == 0 else ORANGE, .25)
            self.circle(d, xx, yy, 4+(i%3), tone)
        # Boundary deforms locally as pair geometry becomes aligned; this is not a universal axis.
        curve=[]
        for i in range(101):
            y=176+i*3.42
            phase=(y-176)/342
            wavy = 842 + 75*math.sin(phase*math.pi*2+.6) + 22*math.sin(phase*math.pi*4)
            final = 850 + 14*math.sin(phase*math.pi*1.4+.6)
            curve.append((lerp(wavy,final,learn),y))
        for i in range(0,len(curve)-1,4):
            d.line(curve[i:i+3],fill=color(MUTED,WHITE,.35),width=2)
        self.round(d,(770,531,968,562),15,(30,57,47),(80,105,82))
        self.text(d,(789,537),"safety boundary",15,WHITE)
        # Three fixed semantic frames, each with original and generated counterpart.
        pair_y=[244,357,465]
        labels=[("own network","no permission"),("de-escalate","intimidate"),("with consent","no consent")]
        for i, y in enumerate(pair_y):
            # Originals alternate sides, illustrating bidirectionality without harmful outputs.
            safe_x=lerp(744+i*12,665+i*9,learn)
            unsafe_x=lerp(929-i*9,1040-i*8,learn)
            a=add if i!=1 else 1
            b=1 if i!=1 else add
            offset=(1-learn)*[15,-22,12][i]
            sy,uy=y-offset,y+offset
            if add>0:
                tone=color((22,47,40),(98,145,119),add)
                self.arrow(d,(safe_x+14,sy),(lerp(safe_x+14,unsafe_x-14,add),lerp(sy,uy,add)),tone,2,7)
                if add>.92:
                    self.arrow(d,(unsafe_x-14,uy),(safe_x+14,sy),tone,2,7)
            for xx,yy,amount,tone,label in [(safe_x,sy,a,GREEN,labels[i][0]),(unsafe_x,uy,b,ORANGE,labels[i][1])]:
                if amount<=0: continue
                self.circle(d,xx,yy,22,color((22,47,40),tone,.1*amount))
                self.circle(d,xx,yy,10,color((22,47,40),tone,amount),color((22,47,40),WHITE,amount),2)
                self.text(d,(xx-54,yy+27),label,14,color((22,47,40),MUTED,amount))
            if chapter in (1,2):
                self.text(d,(456,y-8),["ACCESS","CONFLICT","PRIVACY"][i],11,MUTED,2)
        if chapter == 1:
            self.round(d,(487,172,772,205),12,(28,64,52))
            self.text(d,(502,178),"Same frame / changed critical factor",14,GREEN)
        if chapter == 2:
            self.arrow(d,(991,190),(737,190),GREEN,2,9)
            self.text(d,(765,163),"learned safety direction",14,GREEN)
        if chapter == 3:
            self.round(d,(466,170,775,207),11,(32,80,60),(73,127,97))
            self.round(d,(892,170,1202,207),11,(73,54,38),(139,99,67))
            self.text(d,(492,177),"COMPLY / helpful assistance",15,GREEN)
            self.text(d,(919,177),"REFUSE / safe pivot",15,ORANGE)
            self.round(d,(502,531,752,562),14,(32,80,60))
            self.round(d,(981,531,1202,562),14,(32,80,60))
            self.text(d,(526,537),"The response is safe.",14,GREEN)
            self.text(d,(995,537),"The response is safe.",14,GREEN)
        # Four-chapter timeline and a readable explanatory sentence.
        captions=["Start near the boundary, where surface cues can mislead.",
                  "Counterfactual supervision isolates what changes the safety label.",
                  "Paired examples encourage safety-relevant shifts while preserving shared utility.",
                  "Instruction safety changes. Response safety does not."]
        self.text(d,(48,608),captions[chapter],20,WHITE)
        names=["01  SEED DATA","02  REVERSAL","03  BCFT + SCR","04  SAFE RESPONSES"]
        for i,name in enumerate(names):
            left=48+i*302
            d.line((left,663,left+280,663),fill=GRID,width=3)
            progress=max(0.,min(1.,(t-i*6)/6))
            if progress>0: d.line((left,663,left+280*progress,663),fill=GREEN,width=3)
            self.text(d,(left,678),name,12,GREEN if i==chapter else MUTED,2)
        return im


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--font-dir")
    p.add_argument("--ffmpeg",default="ffmpeg")
    p.add_argument("--output",type=Path,default=ROOT/"site/assets/boundary-film.mp4")
    p.add_argument("--poster",type=Path,default=ROOT/"site/assets/boundary-poster.jpg")
    p.add_argument("--preview-dir",type=Path)
    args=p.parse_args()
    binary=shutil.which(args.ffmpeg)
    if not binary: p.error("FFmpeg was not found; install it or pass --ffmpeg")
    film=Film(font_paths(args.font_dir))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.poster.parent.mkdir(parents=True,exist_ok=True)
    film.frame(15.6).save(args.poster,quality=94,optimize=True)
    if args.preview_dir:
        args.preview_dir.mkdir(parents=True,exist_ok=True)
        for index,t in enumerate((2,9,15.6,21)):
            film.frame(t).save(args.preview_dir/f"film-chapter-{index+1}.png")
    command=[binary,"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pixel_format","rgb24",
             "-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","-","-an","-c:v","libx264",
             "-preset","medium","-crf","19","-pix_fmt","yuv420p","-movflags","+faststart",
             "-map_metadata","-1",str(args.output)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for index in range(FPS*SECONDS):
            process.stdin.write(film.frame(index/FPS).tobytes())
            if index%180==0: print(f"Rendered {index//FPS}/{SECONDS} seconds",flush=True)
        process.stdin.close()
        if process.wait()!=0: raise RuntimeError("FFmpeg encoding failed")
    except BaseException:
        process.kill()
        process.wait()
        raise
    print(f"Rendered {SECONDS}s, {W}x{H}, {FPS}fps, H.264; no audio or measured results",flush=True)


if __name__ == "__main__":
    main()
