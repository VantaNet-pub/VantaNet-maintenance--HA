"""Installation-bound, offline RSA license verification.

Only the public key is shipped. The private signing key must never be included in
the app, repository, container image, backups shared with customers, or releases.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from berlin_time import BERLIN

from flask import abort, jsonify, redirect, request, session

PRODUCT='vantanet-maintenance'
PUBLIC_N_B64='yzPnubExhsmJYkM0ya5ZvDxJ62ZJ1Akv0AQ1JULtY1pHpaLwYMBrjB1nESQTN8yuu3o1goz7FC3MoDxM_f9GBFeyvz3KLgPp4Wq0ewTY3QP3MHWH5-8Gf__lDfbF9wSi3uy5_29ZlJmgwhlrER3tkrWYAzm1XaVhNMHP2UL53VohmkLVSYUmDuSfbWc7ty0tJoh-Z6QFzvYTmYDBXgXSTO7o64ydamCWAOsgn0fT2PYns07RFfdJPEVXy4eBvcNMJkGg9YPjuLn5CJv3VqpZYYj7W1_n-I28JgImne8ufzhi0_gU5rtExUSNZtULU8Ojhs0hkJEZwr1XV7Mdus9AH_tfFQzJH3VFGd-OoPDE2DFmO6M4BTG3uX51PicCrF1SRD3TYcl8-X1e2LUBucgW8CMywxvjmTt-KFN2YNGhgpMRCFPpBKjFhMVoaKTMTHVuC98VbYY3sMXRkPa8eWi0jkFFZ5TSsZvgJL5V1tXYULUaZ6wBfB8vNwefPMqQ_HxJ'
PUBLIC_E=65537
SHA256_DIGEST_INFO=bytes.fromhex('3031300d060960864801650304020105000420')


def _decode(value):
    return base64.urlsafe_b64decode(value+'='*((4-len(value)%4)%4))


PUBLIC_N=int.from_bytes(_decode(PUBLIC_N_B64),'big')


def verify_token(token,installation_id,today=None):
    try:
        encoded,signature_text=token.strip().split('.')
        payload_bytes=_decode(encoded)
        signature=_decode(signature_text)
        size=(PUBLIC_N.bit_length()+7)//8
        if len(signature)!=size:return None
        decoded=pow(int.from_bytes(signature,'big'),PUBLIC_E,PUBLIC_N).to_bytes(size,'big')
        digest=hashlib.sha256(payload_bytes).digest()
        expected=b'\x00\x01'+b'\xff'*(size-len(SHA256_DIGEST_INFO)-len(digest)-3)+b'\x00'+SHA256_DIGEST_INFO+digest
        if not hmac.compare_digest(decoded,expected):return None
        payload=json.loads(payload_bytes)
        if payload.get('product')!=PRODUCT:return None
        if not hmac.compare_digest(str(payload.get('installation_id','')),installation_id):return None
        customer=payload.get('customer')
        if not isinstance(customer,str) or not customer.strip() or len(customer)>160:return None
        expires=payload.get('expires')
        if expires:
            expiry=datetime.strptime(expires,'%Y-%m-%d').date()
            if (today or datetime.now(BERLIN).date())>expiry:return None
        return payload
    except (ValueError,TypeError,KeyError,json.JSONDecodeError):
        return None


class LicenseManager:
    def __init__(self,data_dir):
        self.data_dir=Path(data_dir)
        self.id_file=self.data_dir/'license_installation.json'
        self.license_file=self.data_dir/'license.json'
        self.installation_id=self._load_or_create_id()

    def _atomic_json(self,path,value):
        self.data_dir.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        try:os.chmod(temporary,0o600)
        except OSError:pass
        temporary.replace(path)

    def _load_or_create_id(self):
        try:
            value=json.loads(self.id_file.read_text(encoding='utf-8')).get('installation_id','')
            if len(value)==32 and all(c in '0123456789abcdef' for c in value):return value
        except (OSError,ValueError,AttributeError):pass
        value=secrets.token_hex(16)
        self._atomic_json(self.id_file,{'installation_id':value})
        return value

    def payload(self):
        try:
            record=json.loads(self.license_file.read_text(encoding='utf-8'))
            return verify_token(record.get('token',''),self.installation_id)
        except (OSError,ValueError,AttributeError):return None

    def valid(self):
        return self.payload() is not None

    def activate(self,token):
        payload=verify_token(token,self.installation_id)
        if not payload:return None
        self._atomic_json(self.license_file,{'token':token.strip()})
        return payload


def install_routes(app,manager,page,secrets_module):
    @app.before_request
    def require_activation():
        if request.path=='/activate' or request.path.startswith('/assets/'):
            return None
        if manager.valid():return None
        if request.path.startswith('/api/'):
            return jsonify(ok=False,error='Aktivierung erforderlich'),423
        depth=max(0,len([part for part in request.path.split('/') if part])-1)
        return redirect('../'*depth+'activate')

    @app.route('/activate',methods=['GET','POST'])
    def activate():
        session.setdefault('activation_csrf',secrets_module.token_urlsafe(24))
        error=''
        if request.method=='POST':
            csrf=str(request.form.get('csrf',''))
            if not hmac.compare_digest(csrf,str(session.get('activation_csrf',''))):abort(403)
            payload=manager.activate(request.form.get('license',''))
            if payload:
                session.clear()
                return redirect('./')
            error='Lizenz ungültig, abgelaufen oder für eine andere Installation ausgestellt.'
        return page(ACTIVATION_PAGE,installation_id=manager.installation_id,
            csrf=session['activation_csrf'],error=error)


ACTIVATION_PAGE='''<div class="center"><div class="brand"><img src="assets/logo.png" alt="VantaNet"><h1>VantaNet Maintenance</h1></div><div class="card" style="max-width:620px;margin:35px auto;text-align:left"><h2>Installation aktivieren</h2><p>Diese Installation benötigt eine von VantaNet signierte Lizenz.</p><label>Installations-ID</label><pre id="installation">{{installation_id}}</pre><button type="button" class="secondary" onclick="navigator.clipboard.writeText(document.getElementById('installation').textContent.trim())">ID kopieren</button>{% if error %}<p class="alert">{{error}}</p>{% endif %}<form method="post"><input type="hidden" name="csrf" value="{{csrf}}"><label>Lizenzzeichenfolge</label><textarea name="license" required rows="7" style="width:100%;margin:12px 0;padding:12px;background:#0c1524;color:white;border:1px solid #38506f;border-radius:9px"></textarea><button>Aktivieren</button></form><p class="muted">Die Lizenz ist an diese Installations-ID gebunden. Es wird kein Kennwort im Quellcode gespeichert.</p></div></div>'''
