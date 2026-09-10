"""Owner-side encrypted intake using an existing GitHub CLI login. No paid AI API."""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
import sealed,transport

def main():
    parser=argparse.ArgumentParser();parser.add_argument('job',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('output must not exist')
    archive=sealed.pack(args.job);key=sealed.new_key();session=sealed.new_session()
    checkpoint=args.output.with_name(args.output.name+'-client-key.json')
    if checkpoint.exists():raise ValueError('client checkpoint already exists')
    checkpoint.parent.mkdir(parents=True,exist_ok=True)
    # Keep this ONLY on the owner's machine; it is never sent to GitHub.
    with checkpoint.open('x') as stream:json.dump({'session':session,'private_key':sealed.b64(sealed.private_bytes(key))},stream)
    checkpoint.chmod(0o600)
    request={'version':1,'session':session,'reply_public_key':sealed.public(key),'created_at':time.time()}
    transport.commit({f'territory/transport/requests/{session}':request},'Start owner-authorized encrypted territory job')
    deadline=time.monotonic()+600;server=None
    while time.monotonic()<deadline:
        try:server=transport.read(f'territory/transport/sessions/{session}/public.json');break
        except transport.TransportError:time.sleep(5)
    if server is None or server.get('session')!=session or server.get('expires_at',0)<time.time():raise ValueError('worker session unavailable; private files were not uploaded')
    transport.send_envelope(sealed.seal(archive,server['public_key'],session,'job'),'inputs')
    deadline=time.monotonic()+3000;result=None
    while time.monotonic()<deadline:
        try:result=transport.receive_envelope(session,'outputs');break
        except transport.TransportError:time.sleep(10)
    if result is None:raise ValueError('encrypted result not available; keep the local recovery key')
    sealed.unpack(sealed.unseal(result,key,session,'result'),args.output)
    print('Encrypted result received. Read CHECKPOINT.json for actual gate status; no approval is implied.')
    return 0
if __name__=='__main__':raise SystemExit(main())
