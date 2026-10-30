"""Branded A4 documents for maintenance handover and system checks."""
import io
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)

NAVY = colors.HexColor('#071A33')
BLUE = colors.HexColor('#2458F5')
CYAN = colors.HexColor('#30B8FF')
INK = colors.HexColor('#142033')
MUTED = colors.HexColor('#65758B')
LINE = colors.HexColor('#DCE5F0')
SOFT = colors.HexColor('#F3F7FC')
GREEN = colors.HexColor('#16875B')
AMBER = colors.HexColor('#B26A00')
RED = colors.HexColor('#B53845')


def _styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('Title', parent=base['Title'], fontName='Helvetica-Bold',
            fontSize=23, leading=28, textColor=NAVY, spaceAfter=4*mm, alignment=TA_LEFT),
        'lead': ParagraphStyle('Lead', parent=base['BodyText'], fontSize=10.5, leading=15,
            textColor=MUTED, spaceAfter=5*mm),
        'h2': ParagraphStyle('H2', parent=base['Heading2'], fontName='Helvetica-Bold',
            fontSize=14, leading=18, textColor=NAVY, spaceBefore=4*mm, spaceAfter=3*mm),
        'body': ParagraphStyle('Body', parent=base['BodyText'], fontSize=9.5, leading=13,
            textColor=INK),
        'small': ParagraphStyle('Small', parent=base['BodyText'], fontSize=8, leading=11,
            textColor=MUTED),
        'label': ParagraphStyle('Label', parent=base['BodyText'], fontName='Helvetica-Bold',
            fontSize=7.5, leading=10, textColor=MUTED, uppercase=True),
        'value': ParagraphStyle('Value', parent=base['BodyText'], fontName='Helvetica-Bold',
            fontSize=10.5, leading=14, textColor=INK),
        'status': ParagraphStyle('Status', parent=base['BodyText'], fontName='Helvetica-Bold',
            fontSize=8, leading=10, textColor=colors.white),
    }


def _p(value, style):
    return Paragraph(escape(str(value)), style)


def _status_color(status):
    value = str(status).lower()
    if value == 'geprüft': return GREEN
    if value == 'nicht berechtigt': return AMBER
    return RED


def _canvas_class(title, subtitle, logo_path):
    class BrandedCanvas(pdfcanvas.Canvas):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self._saved_pages=[]
        def showPage(self):
            self._saved_pages.append(dict(self.__dict__));self._startPage()
        def save(self):
            total=len(self._saved_pages)
            for state in self._saved_pages:
                self.__dict__.update(state);self._draw_brand(total);pdfcanvas.Canvas.showPage(self)
            pdfcanvas.Canvas.save(self)
        def _draw_brand(self,total):
            width, height = A4
            self.saveState()
            self.setFillColor(NAVY)
            self.rect(0, height-32*mm, width, 32*mm, stroke=0, fill=1)
            if logo_path.exists():
                self.setFillColor(colors.white)
                self.roundRect(16*mm, height-25*mm, 25*mm, 17*mm, 3*mm, stroke=0, fill=1)
                self.drawImage(str(logo_path), 20*mm, height-23*mm, width=17*mm, height=13*mm,
                    preserveAspectRatio=True, anchor='c', mask='auto')
            self.setFillColor(colors.white)
            self.setFont('Helvetica-Bold', 13)
            self.drawString(48*mm, height-15*mm, title)
            self.setFillColor(colors.HexColor('#BFD5FF'))
            self.setFont('Helvetica', 8.5)
            self.drawString(48*mm, height-21*mm, subtitle)
            self.setStrokeColor(LINE)
            self.line(16*mm, 15*mm, width-16*mm, 15*mm)
            self.setFillColor(MUTED)
            self.setFont('Helvetica', 7.5)
            self.drawString(16*mm, 9.5*mm, 'VantaNet Maintenance 1.3.3')
            self.drawRightString(width-16*mm, 9.5*mm,
                f'Seite {self.getPageNumber()} / {total}')
            self.restoreState()
    return BrandedCanvas


def _document(title, subtitle, logo_path):
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm,
        topMargin=42*mm, bottomMargin=20*mm, title=title, author='VantaNet')
    return out, doc, _canvas_class(title,subtitle,logo_path)


def _info_grid(items, styles):
    cells=[]
    for label, value in items:
        shown='-' if value is None or value=='' else value
        cells.append([[_p(label.upper(), styles['label'])], [_p(shown, styles['value'])]])
    rows=[]
    for index in range(0, len(cells), 2):
        row=[]
        for cell in cells[index:index+2]:
            row.append(Table(cell, colWidths=[76*mm]))
        while len(row)<2: row.append('')
        rows.append(row)
    table=Table(rows, colWidths=[87*mm,87*mm], hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),SOFT),('BOX',(0,0),(-1,-1),0.5,LINE),
        ('INNERGRID',(0,0),(-1,-1),0.5,colors.white),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),5*mm),('RIGHTPADDING',(0,0),(-1,-1),5*mm),
        ('TOPPADDING',(0,0),(-1,-1),3.5*mm),('BOTTOMPADDING',(0,0),(-1,-1),3.5*mm),
    ]))
    return table


def _check_blocks(report, styles):
    blocks=[]
    for check in report.get('checks', []):
        status=check.get('status','nicht verfügbar')
        badge=Table([[_p(status.upper(), styles['status'])]], colWidths=[35*mm])
        badge.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),_status_color(status)),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),3*mm),
            ('TOPPADDING',(0,0),(-1,-1),1.8*mm),('BOTTOMPADDING',(0,0),(-1,-1),1.8*mm)]))
        heading=Table([[_p(check.get('area','Prüfung'),styles['value']),badge]],
            colWidths=[135*mm,35*mm], hAlign='LEFT')
        heading.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('BOTTOMPADDING',(0,0),(-1,-1),2*mm)]))
        body=Table([[_p(check.get('detail',''),styles['body'])],
            [_p('Quelle: '+check.get('source',''),styles['small'])]], colWidths=[170*mm])
        body.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),SOFT),('BOX',(0,0),(-1,-1),0.5,LINE),
            ('LEFTPADDING',(0,0),(-1,-1),4*mm),('RIGHTPADDING',(0,0),(-1,-1),4*mm),
            ('TOPPADDING',(0,0),(-1,-1),2.8*mm),('BOTTOMPADDING',(0,0),(-1,-1),2.8*mm)]))
        blocks.append(KeepTogether([heading,body,Spacer(1,4*mm)]))
    return blocks


def build_check_report(report, stamp, logo_path):
    styles=_styles();created=stamp(report.get('created'))
    out,doc,canvas_class=_document('Home Assistant Prüfbericht','Prüfstand '+created,logo_path)
    counts={}
    for check in report.get('checks',[]):counts[check.get('status','nicht verfügbar')]=counts.get(check.get('status','nicht verfügbar'),0)+1
    story=[_p('Systemprüfung',styles['title']),
        _p('Dokumentation der während der Wartung automatisch ausgeführten Home-Assistant-Prüfungen.',styles['lead']),
        _info_grid([('Prüfstand',created),('Berichts-ID',report.get('id','-')),
            ('Geprüft',counts.get('geprüft',0)),('Hinweise',sum(v for k,v in counts.items() if k!='geprüft'))],styles),
        Spacer(1,6*mm),_p('Prüfergebnisse',styles['h2'])]
    story.extend(_check_blocks(report,styles))
    story.extend([Spacer(1,3*mm),_p('Verantwortliche Fachkraft',styles['h2'])])
    maintenance=report.get('maintenance') or {}
    tech=maintenance.get('technician') or {}
    story.append(_info_grid([('Fachkraft',tech.get('name','-')),('Unternehmen',tech.get('company','-')),
        ('Standort',tech.get('location','-')),('Wartungsbeginn',stamp(maintenance.get('started')))],styles))
    story.extend([Spacer(1,10*mm),_p('Unterschrift Fachkraft',styles['label']),Spacer(1,8*mm)])
    line=Table([['']],colWidths=[80*mm],rowHeights=[1])
    line.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,-1),0.7,INK)]));story.append(line)
    doc.build(story,canvasmaker=canvas_class)
    return out.getvalue()


def build_handover(state, record, report, stamp, logo_path):
    styles=_styles();out,doc,canvas_class=_document('Wartungsübergabe','VantaNet Home Assistant Service',logo_path)
    tech=record.get('technician') or {}
    duration=max(0,record.get('finished',0)-record.get('started',0))
    story=[_p('Wartung erfolgreich dokumentiert',styles['title']),
        _p('Übersicht der ausgeführten Wartung mit Zeitangaben, verantwortlicher Fachkraft und Systemprüfung.',styles['lead']),
        _info_grid([('Standort',tech.get('location','-')),('Fachkraft',tech.get('name','-')),
            ('Unternehmen',tech.get('company','-')),('Wartungs-ID',record.get('id','-')),
            ('Beginn',stamp(record.get('started'))),('Abschluss',stamp(record.get('finished'))),
            ('Dauer',f'{duration//60} Minuten'),('Nächster Termin',stamp(state.get('due')))],styles),
        Spacer(1,6*mm),_p('Systemprüfung',styles['h2'])]
    if report:
        counts={}
        for check in report.get('checks',[]):counts[check.get('status','nicht verfügbar')]=counts.get(check.get('status','nicht verfügbar'),0)+1
        story.extend([_info_grid([('Prüfstand',stamp(report.get('created'))),
            ('Geprüfte Bereiche',len(report.get('checks',[]))),('Erfolgreich',counts.get('geprüft',0)),
            ('Hinweise',sum(v for k,v in counts.items() if k!='geprüft'))],styles),Spacer(1,4*mm)])
        story.extend(_check_blocks(report,styles))
    else:
        story.append(_p('Für diese Wartung liegt noch kein abgeschlossener Prüfstand vor.',styles['body']))
    story.extend([Spacer(1,5*mm)])
    signatures=Table([
        ['', ''],
        [_p('Fachkraft / Datum',styles['small']),_p('Übernahme / Datum',styles['small'])]
    ],colWidths=[82*mm,82*mm],rowHeights=[8*mm,5*mm])
    signatures.setStyle(TableStyle([('LINEABOVE',(0,0),(-1,0),0.7,INK),
        ('TOPPADDING',(0,1),(-1,1),2*mm),('RIGHTPADDING',(0,0),(0,-1),8*mm),
        ('LEFTPADDING',(1,0),(1,-1),8*mm)]));story.append(signatures)
    doc.build(story,canvasmaker=canvas_class)
    return out.getvalue()
