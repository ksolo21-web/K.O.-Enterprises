#!/usr/bin/env python3
"""Upload the exact source capsule using the owner's existing GitHub CLI login.
No token is printed, no paid API is called, and main is never changed.
"""
from pathlib import Path
import base64
import hashlib
import json
import subprocess
import sys

REPO='ksolo21-web/K.O.-Enterprises'
BRANCH='territory-card-production'
PATH='territory/production/Territory-Skills-Source-Capsule.zip'
EXPECTED='49809b315b7dd9939912eca9a716a196abc67a8e649e74c44e1613d5cbc5deb9'

def api(endpoint, data=None):
    command=['gh','api',endpoint]
    text=None
    if data is not None:
        command += ['--method','POST','--input','-']
        text=json.dumps(data)
    result=subprocess.run(command,input=text,text=True,capture_output=True,check=True)
    return json.loads(result.stdout)

def main():
    if len(sys.argv)!=2:raise SystemExit('Usage: python upload_capsule.py Territory-Skills-Source-Capsule.zip')
    archive=Path(sys.argv[1]);raw=archive.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise SystemExit('The archive hash does not match the recovered original capsule.')
    subprocess.run(['gh','auth','status'],check=True,stdout=subprocess.DEVNULL)
    repository=api('repos/'+REPO)
    if repository['full_name']!=REPO or repository['private'] is not False:raise SystemExit('Repository identity/visibility changed. Stop for review.')
    ref=api(f'repos/{REPO}/git/ref/heads/{BRANCH}');base=ref['object']['sha']
    commit=api(f'repos/{REPO}/git/commits/{base}');tree=commit['tree']['sha']
    blob=api(f'repos/{REPO}/git/blobs',{'content':base64.b64encode(raw).decode(),'encoding':'base64'})
    expected_blob=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    if blob['sha']!=expected_blob:raise SystemExit('Uploaded Git blob identity mismatch.')
    newtree=api(f'repos/{REPO}/git/trees',{'base_tree':tree,'tree':[{'path':PATH,'mode':'100644','type':'blob','sha':blob['sha']}]})
    newcommit=api(f'repos/{REPO}/git/commits',{'message':'Preserve exact 138-file territory source capsule','tree':newtree['sha'],'parents':[base]})
    # Fast-forward only. A concurrent owner update fails rather than overwriting work.
    result=subprocess.run(['gh','api',f'repos/{REPO}/git/refs/heads/{BRANCH}','--method','PATCH','--input','-'],
                          input=json.dumps({'sha':newcommit['sha'],'force':False}),text=True,capture_output=True,check=True)
    print('Source capsule committed to '+BRANCH+': '+newcommit['sha'])
    print('The branch workflow will verify the exact capsule. This is not approval of real cards.')

if __name__=='__main__':
    try:main()
    except (OSError,subprocess.CalledProcessError,KeyError,ValueError) as error:
        raise SystemExit('Upload did not complete. Check GitHub CLI authentication and permissions; no main-branch change was requested.') from error
