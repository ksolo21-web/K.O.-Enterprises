"""Ephemeral GitHub worker. Public logs contain no job names, PDFs, or reviews."""
from __future__ import annotations
import argparse,json,os,shutil,tempfile,time
from pathlib import Path
import batch,engine,privacy,sealed,transport

def run(session):
    sealed.metadata(session,'job');engine.verify_skills()
    request_path=f'territory/transport/requests/{session}'
    request=transport.read(request_path)
    if request.get('session')!=session or request.get('version')!=1:raise ValueError('invalid session request')
    history=transport.api(f'repos/{transport.REPO}/commits?path={request_path}&sha={transport.BRANCH}&per_page=1')
    if not history or (history[0].get('author') or {}).get('login')!='ksolo21-web':raise ValueError('session requester is not the authorized owner')
    if abs(time.time()-float(request['created_at']))>1800:raise ValueError('session request expired')
    reply=request['reply_public_key'];key=sealed.new_key()
    transport.commit({f'territory/transport/sessions/{session}/public.json':{'version':1,'session':session,'public_key':sealed.public(key),'source_commit':os.environ.get('GITHUB_SHA'),'expires_at':time.time()+2400}},'Publish ephemeral territory session public key')
    deadline=time.monotonic()+900;envelope=None
    while time.monotonic()<deadline:
        try:envelope=transport.receive_envelope(session,'inputs');break
        except transport.TransportError:time.sleep(5)
    if envelope is None:raise ValueError('encrypted input window expired')
    payload=sealed.unseal(envelope,key,session,'job')
    with tempfile.TemporaryDirectory(prefix='territory-private-',dir=os.environ.get('RUNNER_TEMP')) as temp:
        root=Path(temp);job=root/'job';sealed.unpack(payload,job)
        with privacy.authenticated_session(job,payload):
            result=root/'result';batch.run(job,result,budget_seconds=1800)
        cipher=sealed.seal(sealed.pack(result),reply,session,'result')
        transport.send_envelope(cipher,'outputs')
    print('Encrypted result stored. This is not a card-release approval.',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('session');args=p.parse_args()
    try:run(args.session)
    except Exception:
        # Never leak private card identifiers through exception messages/logs.
        print('Worker did not complete. No release approval was issued.',flush=True);return 2
    return 0
if __name__=='__main__':raise SystemExit(main())
