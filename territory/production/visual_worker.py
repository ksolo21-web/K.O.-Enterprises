"""Owner-started encrypted visual calibration. No private pixels or answers in logs."""
from __future__ import annotations
import json,os,shutil,sys,tempfile,time
from pathlib import Path
import engine,privacy,sealed,transport as t,visual_review


def run(session):
    sealed.metadata(session,'job')
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!=t.REPO or os.environ.get('GITHUB_REF')!='refs/heads/'+t.BRANCH:raise RuntimeError('Approved public runner required')
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    if event['repository']['private'] is not False or event['sender']['login']!='ksolo21-web':raise RuntimeError('Untrusted or potentially metered event')
    engine.verify_skills()
    request=t.read('territory/transport/visual-requests/'+session)
    if set(request)!={'version','session','client_public'} or request['version']!=1 or request['session']!=session:raise RuntimeError('Invalid session request')
    client_public=request['client_public'];sealed.derive(sealed.new_key(),client_public,{'probe':True})
    identity=visual_review.neural.model_identity()
    key=sealed.new_key();expires=int(time.time())+1200
    t.commit({'territory/transport/sessions/'+session+'/ready.json':{'version':1,'session':session,'server_public':sealed.public(key),'expires':expires,'kind':'visual-calibration'}},'Publish ephemeral encrypted-review readiness [skip ci]')
    envelope=None
    while time.time()<expires:
        try:envelope=t.receive_envelope(session,'inputs');break
        except t.TransportError:time.sleep(5)
    if envelope is None:raise RuntimeError('No complete encrypted input before expiry')
    raw=sealed.unseal(envelope,key,session,'job');tmp=Path(tempfile.mkdtemp(prefix='territory-visual-',dir=os.environ['RUNNER_TEMP']))
    try:
        job=tmp/'input';result=tmp/'output';sealed.unpack(raw,job)
        with privacy.authenticated_session(job,raw):
            visual_review.run(job/'job.json',result,identity=identity)
        answer=sealed.seal(sealed.pack(result),client_public,session,'result');t.send_envelope(answer,'outputs')
        t.commit({'territory/transport/sessions/'+session+'/status.json':{'version':1,'session':session,'status':'encrypted-review-returned','release_ready':False}},'Record encrypted-review completion without private findings [skip ci]')
    finally:shutil.rmtree(tmp,ignore_errors=True)
    return {'session':session,'encrypted_review_returned':True,'release_ready':False}

if __name__=='__main__':
    try:print(json.dumps(run(sys.argv[1])))
    except Exception:print(json.dumps({'status':'review-session-failed','release_ready':False}));raise SystemExit(2)
