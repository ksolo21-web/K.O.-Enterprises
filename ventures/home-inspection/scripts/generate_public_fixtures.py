"""Generate public-safe inspection fixtures for tests and demonstrations.

Synthetic schematics only: not photographs, customers, inspections, or labeled defects.
Generated assets are intentionally not committed to the public repository.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw


def make_exterior(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 1800, 960
    img = Image.new('RGB', (w, h), (183, 210, 224))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 720, w, h), fill=(91, 147, 94))
    d.rectangle((180, 398, 1570, 735), fill=(189, 191, 183), outline=(52, 63, 71), width=9)
    d.polygon([(112, 416), (860, 160), (1642, 419)], fill=(73, 76, 87), outline=(36, 42, 49), width=11)
    d.rectangle((285, 491, 800, 733), fill=(228, 226, 209), outline=(43, 50, 58), width=12)
    for x in range(320, 790, 80):
        d.line((x, 497, x, 727), fill=(124, 132, 136), width=5)
    for x in (1020, 1350):
        d.rectangle((x, 470, x + 210, 646), fill=(196, 229, 234), outline=(65, 84, 93), width=14)
        d.line((x+105,470,x+105,646),fill=(65,84,93),width=9)
        d.line((x,558,x+210,558),fill=(65,84,93),width=9)
    d.rectangle((835, 490, 945, 733), fill=(67, 71, 80), outline=(224, 214, 182), width=9)
    d.rectangle((120, 755, 1620, 880), fill=(141, 146, 132))
    d.text((45, 30), 'SYNTHETIC INSPECTION TEST FIXTURE - NOT PROPERTY EVIDENCE', fill=(16, 31, 45))
    img.save(path, optimize=True)


def make_evidence(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img=Image.new('RGB', (1100, 700), (247, 246, 240))
    d=ImageDraw.Draw(img)
    d.rectangle((110, 155, 930, 510), outline=(40, 51, 68), width=18)
    d.line((95, 520, 940, 520),fill=(132, 147, 151),width=30)
    d.rectangle((190, 340, 360, 500),outline=(27,96,153),width=10)
    d.text((110, 75), 'SYNTHETIC SCHEMATIC - NO REAL PROPERTY', fill=(20,30,40))
    img.save(path,optimize=True)


def generate(root: Path, video: bool) -> None:
    e=root/'examples'
    image=e/'demo_exterior.png'
    make_exterior(image)
    make_evidence(e/'demo_evidence.png')
    section=e/'v05_photo_from_video'
    section.mkdir(parents=True,exist_ok=True)
    make_exterior(section/'demo_exterior.png')
    make_evidence(section/'demo_evidence.png')
    if video:
        # Use distinctly changing pixels, not a static image repeated over time.
        # Synthetic motion is essential: a still loop cannot test whether a model
        # selects a video moment on the basis of temporally varying evidence.
        destination=section/'synthetic_moving_house_view.mp4'
        with tempfile.TemporaryDirectory(prefix='.synthetic_frames_', dir=section) as folder:
            frames=Path(folder)
            with Image.open(image) as exterior:
                base=exterior.convert('RGB')
            for index in range(4):
                frame=base.copy()
                pen=ImageDraw.Draw(frame)
                # First half: orange square. Second half: blue circle.
                # Shape/color difference survives standard H.264 compression.
                if index < 2:
                    pen.rectangle((1340, 125, 1580, 365), fill=(245, 130, 24))
                else:
                    pen.ellipse((1340, 125, 1580, 365), fill=(24, 83, 228))
                frame.save(frames/f'frame_{index:02d}.png', optimize=True)
            cmd=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                 '-framerate','1','-i',str(frames/'frame_%02d.png'),
                 '-t','4','-vf','fps=4,format=yuv420p',
                 '-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',
                 '-movflags','+faststart',str(destination)]
            subprocess.run(cmd,check=True,capture_output=True,timeout=90)
    print('Generated synthetic fixtures in',e)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--no-video',action='store_true')
    a=p.parse_args()
    generate(a.root.resolve(),not a.no_video)
