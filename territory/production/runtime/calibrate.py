"""Blind local-model regression calibration; synthetic tests never qualify real cards."""
from __future__ import annotations
import argparse, hashlib, json, os, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from neural import infer, model_identity

SCHEMA = {'type': 'object', 'properties': {
    'observation': {'type': 'string'},
    'label_collision': {'type': 'boolean'}, 'broken_road': {'type': 'boolean'}},
    'required': ['observation', 'label_collision', 'broken_road'], 'additionalProperties': False}
PROMPT = ('Inspect this map crop. The green road is intended to be one closed continuous loop. '
          'broken_road is true only when a white cut interrupts that green loop. '
          'label_collision is true only when dark letters from the two different street names touch or overlap each other. '
          'Judge both checks independently. In observation describe what you can actually see in at most 20 words.')

def fixtures(folder: Path) -> list[dict]:
    folder.mkdir(parents=True, exist_ok=True)
    fonts = [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
             Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf')]
    font_path = next((p for p in fonts if p.exists()), None)
    if font_path is None:
        raise RuntimeError('A normal test font is required; do not replace it with an unreadably small fallback')
    result = []
    for index, (overlap, broken, variant) in enumerate([
            (False, False, 0), (True, False, 0), (False, True, 0), (True, True, 0),
            (False, True, 1), (False, False, 1), (True, True, 1), (True, False, 1)]):
        im = Image.new('RGB', (672, 448), 'white')
        d = ImageDraw.Draw(im)
        box = (52 + variant*10, 54 + variant*12, 620 - variant*8, 394 - variant*6)
        d.rounded_rectangle(box, radius=28, outline=(35, 145, 75), width=8)
        if broken:
            if variant == 0: d.rectangle((302, box[1]-5, 337, box[1]+12), fill='white')
            else: d.rectangle((box[0]-5, 234, box[0]+12, 274), fill='white')
        font = ImageFont.truetype(str(font_path), 35-variant*2)
        a, b = ('Cedar Lane', 'Maple Road') if variant == 0 else ('Willow Court', 'Pine Street')
        first = (142 + variant*12, 150 + variant*13)
        second = (first[0] + (38 if overlap else 0), first[1] + (11 if overlap else 84))
        d.text(first, a, font=font, fill=(28, 28, 28)); d.text(second, b, font=font, fill=(28, 28, 28))
        name = hashlib.sha256(('fixture-v2-'+str(index)).encode()).hexdigest()[:16]
        path = folder / (name+'.png'); im.save(path)
        result.append({'file': path, 'id': name, 'expected': {'label_collision': overlap, 'broken_road': broken},
                       'split': 'development' if variant == 0 else 'held_out'})
    return result

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--fixtures-only', action='store_true'); args = parser.parse_args()
    cases = fixtures(args.out.parent / 'calibration-images')
    if args.fixtures_only:
        print(json.dumps([{'id': c['id'], 'file': str(c['file']), **c['expected']} for c in cases], indent=2)); return 0
    identity = model_identity(); records = []
    for case in cases:
        try:
            receipt = infer([case['file']], PROMPT, SCHEMA, identity=identity, max_tokens=256)
            passed = all(receipt['result'][k] is v for k, v in case['expected'].items())
            records.append({'id': case['id'], 'split': case['split'], 'expected': case['expected'],
                            'passed': passed, 'receipt': receipt})
        except Exception as error:
            records.append({'id': case['id'], 'split': case['split'], 'expected': case['expected'],
                            'passed': False, 'error': type(error).__name__ + ': ' + str(error)})
        print(json.dumps({k: records[-1].get(k) for k in ('id', 'passed', 'error')}, sort_keys=True), flush=True)
        report = {'schema_version': 3, 'source_commit': os.environ.get('GITHUB_SHA'),
                  'run_id': os.environ.get('GITHUB_RUN_ID'), 'model_identity': identity,
                  'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'completed': len(records), 'required': len(cases),
                  'passed': sum(r['passed'] for r in records), 'cases': records,
                  'synthetic_calibration_passed': len(records)==len(cases) and all(r['passed'] for r in records),
                  'real_card_qualification': False, 'release_authorized': False}
        args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['synthetic_calibration_passed'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
