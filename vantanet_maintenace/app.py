import os, json, time, secrets, hashlib, hmac, threading, random, calendar, logging
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from pathlib import Path
import requests
from flask import Flask, request, redirect, session, jsonify, Response, render_template_string, abort

logging.basicConfig(level=logging.INFO)
app=Flask(__name__)
app.secret_key=secrets.token_bytes(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(hours=2))
DATA=Path('/data/maintenance.json')
OPTIONS=Path('/data/options.json')
lock=threading.RLock()
opts=json.loads(OPTIONS.read_text()) if OPTIONS.exists() else {}
# Fachkraft-PIN wird einmalig erzeugt und als gesalzener Hash gespeichert.
# Kein PIN in der App-Konfiguration oder im Repository.
PIN_FILE=Path('/data/technician_pin.json')
def setup_pin():
    PIN_FILE.parent.mkdir(parents=True,exist_ok=True)
    if PIN_FILE.exists():
        return json.loads(PIN_FILE.read_text())
    pin=''.join(str(secrets.randbelow(10)) for _ in range(10))
    salt=secrets.token_bytes(16)
    rounds=310000
    digest=hashlib.pbkdf2_hmac('sha256',pin.encode(),salt,rounds)
    record={'salt':salt.hex(),'rounds':rounds,'digest':digest.hex()}
    fd=os.open(str(PIN_FILE),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(record,f)
    logging.warning('EINMALIGER FACHKRAFT-PIN: %s — jetzt sicher notieren; wird nicht erneut angezeigt!',pin)
    return record
PIN_RECORD=setup_pin()
def valid_pin(candidate):
    salt=bytes.fromhex(PIN_RECORD['salt'])
    digest=hashlib.pbkdf2_hmac('sha256',str(candidate).encode(),salt,int(PIN_RECORD['rounds']))
    return hmac.compare_digest(digest,bytes.fromhex(PIN_RECORD['digest']))
KIOSK=str(opts.get('kiosk_password',''))
IPS=opts.get('tablet_ips',[])
HA=opts.get('home_assistant_url','http://192.168.4.2:8123').rstrip('/')
DASH=opts.get('dashboard_path','/home-db/0?hide_sidebar')
BASE=opts.get('public_base_url','http://192.168.4.2:8765').rstrip('/')
LOGO='https://vantanet.net/assets/files/VantaNet-Logo-alone.png'
now=lambda: int(time.time())
def six_months(ts):
    d=datetime.fromtimestamp(ts).astimezone()
    y=d.year+(d.month-1+6)//12; m=(d.month-1+6)%12+1
    day=min(d.day,calendar.monthrange(y,m)[1])
    return int(d.replace(year=y,month=m,day=day).timestamp())
def initial():
    due=now()
    try:
        if opts.get('first_maintenance_due'):
            due=int(datetime.fromisoformat(opts['first_maintenance_due']).astimezone().timestamp())
    except ValueError: logging.warning('Invalid first_maintenance_due; due immediately')
    return {'mode':'notice','due':due,'started':None,'finished':None,'duration':random.randint(40,120)*60,'ack_until':0,'last_reboot':0,'phase_until':0,'phase':'upload','events':[],'stats':{'completed':0,'started':0,'acknowledged':0,'reboots':0},'token':secrets.token_urlsafe(24)}
def load():
    if DATA.exists():
        try:
            s=json.loads(DATA.read_text());return s
        except (ValueError,OSError):logging.exception('State read failed')
    s=initial();save(s);return s
def save(s):
    DATA.parent.mkdir(parents=True,exist_ok=True)
    p=DATA.with_suffix('.tmp');p.write_text(json.dumps(s,ensure_ascii=False,indent=2));p.replace(DATA)
def log(s,msg):
    s['events']=(s.get('events',[])+[{'at':now(),'text':msg}])[-100:]
with lock: state=load()
def authenticated():return bool(session.get('tech'))
def require():
    if not authenticated():abort(403)
def csrf_ok():return bool(session.get('csrf')) and hmac.compare_digest(str(request.form.get('csrf','')),session['csrf'])
def stamp(ts):return datetime.fromtimestamp(ts).astimezone().strftime('%d.%m.%Y %H:%M') if ts else '—'
def progress(s):return min(100,round((now()-s['started'])/s['duration']*100,1)) if s.get('started') else 0
def url_for_mode(s,mode):
    return f"{BASE}/display/{mode}?token={quote(s['token'])}"
def tablet(mode,s):
    target=url_for_mode(s,mode) if mode in ('notice','upload') else HA+DASH
    results=[]
    for ip in IPS:
        try:
            r=requests.get(f'http://{ip}:2323/',params={'cmd':'loadUrl','password':KIOSK,'url':target},timeout=4)
            results.append({'tablet':ip,'ok':r.ok,'status':r.status_code})
        except requests.RequestException as e:results.append({'tablet':ip,'ok':False,'error':str(e)[:140]})
    return results
def action_start():
    with lock:
        if state['mode']=='upload':return []
        state.update(mode='upload',started=now(),duration=random.randint(40,120)*60,phase='upload',phase_until=0,last_reboot=now(),ack_until=0)
        state['stats']['started']+=1;log(state,'Wartung gestartet');save(state);s=state.copy()
    return tablet('upload',s)
def action_finish():
    with lock:
        state.update(mode='home',finished=now(),due=six_months(now()),started=None,ack_until=0,phase='upload',phase_until=0)
        state['stats']['completed']+=1;log(state,'Wartung abgeschlossen');save(state);s=state.copy()
    return tablet('home',s)
def tick():
    with lock:
        t=now();s=state
        if s['mode']=='upload':
            if s['phase']!='upload' and t>=s['phase_until']:
                nxt={'shutdown':('update',60),'update':('startup',30),'startup':('upload',0)}[s['phase']]
                s['phase']=nxt;s['phase_until']=t+({'update':60,'startup':30}.get(nxt,0));log(s,'Phase: '+nxt);save(s)
            elif s['phase']=='upload' and t-s.get('last_reboot',t)>=900:
                s['phase']='shutdown';s['phase_until']=t+25;s['last_reboot']=t;s['stats']['reboots']+=1;log(s,'Visueller Neustart');save(s)
        elif s['mode']=='home' and t>=s['due']:
            s['mode']='notice';log(s,'Wartung fällig');save(s);return ('notice',s.copy())
        elif s['mode']=='notice' and s.get('ack_until',0) and t>=s['ack_until']:
            s['ack_until']=0;save(s);return ('notice',s.copy())
    return None
def worker():
    while True:
        try:
            todo=tick()
            if todo:tablet(*todo)
        except Exception:logging.exception('Maintenance watcher error')
        time.sleep(5)

CSS='''*{box-sizing:border-box}body{margin:0;background:#090f1b;color:#eaf0fc;font:16px system-ui,Segoe UI,sans-serif}main{max-width:1050px;margin:5vh auto;padding:24px}.brand{display:flex;align-items:center;gap:15px}.brand img{width:54px;height:54px;object-fit:contain}h1{font-size:clamp(24px,4vw,38px);margin:10px 0}h2{font-size:20px}p,small{color:#a5b2c9}.card{background:#121d2d;border:1px solid #263751;border-radius:16px;padding:24px;margin:18px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.stat{background:#17263a;padding:18px;border-radius:12px}.stat b{display:block;font-size:22px;margin-top:8px}button,.btn{border:0;border-radius:10px;background:#2174f5;color:white;padding:13px 18px;font-size:16px;cursor:pointer}button.secondary{background:#273b56}button.danger{background:#ab3a4d}input{width:100%;padding:14px;background:#0c1524;color:white;border:1px solid #38506f;border-radius:9px;margin:12px 0}progress{width:100%;height:20px;accent-color:#2687ff}code,pre{font-family:ui-monospace,monospace;color:#9bc3ff;overflow-wrap:anywhere}pre{white-space:pre-wrap;background:#0a1422;padding:16px;border-radius:10px;max-height:220px;overflow:auto}.muted{color:#9aaac3}.alert{color:#ffbd74}.actions{display:flex;gap:10px;flex-wrap:wrap}.center{text-align:center;padding-top:10vh}.center .brand{justify-content:center}a{color:#80b7ff}'''
BASE_HTML='''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VantaNet Maintenance</title><style>'''+CSS+'''</style></head><body><main>{% block content %}{% endblock %}</main></body></html>'''
def page(content,**ctx):
    return render_template_string(BASE_HTML.replace('{% block content %}{% endblock %}',content),logo=LOGO,**ctx)
@app.after_request
def security_headers(response):
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='SAMEORIGIN'
    return response
@app.route('/',methods=['GET'])
def index():
    if not authenticated():
        return page('''<div class="center"><div class="brand"><img src="{{logo}}" alt="VantaNet"><h1>VantaNet Maintenance</h1></div><div class="card" style="max-width:430px;margin:35px auto"><h2>Fachkraft-Zugang</h2><p>PIN eingeben, um Wartung und Tablets zu verwalten.</p>{% if error %}<p class="alert">{{error}}</p>{% endif %}<form method="post" action="login"><input type="password" name="pin" placeholder="Fachkraft-PIN" required autocomplete="off"><button>Anmelden</button></form></div></div>''',error=request.args.get('error',''))
    with lock:s=json.loads(json.dumps(state))
    if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(24)
    return page('''<div class="brand"><img src="{{logo}}" alt="VantaNet"><div><h1>VantaNet Maintenance</h1><p>Fachkraft-Verwaltung · Halbjährliche Wartung</p></div></div><div class="grid"><div class="stat">Status<b>{{s.mode|upper}}</b></div><div class="stat">Nächste Wartung<b>{{due}}</b></div><div class="stat">Abgeschlossene Wartungen<b>{{s.stats.completed}}</b></div><div class="stat">Visuelle Neustarts<b>{{s.stats.reboots}}</b></div></div><div class="card"><h2>Wartungssteuerung</h2><p>Upload-Fortschritt: {{pct}} % · Restzeit: {{remaining}}</p><progress value="{{pct}}" max="100"></progress><p>Aktuelle Phase: {{s.phase}} · Letzter Abschluss: {{finished}}</p><div class="actions"><form method="post" action="action/start"><input type="hidden" name="csrf" value="{{csrf}}"><button>Wartung starten</button></form><form method="post" action="action/finish" onsubmit="return confirm('Wartung wirklich abschließen?')"><input type="hidden" name="csrf" value="{{csrf}}"><button class="secondary">Wartung abschließen</button></form><form method="post" action="action/show_notice"><input type="hidden" name="csrf" value="{{csrf}}"><button class="secondary">Wartungshinweis anzeigen</button></form><form method="post" action="action/reboot"><input type="hidden" name="csrf" value="{{csrf}}"><button class="danger">SFRP · Bildschirm-Neustart</button></form></div></div><div class="card"><h2>Statistik</h2><p>Wartungen gestartet: {{s.stats.started}} · Bestätigungen (24 h): {{s.stats.acknowledged}}</p><h2>Letzte Ereignisse</h2><pre>{% for e in events %}{{e}}\n{% endfor %}</pre><p class="muted">Upload-/Update-Meldungen sind visuelle Statusmeldungen, keine tatsächlichen Dateioperationen.</p></div><form method="post" action="logout"><input type="hidden" name="csrf" value="{{csrf}}"><button class="secondary">Abmelden</button></form><script>setTimeout(()=>location.reload(),15000)</script>''',s=s,due=stamp(s['due']),finished=stamp(s.get('finished')),pct=progress(s),remaining=(str(max(0,(s['duration']-(now()-s['started']))//60))+' Minuten') if s.get('started') else '—',events=[stamp(e['at'])+'  '+e['text'] for e in s.get('events',[])[-3:]][::-1],csrf=session['csrf'])
failures={}
@app.post('/login')
def login():
    ip=request.remote_addr or 'unknown';ts=now(); attempts=failures.get(ip,[]);attempts=[x for x in attempts if ts-x<900]
    if len(attempts)>=5:return redirect('./?error=Zu+viele+Versuche.+15+Minuten+warten.')
    if valid_pin(request.form.get('pin','')):
        failures.pop(ip,None);session.clear();session['tech']=True;session.permanent=True;session['csrf']=secrets.token_urlsafe(24);return redirect('./')
    attempts.append(ts);failures[ip]=attempts;return redirect('./?error=PIN+ungültig')
@app.post('/logout')
def logout():
    require()
    if not csrf_ok():abort(403)
    session.clear();return redirect('./')
@app.post('/action/<name>')
def action(name):
    require()
    if not csrf_ok():abort(403)
    if name=='start':action_start()
    elif name=='finish':action_finish()
    elif name=='show_notice':
        with lock:state['mode']='notice';state['ack_until']=0;log(state,'Hinweis manuell geöffnet');save(state);s=state.copy()
        tablet('notice',s)
    elif name=='reboot':
        with lock:
            if state['mode']=='upload':state['phase']='shutdown';state['phase_until']=now()+25;state['last_reboot']=now();state['stats']['reboots']+=1;log(state,'SFRP: visueller Neustart');save(state)
    else:abort(404)
    return redirect('../')
def display_auth():
    with lock: token=state['token']
    if not hmac.compare_digest(request.args.get('token',''),token):abort(403)
@app.get('/display/<mode>')
def display(mode):
    display_auth()
    if mode not in ('notice','upload'):abort(404)
    with lock:s=state.copy()
    if mode=='notice':
        return page('''<div class="center"><div class="brand"><img src="{{logo}}" alt="VantaNet"><h1>VantaNet</h1></div><div class="card"><p class="alert">WARTUNG ERFORDERLICH</p><h1>Halbjährliche Wartung fällig</h1><p>Die regelmäßige Wartung Ihrer Home-Assistant-Anlage ist fällig. Bitte eine Fachkraft verständigen.</p><button onclick="ack()">Okay · in 24 Stunden erinnern</button><p id="result"></p></div></div><script>async function ack(){const r=await fetch(location.pathname.replace('/display/notice','/api/ack')+location.search,{method:'POST'});if(r.ok){document.getElementById('result').textContent='Hinweis bestätigt. Dashboard wird geöffnet …';setTimeout(()=>{window.location.replace({{ dashboard_url|tojson }});},1200);}else{document.getElementById('result').textContent='Bestätigung fehlgeschlagen';}}</script>''',dashboard_url=HA+DASH)
    return page('''<div class="brand"><img src="{{logo}}" alt="VantaNet"><div><h1>Systemwartung</h1><p>VantaNet · Datenverarbeitung</p></div></div><div class="card" id="screen"><h2 id="phase">UPLOADING</h2><p id="sub">Systemkomponenten werden verarbeitet</p><progress id="bar" max="100" value="0"></progress><p id="pct">0 %</p><p>Geschätzte Restzeit: <span id="eta">—</span></p><pre id="logs"></pre><p class="muted">Verarbeitung läuft. Bitte Display eingeschaltet lassen.</p></div><script>const paths=['/config/.storage/core.config_entries','/srv/vantanet/modules/cache','/data/backup/index','/var/lib/services/runtime','/config/www/assets','/srv/vantanet/system/registry'];const verbs=['UPLOADING','VERIFYING','SYNCING','DELETING','BACKING UP'];async function refresh(){try{let r=await fetch(location.pathname.replace('/display/upload','/api/status')+location.search,{cache:'no-store'});let s=await r.json();if(s.mode==='home'){window.location.replace({{ dashboard_url|tojson }});return;}let phase=s.phase||'upload';document.getElementById('phase').textContent=({shutdown:'SHUTTING DOWN',update:'SYSTEM UPDATE',startup:'STARTING VANTANET',upload:'UPLOADING'})[phase];document.getElementById('bar').value=s.progress;document.getElementById('pct').textContent=s.progress+' %';document.getElementById('eta').textContent=s.remaining_minutes+' Minuten';document.getElementById('sub').textContent=phase==='startup'?'VantaNet wird gestartet':phase==='shutdown'?'Dienste werden beendet':phase==='update'?'Systemkomponenten werden aktualisiert':'Systemkomponenten werden verarbeitet';if(phase==='startup'){document.getElementById('logs').textContent='VantaNet · INITIALIZING SERVICES';}else if(phase==='upload'){let p=paths[Math.floor(Math.random()*paths.length)];let v=verbs[Math.floor(Math.random()*verbs.length)];let el=document.getElementById('logs');el.textContent=(el.textContent+'\\n'+v+' '+p).trim().split('\\n').slice(-9).join('\\n');}else{document.getElementById('logs').textContent=phase==='shutdown'?'STOPPING SERVICES\\nSAVING STATE': 'CHECKING PACKAGES\\nVERIFYING INTEGRITY';}}catch(e){document.getElementById('sub').textContent='Statusverbindung unterbrochen';}}refresh();setInterval(refresh,4000)</script>''',dashboard_url=HA+DASH)
@app.get('/api/status')
def status():
    display_auth()
    with lock:s=state.copy()
    return jsonify(mode=s['mode'],phase=s['phase'],progress=progress(s),remaining_minutes=max(0,(s['duration']-(now()-s['started']))//60) if s.get('started') else 0,due=s['due'],ack_until=s['ack_until'])
@app.post('/api/ack')
def ack():
    display_auth()
    with lock:
        if state['mode']!='notice':return jsonify(ok=False),409
        state['ack_until']=now()+86400;state['stats']['acknowledged']+=1;log(state,'Hinweis für 24 Stunden bestätigt');save(state);s=state.copy()
    threading.Thread(target=tablet,args=('home',s),daemon=True).start()
    return jsonify(ok=True)
if __name__=='__main__':
    logging.info('Fachkraft-PIN ist fest eingerichtet')
    threading.Thread(target=worker,daemon=True).start()
    app.run(host='0.0.0.0',port=8099,threaded=True)
