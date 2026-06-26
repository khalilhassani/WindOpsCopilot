import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from backend.app.config import settings

def generate_turbine_report(agent_result: dict) -> str:
    """
    Generates a high-quality PDF report for the turbine execution state.
    Returns the absolute path to the generated PDF.
    """
    turbine_id = agent_result.get("turbine_id", "Unknown")
    correlation_id = agent_result.get("correlation_id", "N/A")
    timestamp = agent_result.get("timestamp", datetime.utcnow().isoformat())
    metrics = agent_result.get("metrics", {})
    health_score = agent_result.get("health_score", 100.0)
    alerts = agent_result.get("alerts", [])
    diagnosis = agent_result.get("diagnosis")
    decisions = agent_result.get("decisions", [])
    logs = agent_result.get("logs", [])

    # Setup file path
    filename = f"report_{turbine_id}_{correlation_id[:8]}.pdf"
    filepath = os.path.join(settings.REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    primary_color = colors.HexColor("#0f172a")  # Slate 900
    secondary_color = colors.HexColor("#0284c7") # Sky 600
    danger_color = colors.HexColor("#b91c1c") # Red 700
    warning_color = colors.HexColor("#d97706") # Amber 600
    success_color = colors.HexColor("#16a34a") # Green 600
    text_color = colors.HexColor("#334155") # Slate 700

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=primary_color,
        spaceAfter=12
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=secondary_color,
        spaceBefore=10,
        spaceAfter=6,
        borderPadding=2
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        textColor=text_color,
        leading=14
    )

    bold_body_style = ParagraphStyle(
        'BoldBodyTextCustom',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # Title & Metadata
    story.append(Paragraph(f"WindOps Copilot - Turbine Report", title_style))
    story.append(Paragraph(f"<b>Turbine ID:</b> {turbine_id} | <b>Correlation ID:</b> {correlation_id}", body_style))
    story.append(Paragraph(f"<b>Report Generated:</b> {timestamp}", body_style))
    story.append(Spacer(1, 15))

    # Health Index Banner
    health_color = success_color if health_score >= 85 else (warning_color if health_score >= 60 else danger_color)
    health_banner_data = [[
        Paragraph(f"<b>TURBINE HEALTH STATUS</b>", ParagraphStyle('H1', parent=body_style, textColor=colors.white)),
        Paragraph(f"<b>{health_score:.1f}% Health</b>", ParagraphStyle('H2', parent=body_style, fontSize=14, textColor=colors.white, alignment=2))
    ]]
    health_table = Table(health_banner_data, colWidths=[270, 270])
    health_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), health_color),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(health_table)
    story.append(Spacer(1, 15))

    # 1. Telemetry Data
    story.append(Paragraph("Live Sensor Telemetry", section_style))
    
    sensor_headers = [Paragraph("<b>Sensor Parameter</b>", bold_body_style), Paragraph("<b>Value</b>", bold_body_style), Paragraph("<b>Unit</b>", bold_body_style)]
    sensor_rows = [sensor_headers]
    
    sensor_mappings = [
        ("Wind Speed", "wind_speed", "m/s"),
        ("Rotor Speed", "rotor_speed", "RPM"),
        ("Blade Temperature", "blade_temp", "°C"),
        ("Generator Temperature", "generator_temp", "°C"),
        ("Vibration", "vibration", "mm/s"),
        ("Power Output", "power_output", "MW"),
        ("Operational Status", "status", "")
    ]
    
    for label, key, unit in sensor_mappings:
        val = metrics.get(key, "N/A")
        if isinstance(val, float):
            val_str = f"{val:.2f}"
        else:
            val_str = str(val)
        sensor_rows.append([Paragraph(label, body_style), Paragraph(val_str, body_style), Paragraph(unit, body_style)])

    sensor_table = Table(sensor_rows, colWidths=[180, 180, 180])
    sensor_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(sensor_table)
    story.append(Spacer(1, 15))

    # 2. Alerts Detected
    story.append(Paragraph("Active Fault Alerts", section_style))
    if not alerts:
        story.append(Paragraph("No active alerts detected. The turbine is operating within nominal thresholds.", body_style))
    else:
        alert_headers = [Paragraph("<b>Parameter</b>", bold_body_style), Paragraph("<b>Value</b>", bold_body_style), Paragraph("<b>Threshold</b>", bold_body_style), Paragraph("<b>Severity</b>", bold_body_style)]
        alert_rows = [alert_headers]
        for a in alerts:
            sev = a.get("severity", "warning").upper()
            sev_color = danger_color if sev == "CRITICAL" else warning_color
            alert_rows.append([
                Paragraph(a.get("parameter", "").replace("_", " ").title(), body_style),
                Paragraph(f"{a.get('value', 0.0):.2f}", body_style),
                Paragraph(f"{a.get('threshold', 0.0):.2f}", body_style),
                Paragraph(f"<b>{sev}</b>", ParagraphStyle('AlertSev', parent=body_style, textColor=sev_color))
            ])
        alert_table = Table(alert_rows, colWidths=[135, 135, 135, 135])
        alert_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fee2e2")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#fca5a5")),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(alert_table)
    story.append(Spacer(1, 15))

    # 3. Diagnosis
    story.append(Paragraph("Diagnostic Root Cause Analysis", section_style))
    if diagnosis:
        diag_cause = diagnosis.get("cause", "N/A")
        diag_conf = diagnosis.get("confidence", 0.0) * 100
        diag_details = diagnosis.get("details", "")
        
        diag_data = [
            [Paragraph("<b>Diagnosed Cause:</b>", bold_body_style), Paragraph(diag_cause, body_style)],
            [Paragraph("<b>Confidence Level:</b>", bold_body_style), Paragraph(f"{diag_conf:.1f}%", body_style)],
            [Paragraph("<b>Technical Analysis:</b>", bold_body_style), Paragraph(diag_details, body_style)]
        ]
        diag_table = Table(diag_data, colWidths=[130, 410])
        diag_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f8fafc")),
        ]))
        story.append(diag_table)
    else:
        story.append(Paragraph("No diagnostic analysis was required (turbine health is nominal).", body_style))
    story.append(Spacer(1, 15))

    # 4. Action Scenarios
    story.append(Paragraph("Operational Action Recommendations", section_style))
    if decisions:
        dec_headers = [
            Paragraph("<b>Recommended Action</b>", bold_body_style),
            Paragraph("<b>Description</b>", bold_body_style),
            Paragraph("<b>Risk</b>", bold_body_style),
            Paragraph("<b>Production Loss</b>", bold_body_style),
            Paragraph("<b>Confidence</b>", bold_body_style)
        ]
        dec_rows = [dec_headers]
        for d in decisions:
            risk = d.get("risk_level", "low").upper()
            risk_color = danger_color if risk == "HIGH" else (warning_color if risk == "MEDIUM" else success_color)
            
            dec_rows.append([
                Paragraph(f"<b>{d.get('action', '')}</b>", body_style),
                Paragraph(d.get("description", ""), body_style),
                Paragraph(f"<b>{risk}</b>", ParagraphStyle('RiskC', parent=body_style, textColor=risk_color)),
                Paragraph(d.get("production_impact", ""), body_style),
                Paragraph(f"{d.get('confidence', 0.0) * 100:.0f}%", body_style)
            ])
        dec_table = Table(dec_rows, colWidths=[110, 180, 70, 110, 70])
        dec_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(dec_table)
    else:
        story.append(Paragraph("No operational action recommendations available.", body_style))
        
    story.append(Spacer(1, 15))
    story.append(Paragraph("<i>Note: This report is generated by an autonomous multi-agent system. final actions must be reviewed and authorized by a human operator.</i>", ParagraphStyle('Foot', parent=body_style, fontSize=8, textColor=colors.HexColor("#64748b"))))

    # Build PDF
    doc.build(story)
    
    return filepath
