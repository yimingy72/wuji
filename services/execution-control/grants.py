"""Purpose-limited grants; service credentials never enter model context."""
import base64,hashlib,hmac,json,time
from uuid import UUID

def encode(value):return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
def issue(key,claims,expires):
    body=encode(json.dumps({**claims,"exp":int(expires)},sort_keys=True,separators=(",",":")).encode())
    sig=encode(hmac.new(key.encode(),("wuji-core-v1."+body).encode(),hashlib.sha256).digest())
    return body+"."+sig
def verify(key,token,role):
    try:
        body,sig=token.split(".",1)
        expected=encode(hmac.new(key.encode(),("wuji-core-v1."+body).encode(),hashlib.sha256).digest())
        if not hmac.compare_digest(expected,sig):raise ValueError
        claims=json.loads(base64.urlsafe_b64decode(body+"="*(-len(body)%4)))
        if claims["role"]!=role or claims["exp"]<=time.time():raise ValueError
        UUID(claims["task_id"])
        return claims
    except Exception:raise ValueError("invalid execution credential") from None
