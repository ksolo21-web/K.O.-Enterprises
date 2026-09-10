"""Read-only encrypted return delivery. No decrypting or processing private files."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sealed
import transport

MAX_DOWNLOAD_BYTES=2_000_000
class DeliveryError(RuntimeError): pass

def mirror(session:str, destination:Path) -> dict:
    sealed.metadata(session,'result')
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():
        raise DeliveryError('Fresh encrypted download destination required')
    request=transport.read(f'territory/transport/requests/{session}')
    if not isinstance(request,dict) or request.get('session')!=session or type(request.get('version')) is not int or request['version']!=1:
        raise DeliveryError('Session request differs')
    envelope=transport.receive_envelope(session,'outputs')
    if not isinstance(envelope,dict) or set(envelope)!={'version','session','purpose','sender','receiver','nonce','ciphertext'}:
        raise DeliveryError('Unexpected encrypted return fields')
    if (type(envelope['version']) is not int or envelope['version']!=1 or
        envelope['session']!=session or envelope['purpose']!='result' or
        envelope['receiver']!=request.get('reply_public_key')):
        raise DeliveryError('Encrypted return is not addressed to this session owner')
    for key,length in [('sender',32),('receiver',32),('nonce',12)]:
        if len(sealed.unb64(envelope[key],100))!=length:
            raise DeliveryError('Invalid encrypted return header')
    if not 16<len(sealed.unb64(envelope['ciphertext'],MAX_DOWNLOAD_BYTES))<=MAX_DOWNLOAD_BYTES:
        raise DeliveryError('Encrypted return exceeds download bounds')
    raw=sealed.canonical(envelope)
    if len(raw)>MAX_DOWNLOAD_BYTES:
        raise DeliveryError('Encrypted return exceeds download bounds')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(raw)
    destination.chmod(0o600)
    if destination.read_bytes()!=raw:
        destination.unlink(missing_ok=True)
        raise DeliveryError('Saved encrypted return differs')
    return {'session':session,'encrypted_bytes':len(raw),
            'sha256':hashlib.sha256(raw).hexdigest(),
            'content_decrypted':False,'card_release_authorized':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session');parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    try: print(json.dumps(mirror(args.session,args.destination),sort_keys=True))
    except (DeliveryError,sealed.EnvelopeError,transport.TransportError,OSError):
        raise SystemExit('Encrypted delivery did not complete; no private content was logged.')
