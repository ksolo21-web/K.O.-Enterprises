"""Single loopback generation with an absolute deadline, no redirect/retry."""
import http.client
import json
import socket
import threading
import time
from .core import DataError
from .local_runtime import MAX_REQUEST_BYTES

PORT=11434


def request_json(method,endpoint,payload=None,*,timeout=120,max_bytes=200000):
    if type(timeout) not in (int,float) or not 0<timeout<=600 or type(max_bytes) is not int or not 128<=max_bytes<=1000000:
        raise DataError('Invalid bounded generation deadline/reply limit')
    if (method,endpoint) not in (('GET','/api/tags'),('POST','/api/generate')) or (method=='GET' and payload is not None) or (method=='POST' and not isinstance(payload,dict)):
        raise DataError('Unapproved bounded loopback endpoint')
    encoded=json.dumps(payload,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode() if payload is not None else None
    if encoded is not None and len(encoded)>MAX_REQUEST_BYTES:raise DataError('Bounded generation request exceeds media budget')
    conn=http.client.HTTPConnection('127.0.0.1',PORT,timeout=timeout)
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM);sock.settimeout(timeout);conn.sock=sock
    control=sock.dup()
    expired=threading.Event();started=time.monotonic()
    def stop():
        expired.set()
        # Keep an independent descriptor: HTTP/1.0 getresponse may close the
        # connection's socket object while its buffered body still owns the fd.
        try:control.shutdown(socket.SHUT_RDWR)
        except OSError:pass
        # Do not call HTTPConnection.close from the watchdog: buffered-response
        # locks belong to the reader thread. Shutdown interrupts its read safely.
    timer=threading.Timer(timeout,stop);timer.daemon=True;timer.start()
    try:
        sock.connect(('127.0.0.1',PORT))
        if expired.is_set():raise TimeoutError('Absolute generation deadline expired')
        conn.request(method,endpoint,encoded,{'Content-Type':'application/json','Accept':'application/json'})
        response=conn.getresponse()
        if response.status!=200:raise DataError('Generation status rejected; no redirect or retry')
        chunks=[];size=0
        while True:
            chunk=response.read1(min(16384,max_bytes+1-size))
            if expired.is_set() or time.monotonic()-started>=timeout:raise TimeoutError('Absolute generation deadline expired')
            if not chunk:
                if response.length is not None and response.length>0:raise DataError('Generation response body truncated')
                break
            size+=len(chunk)
            if size>max_bytes:raise DataError('Generation response exceeds budget')
            chunks.append(chunk)
        value=json.loads(b''.join(chunks))
        if not isinstance(value,dict):raise DataError('Generation response is not an object')
        return value
    except (OSError,http.client.HTTPException,ValueError,UnicodeError) as exc:
        if expired.is_set() or isinstance(exc,TimeoutError):raise DataError('Absolute generation deadline expired') from exc
        raise DataError('Bounded local generation failed') from exc
    finally:
        timer.cancel();conn.close();control.close()


def generate(payload,*,timeout=120,max_bytes=200000):
    return request_json('POST','/api/generate',payload,timeout=timeout,max_bytes=max_bytes)
