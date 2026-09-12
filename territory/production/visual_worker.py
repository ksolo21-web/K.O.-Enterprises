"""Owner-started encrypted visual review; public failures contain no private data."""
from __future__ import annotations
import json,os,shutil,sys,tempfile,time
from pathlib import Path
import engine,privacy,sealed,transport as t,visual_review,real_card_review

INPUT_WINDOW_SECONDS=int(os.environ.get('TERRITORY_REVIEW_INPUT_WINDOW_SECONDS','1200'))
if not 60<=INPUT_WINDOW_SECONDS<=5400:raise RuntimeError('Invalid encrypted-review input window')

def run(session):
    sealed.metadata(session,'job')
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!=t.REPO or os.environ.get('GITHUB_REF')!='refs/heads/'+t.BRANCH:raise RuntimeError('Approved public runner required')
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    if event['repository']['private'] is not False or event['sender']['login']!='ksolo21-web':raise RuntimeError('Untrusted or potentially metered event')
    stage='verify_sources';tmp=None
    try:
        engine.verify_skills()
        stage='validate_request'
        request=t.read('territory/transport/visual-requests/'+session)
        if set(request)!={'version','session','client_public'} or type(request['version']) is not int or request['version']!=1 or request['session']!=session:raise RuntimeError('Invalid session request')
        client_public=request['client_public'];sealed.derive(sealed.new_key(),client_public,{'probe':True})
        stage='verify_local_model';identity=visual_review.neural.model_identity()
        key=sealed.new_key();expires=int(time.time())+INPUT_WINDOW_SECONDS
        stage='publish_readiness'
        t.commit({'territory/transport/sessions/'+session+'/ready.json':{'version':1,'session':session,'server_public':sealed.public(key),'expires':expires,'kind':'visual-review','run_id':os.environ.get('GITHUB_RUN_ID'),'source_commit':os.environ.get('GITHUB_SHA')}},'Publish ephemeral encrypted-review readiness [skip ci]')
        envelope=None;stage='receive_input'
        while time.time()<expires:
            try:envelope=t.receive_envelope(session,'inputs');break
            except t.MissingObject:time.sleep(5)
        if envelope is None:raise TimeoutError('Input window expired')
        stage='authenticate_input';raw=sealed.unseal(envelope,key,session,'job')
        tmp=Path(tempfile.mkdtemp(prefix='territory-visual-',dir=os.environ['RUNNER_TEMP']))
        stage='unpack_input';job=tmp/'input';result=tmp/'output';sealed.unpack(raw,job)
        stage='visual_review'
        operation=engine.json_read(job/'job.json').get('kind')
        with privacy.authenticated_session(job,raw):
            if operation=='territory_card_review':
                real_card_review.run(job/'job.json',result,identity=identity)
            else:
                visual_review.run(job/'job.json',result,identity=identity)
        stage='publish_result'
        answer=sealed.seal(sealed.pack(result),client_public,session,'result');t.send_envelope(answer,'outputs')
        t.commit({'territory/transport/sessions/'+session+'/status.json':{'version':1,'session':session,'status':'encrypted-review-returned','run_id':os.environ.get('GITHUB_RUN_ID'),'operation':operation,'release_ready':False}},'Record encrypted-review completion without private findings [skip ci]')
        return {'session':session,'encrypted_review_returned':True,'operation':operation,'release_ready':False}
    except Exception as error:
        code=('protocol_error' if isinstance(error,t.ProtocolError) else
              'input_window_expired' if isinstance(error,TimeoutError) else
              'authentication_error' if isinstance(error,sealed.EnvelopeError) else
              'transport_error' if isinstance(error,t.TransportError) else 'worker_error')
        public={'version':1,'session':session,'status':'failed','stage':stage,'code':code,
                'run_id':os.environ.get('GITHUB_RUN_ID'),'release_ready':False}
        try:t.commit({'territory/transport/sessions/'+session+'/status.json':public},'Record private-review failure stage without private findings [skip ci]')
        except Exception:pass
        print(json.dumps(public),flush=True)
        raise
    finally:
        if tmp is not None:shutil.rmtree(tmp,ignore_errors=True)

if __name__=='__main__':
    try:print(json.dumps(run(sys.argv[1])))
    except Exception:print(json.dumps({'status':'review-session-failed','release_ready':False}));raise SystemExit(2)
