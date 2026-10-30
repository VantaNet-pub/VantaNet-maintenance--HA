"""Read-only checks. Persist only explicitly selected, non-secret summary fields."""
import os
import time
from pathlib import Path
import requests


def collect():
    report = {'id': os.urandom(12).hex(), 'created': int(time.time()), 'checks': []}
    token = os.environ.get('SUPERVISOR_TOKEN')
    def check(label, path, summarize):
        item = {'area': label, 'source': path}
        if not token:
            item.update(status='nicht verfügbar', detail='Kein Supervisor-Zugriff konfiguriert')
        else:
            try:
                r = requests.get('http://supervisor' + path,
                    headers={'Authorization': 'Bearer ' + token}, timeout=12,
                    allow_redirects=False)
                if r.status_code in (401, 403):
                    item.update(status='nicht berechtigt', detail='API verweigert den Zugriff')
                elif r.status_code != 200:
                    item.update(status='nicht verfügbar', detail='HTTP ' + str(r.status_code))
                else:
                    body = r.json()
                    if isinstance(body, dict) and body.get('result') == 'error':
                        raise ValueError('API error')
                    data = body.get('data', body) if isinstance(body, dict) else body
                    item.update(status='geprüft', detail=summarize(data))
            except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
                item.update(status='nicht verfügbar', detail='Verbindung oder Antwort nicht auswertbar')
        report['checks'].append(item)

    def versions(d):
        parts = []
        for key in ('version', 'version_latest'):
            value = d.get(key)
            # Versions must be version-shaped, never arbitrary API text.
            if isinstance(value, str) and len(value) <= 40 and all(c in '0123456789.abrcdev-_' for c in value):
                parts.append(key + ': ' + value)
        current, latest = d.get('version'), d.get('version_latest')
        if current and latest:
            parts.append('Update verfügbar' if current != latest else 'Versionsstand aktuell laut API')
        if not parts:raise ValueError('No versions')
        return '; '.join(parts)

    check('System / Core', '/core/info', versions)
    def resources(d):
        parts=[]
        for key in ('cpu_percent','memory_usage','memory_limit'):
            value=d.get(key)
            if type(value) in (int,float) and value >= 0:
                parts.append(key+': '+str(round(value,2)))
        if not parts:raise ValueError('No metrics')
        return '; '.join(parts)
    check('System / Ressourcen', '/core/stats', resources)
    check('Updates / Supervisor', '/supervisor/info', versions)
    check('Updates / Betriebssystem', '/os/info', versions)
    def entities(d):
        if not isinstance(d, list):
            raise ValueError('Not a list')
        unavailable = sum(x.get('state') == 'unavailable' for x in d if isinstance(x, dict))
        unknown = sum(x.get('state') == 'unknown' for x in d if isinstance(x, dict))
        updates = sum(str(x.get('entity_id', '')).startswith('update.') and x.get('state') == 'on' for x in d if isinstance(x, dict))
        return f'{len(d)} Entitäten; {unavailable} nicht verfügbar; {unknown} unbekannt; {updates} aktive Update-Hinweise. Entitäten sind keine physische Geräteprüfung.'
    check('Geräte / Entitätszustände', '/core/api/states', entities)
    # Device registry is a separate, read-only WebSocket command.
    item = {'area': 'Geräte / Registry', 'source': '/core/websocket · config/device_registry/list'}
    if not token:
        item.update(status='nicht verfügbar', detail='Kein Supervisor-Zugriff konfiguriert')
    else:
        ws = None
        try:
            import websocket
            import json
            ws = websocket.create_connection('ws://supervisor/core/websocket', timeout=12)
            if json.loads(ws.recv()).get('type') != 'auth_required': raise ValueError()
            ws.send(json.dumps({'type':'auth', 'access_token':token}))
            if json.loads(ws.recv()).get('type') != 'auth_ok':
                item.update(status='nicht berechtigt', detail='WebSocket-Anmeldung verweigert')
            else:
                ws.send(json.dumps({'id':1, 'type':'config/device_registry/list'}))
                reply = json.loads(ws.recv())
                if not reply.get('success'):
                    item.update(status='nicht berechtigt', detail='Registry-Abfrage verweigert oder nicht unterstützt')
                elif not isinstance(reply.get('result'), list): raise ValueError()
                else:
                    devices = reply['result']
                    disabled = sum(bool(d.get('disabled_by')) for d in devices)
                    item.update(status='geprüft', detail=f'{len(devices)} registrierte Geräte; {disabled} deaktiviert. Keine Funktions- oder Erreichbarkeitsgarantie.')
        except Exception:
            item.update(status='nicht verfügbar', detail='Registry-Verbindung oder Antwort nicht auswertbar')
        finally:
            if ws is not None: ws.close()
    report['checks'].append(item)
    # Fixed allowlist: metadata only, no directory traversal, content or secrets.
    root = Path(os.environ.get('VANTANET_CONFIG', '/homeassistant'))
    for name in ('configuration.yaml', 'automations.yaml', 'scripts.yaml', 'scenes.yaml'):
        item = {'area':'Dateiinformationen / ' + name, 'source':'Read-only Konfigurationsfreigabe'}
        try:
            p = root / name
            if p.is_symlink():
                raise PermissionError()
            st = p.stat()
            item.update(status='geprüft', detail=f'{st.st_size} Bytes; geändert: {int(st.st_mtime)} (Unixzeit). Inhalt nicht gelesen oder geprüft.')
        except PermissionError:
            item.update(status='nicht berechtigt', detail='Metadatenzugriff verweigert')
        except OSError:
            item.update(status='nicht verfügbar', detail='Datei fehlt oder Freigabe nicht zugänglich')
        report['checks'].append(item)
    return report
