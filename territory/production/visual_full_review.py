"""Encrypted read-only full-card visual review with the pinned local vision model.

This reviewer never edits cards and never authorizes release. It compares exact
private PNG evidence supplied by the owner-side encrypted client and returns
raw model receipts plus bounded 0-10 category observations.
"""
from __future__ import annotations
import json, math, time
from pathlib import Path
from PIL import Image
import engine
from runtime import neural

class FullReviewError(engine.GateError): pass

RESULT_SCHEMA = {
    'type':'object',
    'properties':{
        'score':{'type':'number','minimum':0,'maximum':10},
        'observation':{'type':'string','minLength':1,'maxLength':500},
        'blocking_defects':{'type':'array','items':{'type':'string','minLength':1,'maxLength':220},'maxItems':8}
    },
    'required':['score','observation','blocking_defects'],
    'additionalProperties':False
}

def _image(root: Path, name: str) -> Path:
    path = engine.pinned(root, name)
    with Image.open(path) as im:
        if im.format not in ('PNG','JPEG') or im.width < 128 or im.height < 128 or im.width > 1800 or im.height > 1800:
            raise FullReviewError('Bounded readable PNG/JPEG evidence required')
        im.verify()
    return path

def _infer(images, prompt, identity):
    receipt = neural.infer(images, prompt, RESULT_SCHEMA, identity=identity, max_tokens=384)
    result = receipt.get('result')
    if not isinstance(result, dict) or not isinstance(result.get('score'), (int,float)) or not math.isfinite(result['score']):
        raise FullReviewError('Invalid full-card model result')
    return receipt

def run(job: Path, output: Path, *, identity=None) -> dict:
    engine.private_guard(); before = engine.verify_skills()
    if output.exists(): raise FullReviewError('Fresh full-card review output required')
    data = engine.json_read(job); root = job.parent
    if data.get('schema_version') != 1 or data.get('kind') != 'full_card_review':
        raise FullReviewError('Unsupported full-card review operation')
    required = ('candidate','source','approved_template','approved_apartment','neighbor_260','neighbor_264')
    if any(not isinstance(data.get(k), str) for k in required):
        raise FullReviewError('Full-card review requires six explicit image bindings')
    paths = {k:_image(root, data[k]) for k in required}
    identity = identity or neural.model_identity()
    output.mkdir(parents=True)
    prompts = {
      'source_fidelity': (
        [paths['source'], paths['candidate']],
        'Image 1 is the owner-supplied A262 source screenshot and is the assignment-shape authority. Image 2 is the redrawn candidate card. Ignore phone UI styling. Score 0-10 only on whether the candidate faithfully preserves the visible territory polygon, four apartment-building groups, Timberlea Dr / S Livernois Rd relationship, and visible internal-access geometry without invented extra buildings or clearly invented northern drives. Minor schematic simplification is acceptable. A blocking defect is a material geometry/work-scope mismatch.'),
      'template_likeness': (
        [paths['approved_template'], paths['candidate']],
        'Image 1 is the approved Territory 273 design/template reference. Image 2 is A262. Score 0-10 for same design family: sidebar proportions and typography, legend, panel borders, compass, directions area, thin vector-like road treatment, whitespace discipline, and professional visual balance. Territory-specific geometry may differ. List only material mismatches as blocking defects.'),
      'apartment_likeness': (
        [paths['approved_apartment'], paths['candidate']],
        'Image 1 is an approved apartment territory card. Image 2 is A262. Score 0-10 for apartment-card conventions: clear purple assigned building footprints, green assigned interior access where appropriate, red/context distinction, site naming, approach inset clarity, labels and directions. Do not demand identical geography. List blocking defects only when field use or approved-style likeness is materially harmed.'),
      'readability': (
        [paths['candidate']],
        'Review this exact final A262 card at normal output size. Score 0-10 for label legibility, clutter, road/label association, directions readability, sidebar consistency, approach-inset readability, site-label placement, and absence of obvious clipping/collisions. List every material visual defect; do not invent geographic facts.'),
      'neighbor_260': (
        [paths['neighbor_260'], paths['candidate']],
        'Image 1 is neighboring Territory 260 source assignment; Image 2 is A262. Score 0-10 for whether the visible worked assignment in A262 appears distinct rather than duplicating 260. Distinguish orientation/context streets from worked colored streets. A material same-property or same-worked-segment overlap is a blocking defect. If images do not support a conclusion, include that as a blocking defect rather than guessing.'),
      'neighbor_264': (
        [paths['neighbor_264'], paths['candidate']],
        'Image 1 is neighboring Territory 264 source assignment; Image 2 is A262. Score 0-10 for whether the visible worked assignment in A262 appears distinct rather than duplicating 264. Distinguish context roads from worked colored streets/buildings. A material same-property or same-worked-segment overlap is a blocking defect. If images do not support a conclusion, include that as a blocking defect rather than guessing.')
    }
    receipts = {}; started = time.monotonic()
    for key,(images,prompt) in prompts.items():
        if time.monotonic()-started > 1800: raise FullReviewError('Full-card review time budget exhausted')
        receipts[key] = _infer(images,prompt,identity)
        engine.json_write(output/(key+'.json'), receipts[key])
    values={k:float(v['result']['score']) for k,v in receipts.items()}
    categories={
      'preservation': min(values['source_fidelity'], values['template_likeness']),
      'geography': min(values['source_fidelity'], values['neighbor_260'], values['neighbor_264']),
      'labels': values['readability'],
      'template': min(values['template_likeness'], values['apartment_likeness']),
      'export': values['readability']
    }
    weights={'preservation':.25,'geography':.25,'labels':.25,'template':.15,'export':.10}
    overall=sum(categories[k]*weights[k] for k in weights)
    blockers=[]
    for key,receipt in receipts.items():
        blockers += [key+': '+x for x in receipt['result']['blocking_defects']]
    report={
      'kind':'private_full_card_visual_review','source_commit':__import__('os').environ.get('GITHUB_SHA'),
      'run_id':__import__('os').environ.get('GITHUB_RUN_ID'),'model_identity':identity,
      'actual_model_inference':True,'checks':{k:v['result'] for k,v in receipts.items()},
      'categories':categories,'overall_score':round(overall,3),'blocking_defects':blockers,
      'visual_pass_at_9':all(v>=9 for v in categories.values()) and not blockers,
      'original_sources':before,'original_sources_after':engine.verify_skills(),
      'release_authorized':False,
      'limitations':['Visual review does not replace deterministic PDF, source-hash, current-inventory, or retained-file gates.','Neighbor checks are limited to the explicitly supplied neighboring assignment images.']
    }
    engine.json_write(output/'full-review.json', report)
    return report
