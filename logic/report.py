"""
CryoGuard — PDF Compliance Report Generator
-------------------------------------
Builds a downloadable compliance report summarizing the current
shipment status, the active cargo threshold profile, sensor voting
detail, and the recent event log. Returns raw PDF bytes so the caller
(Streamlit) can hand them straight to a download button without
touching disk.
"""

from __future__ import annotations
import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

STATE_COLORS = {
    "SAFE": colors.HexColor("#1f8a44"),
    "WARNING": colors.HexColor("#c47d0a"),
    "CRITICAL": colors.HexColor("#c0332b"),
    "LOCKED": colors.HexColor("#7a1f1f"),
}


def build_pdf_report(snapshot: dict, log_rows: list[dict]) -> bytes:
    """
    snapshot: dict with keys —
        cargo_mode, profile, state, locked, reasons,
        trusted_temp, trusted_humidity, battery_pct,
        confidence, safe_hours_remaining, transit_hours_remaining,
        route_status, route_margin_hours,
        temp_readings, temp_flagged, humidity_readings, humidity_flagged,
        jolt_flags, jolt_confirmed, jolt_votes, jolt_total
    log_rows: list of dicts (most recent events, oldest first) with keys —
        tick, state, temp, humidity, battery, route_status
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CGTitle", parent=styles["Title"], fontSize=20, spaceAfter=4)
    sub_style = ParagraphStyle("CGSub", parent=styles["Normal"], textColor=colors.grey, spaceAfter=14)
    h2 = ParagraphStyle("CGH2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    body = styles["Normal"]

    story = []

    # --- Header ---
    story.append(Paragraph("CryoGuard Cold Chain Compliance Report", title_style))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp; "
        f"Cargo Mode: <b>{snapshot['cargo_mode']}</b> &nbsp;|&nbsp; "
        f"Reference standard: {snapshot['profile']['reference']}",
        sub_style,
    ))

    # --- Status banner ---
    display_state = "LOCKED" if snapshot["locked"] else snapshot["state"]
    banner_color = STATE_COLORS.get(display_state, colors.grey)
    banner_table = Table([[Paragraph(f"<b>SHIPMENT STATUS: {display_state}</b>", ParagraphStyle(
        "Banner", parent=styles["Normal"], textColor=colors.white, fontSize=14, alignment=1))]],
        colWidths=[6.8 * inch])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), banner_color),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 12))

    # --- Key metrics table ---
    story.append(Paragraph("Key Metrics", h2))
    profile = snapshot["profile"]
    metrics_data = [
        ["Metric", "Value", "Safe Band"],
        ["Temperature", f"{snapshot['trusted_temp']:.1f} \u00b0C", f"{profile['temp_min']}-{profile['temp_max']} \u00b0C"],
        ["Humidity", f"{snapshot['trusted_humidity']:.1f} %", f"{profile['humidity_min']}-{profile['humidity_max']} %"],
        ["Battery", f"{snapshot['battery_pct']:.0f} %", "\u2014"],
        ["Predictive Confidence", f"{snapshot['confidence']:.0f} %", "\u2014"],
        ["Estimated Safe Time Remaining", f"{snapshot['safe_hours_remaining']:.1f} hrs", f"budget: {profile['max_safe_hours']} hrs"],
        ["Remaining Transit Time", f"{snapshot['transit_hours_remaining']:.1f} hrs", "\u2014"],
        ["Route Viability", f"{snapshot['route_status']} ({snapshot['route_margin_hours']:+.1f} hrs margin)", "\u2014"],
    ]
    t = Table(metrics_data, colWidths=[2.3 * inch, 2.5 * inch, 2.0 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c2733")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    # --- Reasons / flags ---
    if snapshot["reasons"]:
        story.append(Paragraph("Status Reasons", h2))
        for r in snapshot["reasons"]:
            story.append(Paragraph(f"\u2022 {r}", body))

    # --- Sensor voting detail ---
    story.append(Paragraph("Fail-Safe Sensor Voting Detail", h2))
    sensor_data = [["Parameter", "Raw Readings", "Flagged Sensors", "Trusted Value"]]
    sensor_data.append([
        "Temperature",
        ", ".join(f"{v:.1f}" for v in snapshot["temp_readings"]),
        ", ".join(f"S{i+1}" for i in snapshot["temp_flagged"]) or "None",
        f"{snapshot['trusted_temp']:.1f} \u00b0C",
    ])
    sensor_data.append([
        "Humidity",
        ", ".join(f"{v:.1f}" for v in snapshot["humidity_readings"]),
        ", ".join(f"S{i+1}" for i in snapshot["humidity_flagged"]) or "None",
        f"{snapshot['trusted_humidity']:.1f} %",
    ])
    sensor_data.append([
        "Jolt (quorum)",
        ", ".join("TRIG" if f else "-" for f in snapshot["jolt_flags"]),
        f"{snapshot['jolt_votes']}/{snapshot['jolt_total']} sensors agree",
        "CONFIRMED" if snapshot["jolt_confirmed"] else "Not confirmed",
    ])
    st = Table(sensor_data, colWidths=[1.3 * inch, 2.2 * inch, 1.8 * inch, 1.5 * inch])
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c2733")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(st)

    # --- Event log ---
    if log_rows:
        story.append(PageBreak())
        story.append(Paragraph("Recent Event Log", h2))
        log_data = [["Tick", "State", "Temp (\u00b0C)", "Humidity (%)", "Battery (%)", "Route Status"]]
        for row in log_rows[-30:]:
            log_data.append([
                str(row["tick"]), row["state"], f"{row['temp']:.1f}",
                f"{row['humidity']:.1f}", f"{row['battery']:.0f}", row["route_status"],
            ])
        lt = Table(log_data, colWidths=[0.6 * inch, 1.1 * inch, 1.1 * inch, 1.2 * inch, 1.1 * inch, 1.6 * inch], repeatRows=1)
        lt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c2733")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ]))
        story.append(lt)

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "This report was generated automatically by CryoGuard for demonstration purposes. "
        "Threshold values are representative of published cold-chain guidance and should be "
        "validated against your organization's certified standard before operational use.",
        ParagraphStyle("Disclaimer", parent=styles["Normal"], fontSize=7.5, textColor=colors.grey),
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
