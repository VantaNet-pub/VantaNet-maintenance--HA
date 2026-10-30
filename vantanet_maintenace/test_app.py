import os
import tempfile
import unittest
import copy
import json
from unittest.mock import patch, Mock
from pathlib import Path

TEST_DATA=tempfile.TemporaryDirectory()
os.environ['VANTANET_DATA']=TEST_DATA.name
import app as m
import reports


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        m.state.clear();m.state.update(m.initial())
        m.state.update(reports=[],reminder_enabled=True,technician={},last_maintenance=None)
        self.client=m.app.test_client()
        with self.client.session_transaction() as s:s.update(tech=True,csrf='test')
        self.tablets=patch('app.tablet',return_value=[])
        # install closures hold original tablet; IPS=[] ensures no external I/O.
        m.IPS=[]

    def post(self,action,**kw):
        return self.client.post('/action/'+action,data={'csrf':'test',**kw})

    def start(self,mode='manual',minutes='1'):
        return self.post('start',name='Erika Muster',company='VantaNet',location='Berlin',duration_mode=mode,minutes=minutes)

    def test_auth_and_csrf(self):
        self.assertEqual(self.client.post('/action/reset_stats').status_code,403)
        with self.client.session_transaction() as s:s.clear()
        self.assertEqual(self.client.get('/handover.pdf').status_code,403)
        self.assertEqual(self.post('start').status_code,403)

    def test_dashboard_popup_and_visible_logs(self):
        m.state['events']=[{'at':m.now(),'text':f'LOG{i}'} for i in range(6)]
        r=self.client.get('/')
        self.assertEqual(r.status_code,200)
        text=r.get_data(as_text=True)
        self.assertIn('80–120',text);self.assertIn('20–60',text)
        self.assertNotIn('LOG2',text);self.assertIn('LOG3',text)

    def test_duration_modes(self):
        for mode,lo,hi in [('auto',80,120),('quick',20,60),('manual',1,1)]:
            m.state['mode']='home'
            self.assertEqual(self.start(mode).status_code,302)
            self.assertTrue(lo*60<=m.state['duration']<=hi*60)
        m.state['mode']='home'
        self.assertEqual(self.start(minutes='0').status_code,400)
        self.assertEqual(self.start(minutes='NaN').status_code,400)

    def test_active_guards_and_auto_completion(self):
        self.start()
        self.assertEqual(self.start().status_code,409)
        self.assertEqual(self.post('show_notice').status_code,409)
        end=m.state['started']+m.state['duration']
        with patch('app.time.time',return_value=end+1):todo=m.tick()
        self.assertEqual(todo[0],'home');self.assertEqual(m.state['stats']['completed'],1)
        self.assertEqual(m.state['last_maintenance']['finished'],end)
        self.post('finish');self.assertEqual(m.state['stats']['completed'],1)

    def test_reminder(self):
        token=m.state['token']
        r=self.client.post('/api/ack?token='+token)
        self.assertEqual(r.status_code,200)
        self.assertAlmostEqual(r.json['next_reminder'],m.now()+86400,delta=2)
        with patch('app.time.time',return_value=r.json['next_reminder']+1):
            self.assertEqual(m.tick()[0],'notice')
        self.post('disable_reminder')
        self.assertIsNone(m.tick())
        self.assertEqual(m.state['mode'],'home')
        self.post('delete_reminder');self.assertEqual(m.state['ack_until'],0)
        self.post('enable_reminder');self.assertEqual(m.tick()[0],'notice')

    def test_due_and_resets(self):
        future='2090-01-01T12:00'
        self.assertEqual(self.post('set_due',due=future).status_code,302)
        due=m.state['due'];self.start();self.post('finish')
        self.assertEqual(m.state['due'],due)
        self.assertEqual(self.post('set_due',due='bad').status_code,400)
        self.assertEqual(self.post('set_due',due='2000-01-01T00:00').status_code,400)
        self.post('reset_stats');self.assertEqual(sum(m.state['stats'].values()),0)
        self.post('reset_events');self.assertEqual(m.state['events'],[])

    def test_sfrp_intervals(self):
        self.start()
        for _ in range(20):
            m.schedule_reboot(m.state,1000)
            self.assertTrue(1900<=m.state['next_reboot']<=2200)
        m.begin_visual_reboot(m.state,'Test')
        scheduled=m.state['next_reboot']
        self.assertTrue(m.now()+900<=scheduled<=m.now()+1200)
        m.state.update(phase='startup',phase_until=m.now()-1)
        m.tick();self.assertEqual(m.state['next_reboot'],scheduled)

    def test_pdf(self):
        from pypdf import PdfReader
        import io
        self.assertEqual(self.client.get('/handover.pdf').status_code,409)
        self.start();self.post('finish')
        # Include longest ordinary check summaries for pagination QA.
        m.state['reports']=[reports.collect()]
        r=self.client.get('/handover.pdf')
        self.assertEqual(r.status_code,200)
        reader=PdfReader(io.BytesIO(r.data))
        self.assertAlmostEqual(float(reader.pages[0].mediabox.width),595.276,places=2)
        text=''.join(p.extract_text() for p in reader.pages)
        self.assertIn('Erika Muster',text);self.assertIn('Berlin',text)
        self.assertIn('Simulationen',text)
        output=os.environ.get('VANTANET_TEST_PDF')
        if output:Path(output).write_bytes(r.data)

    def test_display_and_token(self):
        self.assertEqual(self.client.get('/api/status?token=wrong').status_code,403)
        r=self.client.get('/display/upload?token='+m.state['token'])
        self.assertIn('VISUELLE SIMULATION',r.get_data(as_text=True))
        self.assertEqual(self.client.get('/assets/logo.png').status_code,200)

    def test_report_retention(self):
        # Deterministic synchronous thread adapter exercises the real route.
        class Immediate:
            def __init__(self,target,**kwargs):self.target=target
            def start(self):self.target()
        with patch('maintenance_v130.threading.Thread',Immediate),patch('maintenance_v130.collect',side_effect=[{'id':str(i),'checks':[],'created':1} for i in range(5)]):
            for _ in range(5):self.assertEqual(self.post('report').status_code,302)
        self.assertEqual([x['id'] for x in m.state['reports']],['2','3','4'])

    def test_state_survives_reload(self):
        self.start()
        saved=m.load()
        self.assertEqual(saved['started'],m.state['started'])
        self.assertEqual(saved['technician']['location'],'Berlin')
        self.assertEqual(saved['duration'],60)

    def test_legacy_state_migration(self):
        # Existing v1.2 state gains defaults without losing counters or PIN.
        import maintenance_v130
        old=m.initial();old['stats']['completed']=9
        fake=dict(m.__dict__)
        from flask import Flask
        fake['app']=Flask('migration');fake['state']=old
        fake['save']=lambda s:None
        fake['index']=lambda:None
        maintenance_v130.install(fake)
        self.assertEqual(old['stats']['completed'],9)
        self.assertEqual(old['reports'],[])
        self.assertTrue(old['reminder_enabled'])


class ReportTests(unittest.TestCase):
    def test_device_and_entity_summary(self):
        ws=Mock()
        ws.recv.side_effect=[json.dumps({'type':'auth_required'}),json.dumps({'type':'auth_ok'}),json.dumps({'success':True,'result':[{'disabled_by':None},{'disabled_by':'user'}]})]
        response=Mock(status_code=200)
        response.json.return_value=[{'entity_id':'update.test','state':'on','attributes':{'password':'SECRET'}},{'entity_id':'sensor.x','state':'unavailable'}]
        with patch.dict(os.environ,{'SUPERVISOR_TOKEN':'TEST'}),patch('reports.requests.get',return_value=response),patch('websocket.create_connection',return_value=ws):r=reports.collect()
        self.assertTrue(any('2 registrierte' in c['detail'] for c in r['checks']))
        self.assertTrue(any('1 nicht verfügbar' in c['detail'] for c in r['checks']))
        self.assertNotIn('SECRET',json.dumps(r));ws.close.assert_called_once()

    def test_malformed_api_and_timeout(self):
        for effect in [ValueError(),reports.requests.Timeout()]:
            with patch.dict(os.environ,{'SUPERVISOR_TOKEN':'TEST'}),patch('reports.requests.get',side_effect=effect),patch('websocket.create_connection',side_effect=OSError()):r=reports.collect()
            self.assertEqual(r['checks'][0]['status'],'nicht verfügbar')

    def test_no_credentials_or_arbitrary_response_data(self):
        secret='SECRET_TEST_DO_NOT_EXPORT'
        response=Mock(status_code=200)
        response.json.return_value={'result':'ok','data':{'version':'2026.10.1','version_latest':'2026.10.2','password':secret,'token':secret}}
        with patch.dict(os.environ,{'SUPERVISOR_TOKEN':secret}),patch('reports.requests.get',return_value=response),patch('websocket.create_connection',side_effect=OSError()):
            report=reports.collect()
        self.assertNotIn(secret,json.dumps(report))
        self.assertIn('Update verfügbar',report['checks'][0]['detail'])

    def test_permission_and_outages(self):
        for status,expected in [(403,'nicht berechtigt'),(401,'nicht berechtigt'),(500,'nicht verfügbar')]:
            with patch.dict(os.environ,{'SUPERVISOR_TOKEN':'test'}),patch('reports.requests.get',return_value=Mock(status_code=status)),patch('websocket.create_connection',side_effect=OSError()):
                self.assertEqual(reports.collect()['checks'][0]['status'],expected)
        with patch.dict(os.environ,{},clear=True):
            r=reports.collect()
            self.assertTrue(all(x['status']!='geprüft' for x in r['checks']))

    def test_file_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'configuration.yaml').write_text('password: SECRET_CONTENT')
            with patch.dict(os.environ,{'VANTANET_CONFIG':tmp,'SUPERVISOR_TOKEN':''}):r=reports.collect()
        text=json.dumps(r)
        self.assertNotIn('SECRET_CONTENT',text)
        self.assertTrue(any(c['status']=='geprüft' and 'Bytes' in c['detail'] for c in r['checks']))


if __name__=='__main__':unittest.main(verbosity=2)
