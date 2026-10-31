"""No-network check that every bundled policy and evidence playbook is valid.

Never rewrites a case, fetches proprietary standards, or publishes a report.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from inspection_engine.inspection_policy import load_policy, policy_digest, active_sop_context
from inspection_engine.source_of_truth import load_catalog
from inspection_engine.michigan_authority import load_authorities, authority_digest
from inspection_engine.failure_modes import load_playbooks, playbook_digest
from inspection_engine.descriptors import REQUIRED_FEATURES


def audit():
    policy=load_policy();v2=load_catalog();mi=load_authorities();play=load_playbooks()
    status={
     'status':'OFFLINE_POLICY_CONSISTENCY_PASSED_NOT_FIELD_VALIDATION',
     'snapshot':policy['edition'],
     'national_policy_digest_sha256':policy_digest(),
     'michigan_authorities_sha256':authority_digest(),
     'michigan_failure_modes_sha256':playbook_digest(),
     'reference_count_v4':len(policy['sources']),
     'reference_count_v2':len(v2['source_records']),
     'michigan_code_status_count':len(mi['sources']),
     'system_cards':len(policy['systems']),
     'validated_engine_feature_codes':sum(map(len,REQUIRED_FEATURES.values())),
     'scope_residential_2026':active_sop_context('residential','2026-10-31'),
     'scope_residential_2027':active_sop_context('residential','2027-01-01'),
     'scope_commercial':active_sop_context('commercial','2026-10-31'),
     'explicit_unmapped_topic':'InterNACHI 3.8 fireplace/hearth: inspector coverage triage required',
     'external_source_freshness_verified':False,
     'municipal_ahj_verified':False,
     'full_licensed_code_text_embedded':False,
     'manufacturer_specific_manual_coverage_complete':False,
     'expert_annotated_field_accuracy_verified':False,
     'customer_release_allowed':False,
     'notes':'Policy is integrated offline; a source index is not the full legal text or evidence of the condition of any property.'
    }
    return status


def main():
    parser=argparse.ArgumentParser(description='Audit embedded national/Michigan inspection knowledge offline')
    parser.add_argument('--out',type=Path,help='Optional new JSON audit file; never overwritten')
    args=parser.parse_args()
    result=audit()
    if args.out:
        if args.out.exists():parser.error('Will not overwrite an existing audit record')
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=='__main__':sys.exit(main())
