"""Private, permission-gated local reference access; no full text in public GitHub.

A purchase/subscription alone is not treated as permission for machine ingestion.
This module verifies metadata and a private local file; never copies file bytes
into an output record, commits documents, or uses any remote service.
"""
from __future__ import annotations
from datetime import date
import hashlib
from pathlib import Path
import re

HEX=re.compile(r'[0-9a-f]{64}\Z')
class LicenseBlock(ValueError): pass


def prepare_licensed_reference(file:Path, *, private_root:Path, permission:dict)->dict:
    root=Path(private_root).resolve(strict=True)
    requested=Path(file)
    if requested.is_symlink():raise LicenseBlock('Symlink references are prohibited')
    target=requested.resolve(strict=True)
    if (root.stat().st_mode & 0o077) != 0:
        raise LicenseBlock('Private library directory must not permit group or public access')
    if not target.is_file() or target==root or root not in target.parents:
        raise LicenseBlock('Licensed reference must stay inside the designated private library')
    if target.stat().st_size>150*1024*1024:raise LicenseBlock('Reference file exceeds configured local indexing limit')
    if not isinstance(permission,dict):raise LicenseBlock('Rights receipt required')
    for key in ('publisher','title','edition','licensee','permission_receipt_sha256','expires_on'):
        if not isinstance(permission.get(key),str) or not permission[key].strip():
            raise LicenseBlock('Rights receipt incomplete: '+key)
    if not HEX.fullmatch(permission['permission_receipt_sha256']):raise LicenseBlock('Invalid rights receipt hash')
    try:expiry=date.fromisoformat(permission['expires_on'])
    except ValueError as e:raise LicenseBlock('Invalid license expiry') from e
    if expiry<date.today():raise LicenseBlock('Licensed access expired')
    if permission.get('machine_indexing_authorized') is not True:
        raise LicenseBlock('No explicit rights for automated ingestion or indexing')
    if permission.get('private_local_only') is not True:
        raise LicenseBlock('Source license does not permit the required private use')
    if permission.get('public_repository_distribution') is True:
        raise LicenseBlock('Restricted full text is not distributed to public repositories')
    digest=hashlib.sha256()
    with target.open('rb') as fh:
        for chunk in iter(lambda:fh.read(1024*1024), b''):digest.update(chunk)
    return {'status':'PRIVATE_REFERENCE_LICENSE_DECLARED_NEEDS_RIGHTS_REVIEW',
            'title':permission['title'],'publisher':permission['publisher'],
            'edition':permission['edition'],'file_sha256':digest.hexdigest(),
            'permission_receipt_sha256':permission['permission_receipt_sha256'],
            'license_expiry':permission['expires_on'],
            'machine_use_permission_recorded':True,'publisher_authorization_independently_verified':False,
            'machine_indexing_approved_for_production':False,
            'public_text_export_allowed':False,
            'content_extracted':False,'customer_release_allowed':False}
