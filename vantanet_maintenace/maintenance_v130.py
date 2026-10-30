"""V1.3 lifecycle, authenticated controls, read-only reports and A4 handover."""
import copy
import io
import random
import threading
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from flask import request, session, abort, redirect, Response, send_from_directory
from reports import collect


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

    def finish_locked(at):
        if state['mode'] != 'upload': return False
        state['last_maintenance'] = {'started':state['started'], 'finished':at,
            'planned_seconds':state['duration'], 'technician':copy.deepcopy(state['technician'])}
        due = state['due'] if state.get('due_manual') and state['due'] > at else g['six_months'](at)
        state['due_manual'] = False
        state.update(mode='home', finished=at, due=due, started=None,
            ack_until=0, phase='upload', phase_until=0, next_reboot=0, reminder_enabled=True)
        state['stats']['completed'] += 1
        log(state, 'Wartung abgeschlossen (keine Bestätigung technischer Fehlerfreiheit)')
        save(state)
        return True

    def action_finish():
        with lock:
            changed = finish_locked(now())
            s = copy.deepcopy(state)
        return tablet('home', s) if changed else []

    def tick():
        with lock:
            if state['mode'] == 'upload' and now() >= state['started'] + state['duration']:
                finish_locked(state['started'] + state['duration'])
                return ('home', copy.deepcopy(state))
            if state['mode'] != 'upload' and not state['reminder_enabled']:
                return None
        return original_tick()
    g.update(tick=tick, action_finish=action_finish)

    def index():
        if not g['authenticated'](): return original_index()
        with lock: s = copy.deepcopy(state)
        session.setdefault('csrf', g['secrets'].token_urlsafe(24))
        return g['page'](DASHBOARD, s=s, csrf=session['csrf'], stamp=stamp,
            active=s['mode']=='upload', pct=g['progress'](s),
            due_input=datetime.fromtimestamp(s['due']).astimezone().strftime('%Y-%m-%dT%H:%M'),
            location=g['opts'].get('site_location',''), message=request.args.get('message',''),
            reporting=busy.locked())
    app.view_functions['index'] = index

    def action(name):
        require()
        if not csrf_ok(): abort(403)
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
                state.update(mode='upload',started=now(),duration=minutes*60,technician=tech,
                    phase='upload',phase_until=0,last_reboot=now(),ack_until=0)
                g['schedule_reboot'](state)
                state['stats']['started'] += 1
                log(state,'Wartung gestartet; visuelle Simulation separat von Prüfberichten')
                save(state); s=copy.deepcopy(state); target='upload'
            elif name == 'finish':
                changed=finish_locked(now());s=copy.deepcopy(state);target='home' if changed else None
            elif name == 'show_notice':
                state.update(mode='notice',ack_until=0,reminder_enabled=True)
                log(state,'Hinweis manuell geöffnet');save(state);s=copy.deepcopy(state);target='notice'
            elif name == 'reboot':
                if state['mode']!='upload' or state['phase']!='upload': abort(409)
                g['begin_visual_reboot'](state,'SFRP: visueller Neustart erzwungen');target=None
            elif name == 'reset_stats':
                state['stats']={k:0 for k in state['stats']};save(state);target=None
            elif name == 'reset_events':
                state['events']=[];save(state);target=None
            elif name == 'set_due':
                try:
                    text=request.form.get('due','')
                    value=datetime.fromisoformat(text)
                    ts=int(value.astimezone().timestamp())
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
            elif name == 'report':
                if not busy.acquire(blocking=False):abort(409)
                def run_report():
                    try:
                        report=collect()
                        with lock:
                            report['maintenance']=copy.deepcopy(state.get('last_maintenance'))
                            state['reports']=(state['reports']+[report])[-3:]
                            log(state,'Realer Prüfbericht erstellt; Einschränkungen im Bericht beachten');save(state)
                    finally:busy.release()
                threading.Thread(target=run_report,daemon=True).start();target=None
            else:abort(404)
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
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether
        with lock:s=copy.deepcopy(state)
        record=s['last_maintenance']
        if not record: abort(409)
        out=io.BytesIO();styles=getSampleStyleSheet();story=[]
        logo=Path(__file__).parent/'assets/logo.png'
        if logo.exists():
            image=Image(str(logo));image._restrictSize(52*mm,22*mm);story.extend([image,Spacer(1,8*mm)])
        def paragraph(text,style='BodyText'):
            story.append(Paragraph(escape(str(text)),styles[style]));story.append(Spacer(1,3*mm))
        paragraph('VantaNet - Wartungsübergabe','Title')
        tech=record['technician']
        for label,value in [('Standort',tech.get('location','')),('Fachkraft',tech.get('name','')),
            ('Unternehmen',tech.get('company','')),('Beginn',stamp(record['started'])),
            ('Abschluss',stamp(record['finished'])),('Dauer',str(round((record['finished']-record['started'])/60,1))+' Minuten'),
            ('Geplant',str(record['planned_seconds']//60)+' Minuten'),('Nächster Termin',stamp(s['due']))]:
            paragraph(label+': '+value)
        paragraph('Zeitzone: '+datetime.fromtimestamp(record['started']).astimezone().strftime('%Z (UTC%z)'),'BodyText')
        paragraph('Prüfstatus und Grenzen','Heading2')
        paragraph('Bildschirmabläufe und SFRP sind visuelle Simulationen. Es wurden dadurch keine Updates, Uploads, Löschungen oder Systemneustarts durchgeführt. Ein Zeitablauf bestätigt keine technische Fehlerfreiheit.')
        if s['reports']:
            r=s['reports'][-1]
            paragraph('Letzter unabhängiger Prüfstand: '+stamp(r['created']))
            for c in r['checks']:
                group_start=len(story)
                paragraph(c['area']+' - '+c['status'],'Heading3')
                paragraph(c['detail'])
                story[group_start:]=[KeepTogether(story[group_start:])]
        else:paragraph('Kein realer Prüfbericht vorhanden.')
        paragraph('Übergabe / Unterschrift Fachkraft: __________________________')
        paragraph('Übernahme / Unterschrift: __________________________________')
        def footer(canvas,doc):
            canvas.setFillColor(colors.HexColor('#35557b'));canvas.setFont('Helvetica',9)
            canvas.drawString(18*mm,12*mm,'VantaNet Maintenance V1.3.0');canvas.drawRightString(192*mm,12*mm,str(doc.page))
        SimpleDocTemplate(out,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,
            topMargin=16*mm,bottomMargin=20*mm).build(story,onFirstPage=footer,onLaterPages=footer)
        return Response(out.getvalue(),mimetype='application/pdf',headers={'Content-Disposition':'attachment; filename="VantaNet-Wartungsuebergabe.pdf"'})


DASHBOARD = '''
<div class="brand"><img src="{{logo}}" alt="VantaNet"><div><h1>VantaNet Maintenance</h1><p>V1.3.0 · Fachkraft-Verwaltung</p></div></div>
{% macro form(action,label,disabled=false) %}<form method="post" action="action/{{action}}"><input type="hidden" name="csrf" value="{{csrf}}"><button {% if disabled %}disabled{% endif %}>{{label}}</button></form>{% endmacro %}
<style>button:disabled{opacity:.4;cursor:not-allowed}dialog{background:#121d2d;color:#eaf0fc;border:1px solid #38506f;border-radius:16px;max-width:560px;width:94%}dialog::backdrop{background:#000b}select{padding:12px;width:100%;background:#0c1524;color:white}label{display:block}article{border-top:1px solid #38506f;padding:12px 0}</style>
<div class="grid"><div class="stat">Status<b>{{s.mode|upper}}</b></div><div class="stat">Nächste Wartung<b>{{stamp(s.due)}}</b></div><div class="stat">Abgeschlossen<b>{{s.stats.completed}}</b></div><div class="stat">Visuelle Neustarts<b>{{s.stats.reboots}}</b></div></div>
<div class="card"><h2>Wartungssteuerung</h2><p>{{message}}</p><p>Visuelle Simulation: {{pct}} % · Phase {{s.phase}}</p><progress value="{{pct}}" max="100"></progress>
{% if active %}<p>Beginn {{stamp(s.started)}} · Automatischer Abschluss {{stamp(s.started+s.duration)}}</p>{% endif %}
<div class="actions"><button onclick="document.getElementById('start').showModal()" {% if active %}disabled{% endif %}>Wartung starten</button>{{form('finish','Wartung abschließen',not active)}}{{form('show_notice','Wartungshinweis anzeigen',active)}}{{form('reboot','SFRP · Bildschirm-Neustart',not active)}}</div>
<p>Alle Bildschirmabläufe sind Simulationen. SFRP startet automatisch zufällig alle 15–20 Minuten. Reale Prüfungen stehen separat unten.</p></div>
<dialog id="start"><h2>Wartung starten</h2><form method="post" action="action/start"><input type="hidden" name="csrf" value="{{csrf}}"><label>Fachkraft<input name="name" maxlength="160" required></label><label>Unternehmen<input name="company" maxlength="160" required></label><label>Standort<input name="location" value="{{location}}" maxlength="160" required></label><label>Dauer<select name="duration_mode"><option value="auto">Automatisch · 80–120 Minuten</option><option value="quick">Schnell · 20–60 Minuten</option><option value="manual">Manuell</option></select></label><label>Manuelle Minuten (1–1440)<input type="number" name="minutes" min="1" max="1440" value="90"></label><button>Jetzt starten</button><button type="button" class="secondary" onclick="this.closest('dialog').close()">Abbrechen</button></form></dialog>
<div class="card"><h2>Termin und Erinnerung</h2><p>Nächster Termin: {{stamp(s.due)}} · Erinnerung {{'aktiv' if s.reminder_enabled else 'deaktiviert'}}</p><p>24-Stunden-Erinnerung: {{stamp(s.ack_until) if s.ack_until else 'nicht vorgemerkt'}}</p><form method="post" action="action/set_due"><input type="hidden" name="csrf" value="{{csrf}}"><label>Nächster Termin (lokale Anlagenzeit)<input type="datetime-local" name="due" value="{{due_input}}" required></label><button>Termin speichern / Erinnerung aktivieren</button></form><div class="actions">{{form('delete_reminder','Erinnerung löschen')}}{{form('disable_reminder','Erinnerung deaktivieren')}}{{form('enable_reminder','Erinnerung aktivieren')}}</div></div>
<div class="card"><h2>Statistiken und Ereignisse</h2><p>Gestartet: {{s.stats.started}} · 24-h-Bestätigungen: {{s.stats.acknowledged}}</p><pre>{% for e in s.events[-3:]|reverse %}{{stamp(e.at)}} {{e.text}}\n{% endfor %}</pre><div class="actions">{{form('reset_stats','Statistiken zurücksetzen')}}{{form('reset_events','Ereignisse zurücksetzen')}}</div></div>
<div class="card"><h2>Reale Home-Assistant-Prüfberichte</h2><p>Nur lesende Abfragen. Fehlende Rechte und nicht verfügbare Daten werden ausgewiesen. Maximal drei gespeicherte Prüfstände. Keine Zugangsdaten oder Dateiinhalte.</p>{{form('report','Prüfung läuft …' if reporting else 'Jetzt real prüfen',reporting)}}
{% for r in s.reports|reverse %}<article><h3>Prüfstand {{stamp(r.created)}}</h3>{% for c in r.checks %}<p><b>{{c.area}} · {{c.status}}</b><br>{{c.detail}}<br><small>Quelle: {{c.source}}</small></p>{% endfor %}</article>{% endfor %}
{% if s.last_maintenance %}<a class="btn" href="handover.pdf">A4-PDF zur Wartungsübergabe</a>{% endif %}</div>
<form method="post" action="logout"><input type="hidden" name="csrf" value="{{csrf}}"><button class="secondary">Abmelden</button></form>
<script>setInterval(()=>{if(!document.querySelector('dialog[open]')&&!document.querySelector('input:focus')&&!document.querySelector('select:focus'))location.reload()},15000)</script>
'''
