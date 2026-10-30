"""V1.3 lifecycle, automatic system checks and branded A4 documents."""
import copy
import io
import random
import threading
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from flask import request, session, abort, redirect, Response, send_from_directory
from reports import collect
from pdf_reports import build_check_report, build_handover


def install(g):
    app, state, lock = g['app'], g['state'], g['lock']
    now, save, log, tablet = (g[k] for k in ('now','save','log','tablet'))
    require, csrf_ok, stamp = (g[k] for k in ('require','csrf_ok','stamp'))
    state.setdefault('reports', [])
    state['reports'] = state['reports'][-3:]
    state.setdefault('reminder_enabled', True)
    state.setdefault('technician', {})
    state.setdefault('last_maintenance', None)
    save(state)
    busy = threading.Lock()
    original_tick, original_index = g['tick'], g['index']

    def maintenance_report(s, maintenance_id):
        for report in reversed(s.get('reports', [])):
            if (report.get('maintenance') or {}).get('id') == maintenance_id:
                return report
        return None

    def run_report(maintenance):
        try:
            report=collect()
            report['maintenance']=copy.deepcopy(maintenance)
            with lock:
                state['reports']=(state['reports']+[report])[-3:]
                log(state,'Home-Assistant-Prüfung abgeschlossen')
                save(state)
        finally:
            busy.release()

    def finish_locked(at):
        if state['mode'] != 'upload': return False
        state['last_maintenance'] = {'id':state.get('maintenance_id'),
            'started':state['started'], 'finished':at,
            'planned_seconds':state['duration'], 'technician':copy.deepcopy(state['technician'])}
        due = state['due'] if state.get('due_manual') and state['due'] > at else g['six_months'](at)
        state['due_manual'] = False
        state.update(mode='home', finished=at, due=due, started=None,
            ack_until=0, phase='upload', phase_until=0, next_reboot=0, reminder_enabled=True)
        state['stats']['completed'] += 1
        log(state, 'Wartung abgeschlossen')
        save(state)
        return True

    def action_finish():
        with lock:
            changed = finish_locked(now())
            s = copy.deepcopy(state)
        return tablet('home', s) if changed else []

    def tick():
        finished=None
        with lock:
            if state['mode'] == 'upload' and now() >= state['started'] + state['duration']:
                finish_locked(state['started'] + state['duration'])
                finished=('home', copy.deepcopy(state))
            if state['mode'] != 'upload' and not state['reminder_enabled']:
                return None
        if finished:return finished
        return original_tick()
    g.update(tick=tick, action_finish=action_finish)

    def index():
        if not g['authenticated'](): return original_index()
        with lock: s = copy.deepcopy(state)
        session.setdefault('csrf', g['secrets'].token_urlsafe(24))
        return g['page'](DASHBOARD, s=s, csrf=session['csrf'], stamp=stamp,
            active=s['mode']=='upload', pct=g['progress'](s),
            due_input=datetime.fromtimestamp(s['due'],g['BERLIN']).strftime('%Y-%m-%dT%H:%M'),
            location=g['opts'].get('site_location',''), message=request.args.get('message',''),
            reporting=busy.locked())
    app.view_functions['index'] = index

    def action(name):
        require()
        if not csrf_ok(): abort(403)
        report_snapshot=None
        with lock:
            if name in ('start','show_notice') and state['mode']=='upload': abort(409)
            if name == 'start':
                tech = {k:request.form.get(k,'').strip() for k in ('name','company','location')}
                if any(not v or len(v)>160 for v in tech.values()): abort(400)
                mode = request.form.get('duration_mode')
                if mode == 'auto': minutes=random.randint(80,120)
                elif mode == 'quick': minutes=random.randint(20,60)
                elif mode == 'manual':
                    try: minutes=int(request.form.get('minutes',''))
                    except ValueError: abort(400)
                    if not 1 <= minutes <= 1440: abort(400)
                else: abort(400)
                if not busy.acquire(blocking=False): abort(409)
                maintenance_id=g['secrets'].token_hex(8)
                state.update(mode='upload',started=now(),duration=minutes*60,technician=tech,
                    maintenance_id=maintenance_id,phase='upload',phase_until=0,last_reboot=now(),ack_until=0)
                g['schedule_reboot'](state)
                state['stats']['started'] += 1
                log(state,'Wartung gestartet; Home-Assistant-Prüfung läuft')
                report_snapshot={'id':maintenance_id,'started':state['started'],
                    'planned_seconds':state['duration'],'technician':copy.deepcopy(tech)}
                save(state); s=copy.deepcopy(state); target='upload'
            elif name == 'finish':
                changed=finish_locked(now());s=copy.deepcopy(state);target='home' if changed else None
            elif name == 'show_notice':
                state.update(mode='notice',ack_until=0,reminder_enabled=True)
                log(state,'Hinweis manuell geöffnet');save(state);s=copy.deepcopy(state);target='notice'
            elif name == 'reboot':
                if state['mode']!='upload' or state['phase']!='upload': abort(409)
                g['begin_sfrp'](state,'SFRP manuell gestartet');target=None
            elif name == 'reset_stats':
                state['stats']={k:0 for k in state['stats']};save(state);target=None
            elif name == 'reset_events':
                state['events']=[];save(state);target=None
            elif name == 'set_due':
                try:
                    text=request.form.get('due','')
                    value=datetime.fromisoformat(text).replace(tzinfo=g['BERLIN'])
                    ts=int(value.timestamp())
                    if ts <= now(): abort(400)
                except (ValueError,OverflowError,OSError): abort(400)
                state.update(due=ts,due_manual=True,reminder_enabled=True,ack_until=0)
                target=None
                if state['mode']=='notice':state['mode']='home';target='home'
                log(state,'Nächster Wartungstermin manuell festgelegt');save(state);s=copy.deepcopy(state)
            elif name in ('disable_reminder','delete_reminder','enable_reminder'):
                enabled=name=='enable_reminder'
                state['reminder_enabled']=enabled
                if name=='delete_reminder':state['ack_until']=0
                target=None
                if not enabled and state['mode']=='notice':state['mode']='home';target='home'
                log(state,'Erinnerung aktiviert' if enabled else 'Erinnerung deaktiviert / gelöscht')
                save(state);s=copy.deepcopy(state)
            else:abort(404)
        if report_snapshot:
            threading.Thread(target=run_report,args=(report_snapshot,),daemon=True).start()
        if target: tablet(target,s)
        return redirect('../')
    app.view_functions['action']=action

    @app.get('/assets/<path:name>')
    def assets(name):
        if name != 'logo.png': abort(404)
        return send_from_directory(Path(__file__).parent/'assets',name)
    @app.get('/handover.pdf')
    def handover():
        require()
        with lock:s=copy.deepcopy(state)
        record=s['last_maintenance']
        if not record: abort(409)
        logo=Path(__file__).parent/'assets/logo.png'
        report=maintenance_report(s,record.get('id'))
        data=build_handover(s,record,report,stamp,logo)
        return Response(data,mimetype='application/pdf',headers={'Content-Disposition':'attachment; filename="VantaNet-Wartungsuebergabe.pdf"'})

    @app.get('/report/<report_id>.pdf')
    def report_pdf(report_id):
        require()
        with lock:
            report=next((copy.deepcopy(r) for r in state.get('reports',[]) if r.get('id')==report_id),None)
        if not report:abort(404)
        data=build_check_report(report,stamp,Path(__file__).parent/'assets/logo.png')
        return Response(data,mimetype='application/pdf',headers={'Content-Disposition':'attachment; filename="VantaNet-Pruefbericht.pdf"'})

    def status_v130():
        g['display_auth']()
        with lock:
            s=copy.deepcopy(state)
            report=maintenance_report(s,s.get('maintenance_id'))
        return g['jsonify'](mode=s['mode'],phase=s['phase'],progress=g['progress'](s),
            remaining_minutes=max(0,(s['duration']-(now()-s['started']))//60) if s.get('started') else 0,
            due=s['due'],ack_until=s['ack_until'],reporting=busy.locked(),
            checks=(report or {}).get('checks',[]))
    app.view_functions['status']=status_v130

    def display_v130(mode):
        g['display_auth']()
        if mode not in ('notice','upload'):abort(404)
        if mode=='notice':return g['display'].__wrapped__(mode) if hasattr(g['display'],'__wrapped__') else original_display(mode)
        return g['page'](MAINTENANCE_DISPLAY,dashboard_url=g['HA']+g['DASH'])
    original_display=g['display']
    app.view_functions['display']=display_v130


DASHBOARD = '''
<div class="brand"><img src="{{logo}}" alt="VantaNet"><div><h1>VantaNet Maintenance</h1><p>V1.3.4 · Fachkraft-Verwaltung</p></div></div>
{% macro form(action,label,disabled=false) %}<form method="post" action="action/{{action}}"><input type="hidden" name="csrf" value="{{csrf}}"><button {% if disabled %}disabled{% endif %}>{{label}}</button></form>{% endmacro %}
<style>button:disabled{opacity:.4;cursor:not-allowed}dialog{background:#121d2d;color:#eaf0fc;border:1px solid #38506f;border-radius:16px;max-width:780px;width:94%}dialog::backdrop{background:#000b}select{padding:12px;width:100%;background:#0c1524;color:white}label{display:block}article{border-top:1px solid #38506f;padding:12px 0}.eye{background:transparent;font-size:22px;padding:4px 10px}.event-list{max-height:60vh;overflow:auto}.event{display:grid;grid-template-columns:145px 1fr;gap:12px;padding:10px 0;border-bottom:1px solid #263751}.report-head{display:flex;justify-content:space-between;align-items:center;gap:12px}.status-ok{color:#55d89d}.status-note{color:#ffbd74}@media(max-width:600px){.event{grid-template-columns:1fr}}</style>
<div class="grid"><div class="stat">Status<b>{{s.mode|upper}}</b></div><div class="stat">Nächste Wartung<b>{{stamp(s.due)}}</b></div><div class="stat">Abgeschlossen<b>{{s.stats.completed}}</b></div><div class="stat">SFRP-Zyklen<b>{{s.stats.reboots}}</b></div></div>
<div class="card"><h2>Wartungssteuerung</h2><p>{{message}}</p><p>Wartungsfortschritt: {{pct}} %</p><progress value="{{pct}}" max="100"></progress>
{% if active %}<p>Beginn {{stamp(s.started)}} · Automatischer Abschluss {{stamp(s.started+s.duration)}}</p>{% endif %}
<div class="actions"><button onclick="document.getElementById('start').showModal()" {% if active or reporting %}disabled{% endif %}>Wartung starten</button>{{form('finish','Wartung abschließen',not active)}}{{form('show_notice','Wartungshinweis anzeigen',active)}}{{form('reboot','SFRP starten',not active)}}</div>
<p>{% if reporting %}Home-Assistant-Systemprüfung läuft automatisch …{% elif active and s.reports %}Systemprüfung abgeschlossen.{% else %}Die Home-Assistant-Systemprüfung startet automatisch mit jeder Wartung.{% endif %} SFRP startet während der Wartung zufällig alle 15–20 Minuten.</p>
{% for r in s.reports|reverse %}{% if loop.first %}<article><div class="report-head"><h3>Letzter Prüfstand · {{stamp(r.created)}}</h3><a class="btn" href="report/{{r.id}}.pdf">Prüfbericht A4</a></div>{% for c in r.checks %}<p><b>{{c.area}}</b> · <span class="{{'status-ok' if c.status=='geprüft' else 'status-note'}}">{{c.status}}</span><br><small>{{c.detail}}</small></p>{% endfor %}</article>{% endif %}{% endfor %}</div>
<dialog id="start"><h2>Wartung starten</h2><form method="post" action="action/start"><input type="hidden" name="csrf" value="{{csrf}}"><label>Fachkraft<input name="name" maxlength="160" required></label><label>Unternehmen<input name="company" maxlength="160" required></label><label>Standort<input name="location" value="{{location}}" maxlength="160" required></label><label>Dauer<select name="duration_mode"><option value="auto">Automatisch · 80–120 Minuten</option><option value="quick">Schnell · 20–60 Minuten</option><option value="manual">Manuell</option></select></label><label>Manuelle Minuten (1–1440)<input type="number" name="minutes" min="1" max="1440" value="90"></label><button>Jetzt starten</button><button type="button" class="secondary" onclick="this.closest('dialog').close()">Abbrechen</button></form></dialog>
<div class="card"><h2>Termin und Erinnerung</h2><p>Nächster Termin: {{stamp(s.due)}} · Erinnerung {{'aktiv' if s.reminder_enabled else 'deaktiviert'}}</p><p>24-Stunden-Erinnerung: {{stamp(s.ack_until) if s.ack_until else 'nicht vorgemerkt'}}</p><form method="post" action="action/set_due"><input type="hidden" name="csrf" value="{{csrf}}"><label>Nächster Termin (lokale Anlagenzeit)<input type="datetime-local" name="due" value="{{due_input}}" required></label><button>Termin speichern / Erinnerung aktivieren</button></form><div class="actions">{{form('delete_reminder','Erinnerung löschen')}}{{form('disable_reminder','Erinnerung deaktivieren')}}{{form('enable_reminder','Erinnerung aktivieren')}}</div></div>
<div class="card"><div class="report-head"><h2>Statistiken und Ereignisse</h2><button class="eye" title="Alle Ereignisse anzeigen" aria-label="Alle Ereignisse anzeigen" onclick="document.getElementById('events').showModal()">👁️</button></div><p>Gestartet: {{s.stats.started}} · Abgeschlossen: {{s.stats.completed}} · 24-h-Bestätigungen: {{s.stats.acknowledged}}</p><pre>{% for e in s.events[-3:]|reverse %}{{stamp(e.at)}} {{e.text}}\n{% endfor %}</pre><div class="actions">{{form('reset_stats','Statistiken zurücksetzen')}}{{form('reset_events','Ereignisse zurücksetzen')}}{% if s.last_maintenance %}<a class="btn" href="handover.pdf">Wartungsübergabe A4</a>{% endif %}</div></div>
<dialog id="events"><div class="report-head"><h2>Alle Ereignisse</h2><button class="secondary" onclick="this.closest('dialog').close()">Schließen</button></div><div class="event-list">{% for e in s.events|reverse %}<div class="event"><small>{{stamp(e.at)}}</small><span>{{e.text}}</span></div>{% else %}<p>Keine Ereignisse vorhanden.</p>{% endfor %}</div></dialog>
<form method="post" action="logout"><input type="hidden" name="csrf" value="{{csrf}}"><button class="secondary">Abmelden</button></form>
<script>setInterval(()=>{if(!document.querySelector('dialog[open]')&&!document.querySelector('input:focus')&&!document.querySelector('select:focus'))location.reload()},15000)</script>
'''

MAINTENANCE_DISPLAY='''<div class="brand"><img src="{{logo}}" alt="VantaNet"><div><h1>Systemwartung</h1><p>VantaNet · Home Assistant</p></div></div><div class="card"><h2 id="phase">Systemprüfung wird vorbereitet</h2><p id="sub">Home Assistant wird geprüft</p><progress id="bar" max="100" value="0"></progress><p><span id="pct">0 %</span> · Restzeit <span id="eta">—</span></p><div id="checks"></div><p class="muted">Display eingeschaltet lassen. Die Wartung wird nach Ablauf automatisch abgeschlossen.</p></div><script>async function refresh(){try{const r=await fetch(location.pathname.replace('/display/upload','/api/status')+location.search,{cache:'no-store'});const s=await r.json();if(s.mode==='home'){window.location.replace({{dashboard_url|tojson}});return}document.getElementById('bar').value=s.progress;document.getElementById('pct').textContent=s.progress+' %';document.getElementById('eta').textContent=s.remaining_minutes+' Minuten';document.getElementById('phase').textContent=s.reporting?'Home-Assistant-Systemprüfung läuft':'Wartung läuft';document.getElementById('sub').textContent=s.reporting?'System, Updates, Geräte und Dateiinformationen werden geprüft':'Systemprüfung abgeschlossen';document.getElementById('checks').innerHTML=(s.checks||[]).slice(0,6).map(c=>'<p><b>'+safe(c.area)+'</b> · '+safe(c.status)+'<br><small>'+safe(c.detail)+'</small></p>').join('')}catch(e){document.getElementById('sub').textContent='Statusverbindung unterbrochen'}}function safe(v){const e=document.createElement('span');e.textContent=String(v||'');return e.innerHTML}refresh();setInterval(refresh,4000)</script>'''
