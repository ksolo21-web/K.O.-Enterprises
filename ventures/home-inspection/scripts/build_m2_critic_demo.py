"""Disclosed scripted technical-review test; creates no real inspection findings."""
from pathlib import Path
import json
from inspection_engine.critic import review_specialist_dossier
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output'/'m2_specialist_demo'
OUT=ROOT/'output'/'m2_critic_demo'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    doc=json.loads((BASE/'03_project_unapproved.json').read_text())
    dossier=json.loads((BASE/'02_specialist_dossier.json').read_text())
    examples=[]
    def fake_reviewer(image,prompt):
        examples.append({'image_size_bytes':len(image),'saw_claim_as_data':'CLAIM DATA:' in prompt})
        return {'decision':'insufficient_evidence','reason':'Synthetic picture cannot demonstrate material identity or hidden conditions.',
                'missing_evidence':'Inspector observation and close photo of material edge or manufacturer label.'}
    reviewed=review_specialist_dossier(doc,BASE,dossier,fake_reviewer,
                                reviewer_id='Q02',provider_id='DISCLOSED_SCRIPTED_SECOND_PASS')
    (OUT/'01_separate_technical_review.json').write_text(json.dumps(reviewed,indent=2)+'\n')
    (OUT/'02_review_execution_metadata.json').write_text(json.dumps({
        'provider_is_scripted':True,'real_model_executed':False,
        'source_media_verified':True,'prompts_received':examples,
        'reviewer_role':'Q02','qualified_human_signed':False,
        'customer_release_allowed':False},indent=2)+'\n')
    print(json.dumps({'review_items':len(reviewed['items']), 'summary':reviewed['decision_summary'],
                      'customer_release_allowed':False},indent=2))
if __name__=='__main__':main()
