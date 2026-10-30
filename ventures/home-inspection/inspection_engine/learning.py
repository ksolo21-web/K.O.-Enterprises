"""Controlled learning workflow: human-reference comparisons and review gates.
No automatic weight changes, prompts revisions or training from unapproved reports.
"""
from __future__ import annotations
from .core import SYSTEM_NAME

def _index(items):
    return {(o['system'].strip().lower(), o['feature'].strip().lower()):o for o in items}

def compare_to_human(agent_report:dict,human_report:dict)->dict:
    """Compare structured factual observations. Free-form PDF understanding needs later model integration."""
    agent=_index(agent_report.get('observations',[]))
    human=_index(human_report.get('observations',[]))
    missed=[]; disputed=[]; extra=[]; aligned=[]
    for key, h in human.items():
        a=agent.get(key)
        if a is None or (h['status']=='observed' and a['status']!='observed'):
            missed.append({'system':key[0],'feature':key[1],'human':h,'agent':a})
        elif h['status']!=a['status'] or (h.get('description','').strip().lower()!=a.get('description','').strip().lower()):
            disputed.append({'system':key[0],'feature':key[1],'human':h,'agent':a})
        else: aligned.append(key)
    for key,a in agent.items():
        if key not in human: extra.append({'system':key[0],'feature':key[1],'agent':a})
    return {'missed':missed,'disputed':disputed,'extra':extra,'aligned_count':len(aligned),
            'review_status':'AWAITING QUALIFIED HUMAN LABEL REVIEW',
            'training_approved':False,
            'next_step':'Obtain evidence-bound human decisions; add approved cases to frozen regression set; test candidate change.'}
