"""Generate the AarogyaNet pitch PDF (English) for HackNation 2026."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


PALETTE = {
    "ink": colors.HexColor("#0F1B1A"),
    "deep": colors.HexColor("#0E4F4A"),
    "teal": colors.HexColor("#1B7A72"),
    "mint": colors.HexColor("#9FD3C7"),
    "sand": colors.HexColor("#F5EFE6"),
    "paper": colors.HexColor("#FBF9F4"),
    "coral": colors.HexColor("#E8634A"),
    "amber": colors.HexColor("#F2B544"),
    "muted": colors.HexColor("#5C6B68"),
    "rule": colors.HexColor("#D9D2C5"),
    "white": colors.white,
}


styles = getSampleStyleSheet()


def style(name: str, **kw) -> ParagraphStyle:
    base = ParagraphStyle(name=name, parent=styles["Normal"])
    for k, v in kw.items():
        setattr(base, k, v)
    return base


S_TITLE = style(
    "title",
    fontName="Helvetica-Bold",
    fontSize=44,
    leading=50,
    textColor=PALETTE["deep"],
    alignment=TA_LEFT,
    spaceAfter=8,
)
S_SUPER = style(
    "super",
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=12,
    textColor=PALETTE["coral"],
    alignment=TA_LEFT,
    spaceAfter=4,
)
S_TAGLINE = style(
    "tagline",
    fontName="Helvetica-Oblique",
    fontSize=18,
    leading=24,
    textColor=PALETTE["muted"],
    alignment=TA_LEFT,
    spaceAfter=18,
)
S_H1 = style(
    "h1",
    fontName="Helvetica-Bold",
    fontSize=24,
    leading=28,
    textColor=PALETTE["deep"],
    spaceBefore=4,
    spaceAfter=10,
)
S_H2 = style(
    "h2",
    fontName="Helvetica-Bold",
    fontSize=12,
    leading=15,
    textColor=PALETTE["teal"],
    spaceBefore=6,
    spaceAfter=4,
)
S_KICKER = style(
    "kicker",
    fontName="Helvetica-Bold",
    fontSize=9,
    leading=11,
    textColor=PALETTE["coral"],
    spaceAfter=2,
)
S_BODY = style(
    "body",
    fontName="Helvetica",
    fontSize=10.5,
    leading=15,
    textColor=PALETTE["ink"],
    alignment=TA_JUSTIFY,
    spaceAfter=8,
)
S_BODY_TIGHT = style(
    "body_tight",
    fontName="Helvetica",
    fontSize=10,
    leading=14,
    textColor=PALETTE["ink"],
    spaceAfter=4,
)
S_LEAD = style(
    "lead",
    fontName="Helvetica",
    fontSize=12,
    leading=18,
    textColor=PALETTE["ink"],
    alignment=TA_JUSTIFY,
    spaceAfter=10,
)
S_QUOTE = style(
    "quote",
    fontName="Helvetica-Oblique",
    fontSize=13,
    leading=19,
    textColor=PALETTE["deep"],
    alignment=TA_LEFT,
    leftIndent=12,
    spaceAfter=10,
)
S_STAT_NUM = style(
    "stat_num",
    fontName="Helvetica-Bold",
    fontSize=28,
    leading=30,
    textColor=PALETTE["deep"],
    alignment=TA_CENTER,
)
S_STAT_LABEL = style(
    "stat_label",
    fontName="Helvetica",
    fontSize=8.5,
    leading=11,
    textColor=PALETTE["muted"],
    alignment=TA_CENTER,
)
S_FOOTER = style(
    "footer",
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=PALETTE["muted"],
    alignment=TA_LEFT,
)
S_COVER_NUM = style(
    "cover_num",
    fontName="Helvetica-Bold",
    fontSize=72,
    leading=72,
    textColor=PALETTE["coral"],
    alignment=TA_LEFT,
)
S_COVER_NUM_LABEL = style(
    "cover_num_label",
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=14,
    textColor=PALETTE["deep"],
    alignment=TA_LEFT,
)
S_CODE = style(
    "code",
    fontName="Courier",
    fontSize=7.0,
    leading=8.6,
    textColor=PALETTE["ink"],
)
S_TBL = style(
    "tbl",
    fontName="Helvetica",
    fontSize=8.6,
    leading=11,
    textColor=PALETTE["ink"],
)
S_TBL_BOLD = style(
    "tbl_bold",
    fontName="Helvetica-Bold",
    fontSize=8.8,
    leading=11,
    textColor=PALETTE["deep"],
)
S_TBL_HEAD = style(
    "tbl_head",
    fontName="Helvetica-Bold",
    fontSize=9.2,
    leading=11.5,
    textColor=PALETTE["white"],
)
S_TBL_MUTED = style(
    "tbl_muted",
    fontName="Helvetica",
    fontSize=8.6,
    leading=11,
    textColor=PALETTE["muted"],
)


def P(text: str, st: ParagraphStyle = S_TBL) -> Paragraph:
    return Paragraph(text, st)


def hr(width: float = 17 * cm, color=None, thickness: float = 0.7) -> Table:
    line = Table([[""]], colWidths=[width], rowHeights=[thickness])
    line.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color or PALETTE["rule"]),
                ("LINEBELOW", (0, 0), (-1, -1), 0, PALETTE["rule"]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return line


def stat_card(value: str, label: str, color=None) -> Table:
    color = color or PALETTE["deep"]
    inner = Table(
        [
            [Paragraph(f'<font color="{color.hexval()}">{value}</font>', S_STAT_NUM)],
            [Paragraph(label, S_STAT_LABEL)],
        ],
        colWidths=[3.95 * cm],
    )
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE["sand"]),
                ("BOX", (0, 0), (-1, -1), 0.6, PALETTE["rule"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return inner


def stat_row(items: list[tuple[str, str, object]]) -> Table:
    cells = [stat_card(v, l, c) for v, l, c in items]
    row = Table([cells], colWidths=[4.15 * cm] * len(cells))
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return row


def callout(title: str, body: str, accent=None) -> Table:
    accent = accent or PALETTE["coral"]
    inner = Table(
        [
            [Paragraph(title, S_KICKER)],
            [Paragraph(body, S_BODY_TIGHT)],
        ],
        colWidths=[16.5 * cm],
    )
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE["paper"]),
                ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return inner


def feature_card(num: str, title: str, body: str) -> Table:
    num_para = Paragraph(
        f'<font color="{PALETTE["coral"].hexval()}" size="20"><b>{num}</b></font>',
        style("fc_num",
              fontName="Helvetica-Bold",
              fontSize=20,
              leading=22,
              textColor=PALETTE["coral"],
              alignment=TA_CENTER),
    )
    title_para = Paragraph(
        f'<font color="{PALETTE["deep"].hexval()}"><b>{title}</b></font>',
        style("fc_title",
              fontName="Helvetica-Bold",
              fontSize=12,
              leading=14,
              textColor=PALETTE["deep"]),
    )
    body_para = Paragraph(
        body,
        style("fc_body",
              fontName="Helvetica",
              fontSize=9.4,
              leading=12.4,
              textColor=PALETTE["ink"]),
    )
    right_stack = Table(
        [[title_para], [body_para]],
        colWidths=[14.7 * cm],
    )
    right_stack.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (0, 0), 0),
        ("BOTTOMPADDING", (0, 0), (0, 0), 4),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (0, 1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    inner = Table([[num_para, right_stack]], colWidths=[1.5 * cm, 14.7 * cm])
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE["sand"]),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE["rule"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (0, 0), "TOP"),
                ("VALIGN", (1, 0), (1, 0), "TOP"),
            ]
        )
    )
    return inner


def persona_card(role: str, name: str, scenario: str) -> Table:
    inner = Table(
        [
            [Paragraph(role, S_KICKER)],
            [Paragraph(f'<b>{name}</b>', style("p_name",
                                              fontName="Helvetica-Bold",
                                              fontSize=12,
                                              leading=14,
                                              textColor=PALETTE["deep"]))],
            [Paragraph(scenario, S_BODY_TIGHT)],
        ],
        colWidths=[5.45 * cm],
    )
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE["paper"]),
                ("BOX", (0, 0), (-1, -1), 0.5, PALETTE["rule"]),
                ("LINEABOVE", (0, 0), (-1, 0), 3, PALETTE["coral"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return inner


def section_header(kicker: str, title: str) -> list:
    return [
        Paragraph(kicker, S_SUPER),
        Paragraph(title, S_H1),
        hr(),
        Spacer(1, 12),
    ]


def header_footer(canvas, doc):
    canvas.saveState()
    page_w, page_h = A4
    if doc.page > 1:
        canvas.setFillColor(PALETTE["deep"])
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(2 * cm, page_h - 1.2 * cm, "AarogyaNet")
        canvas.setFillColor(PALETTE["muted"])
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            4 * cm, page_h - 1.2 * cm,
            "Guide care, don't just map it.  ·  HackNation 2026 / Challenge 3"
        )
        canvas.setStrokeColor(PALETTE["rule"])
        canvas.setLineWidth(0.4)
        canvas.line(2 * cm, page_h - 1.4 * cm, page_w - 2 * cm, page_h - 1.4 * cm)
        canvas.setFillColor(PALETTE["muted"])
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(
            page_w - 2 * cm, 1.2 * cm, f"Page {doc.page}"
        )
        canvas.drawString(
            2 * cm, 1.2 * cm,
            "Databricks Vector Search  ·  Foundation Model APIs  ·  Genie  ·  SQL Warehouse  ·  MLflow Agent Bricks"
        )
    canvas.restoreState()


def cover_page(canvas, doc):
    canvas.saveState()
    page_w, page_h = A4
    canvas.setFillColor(PALETTE["deep"])
    canvas.rect(0, page_h - 5.5 * cm, page_w, 5.5 * cm, stroke=0, fill=1)
    canvas.setFillColor(PALETTE["coral"])
    canvas.rect(0, page_h - 5.7 * cm, page_w, 0.2 * cm, stroke=0, fill=1)

    canvas.setFillColor(PALETTE["white"])
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(2 * cm, page_h - 1.6 * cm, "HACKNATION 2026  ·  CHALLENGE 3")
    canvas.setFillColor(PALETTE["mint"])
    canvas.setFont("Helvetica", 9)
    canvas.drawString(2 * cm, page_h - 2.0 * cm, "Databricks Agentic Healthcare Maps")

    canvas.setFillColor(PALETTE["white"])
    canvas.setFont("Helvetica-Bold", 56)
    canvas.drawString(2 * cm, page_h - 4.2 * cm, "AarogyaNet")
    canvas.setFillColor(PALETTE["mint"])
    canvas.setFont("Helvetica-Oblique", 14)
    canvas.drawString(2 * cm, page_h - 5.1 * cm,
                      "Guide care, don't just map it.")

    canvas.setFillColor(PALETTE["sand"])
    canvas.rect(0, 0, page_w, page_h - 5.7 * cm, stroke=0, fill=1)

    canvas.setFillColor(PALETTE["coral"])
    canvas.setFont("Helvetica-Bold", 84)
    canvas.drawString(2 * cm, page_h - 8.6 * cm, "10,000")
    canvas.setFillColor(PALETTE["deep"])
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(2 * cm, page_h - 9.4 * cm,
                      "facilities ingested, cleaned, and trust-scored")
    canvas.setFillColor(PALETTE["muted"])
    canvas.setFont("Helvetica", 11)
    canvas.drawString(2 * cm, page_h - 9.95 * cm,
                      "across India — every recommendation grounded in real Databricks data.")

    canvas.setStrokeColor(PALETTE["rule"])
    canvas.setLineWidth(0.6)
    canvas.line(2 * cm, page_h - 11.0 * cm, page_w - 2 * cm, page_h - 11.0 * cm)

    canvas.setFillColor(PALETTE["deep"])
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(2 * cm, page_h - 11.9 * cm, "THE PROMISE")
    canvas.setFillColor(PALETTE["ink"])
    canvas.setFont("Helvetica", 12)
    lines = [
        "Google Maps shows the nearest hospital. Nearest is not best.",
        "AarogyaNet triages the patient, ranks hospitals on calibrated trust,",
        "books bed + ambulance + doctor + drug atomically, and learns from outcomes.",
    ]
    y = page_h - 12.6 * cm
    for ln in lines:
        canvas.drawString(2 * cm, y, ln)
        y -= 0.55 * cm

    mini_stats = [
        ("3,736", "PINs mapped"),
        ("4-tier", "Trust badge"),
        ("$0.30", "LLM cost / 256"),
        ("0.831 → 0.350", "Trust learns"),
    ]
    box_top = page_h - 16.2 * cm
    box_h = 2.1 * cm
    box_w = (page_w - 4 * cm - 3 * 0.4 * cm) / 4
    for i, (val, lbl) in enumerate(mini_stats):
        x = 2 * cm + i * (box_w + 0.4 * cm)
        canvas.setFillColor(PALETTE["white"])
        canvas.setStrokeColor(PALETTE["rule"])
        canvas.setLineWidth(0.5)
        canvas.roundRect(x, box_top, box_w, box_h, 4, stroke=1, fill=1)
        canvas.setFillColor(PALETTE["coral"])
        canvas.setFont("Helvetica-Bold", 16 if len(val) <= 6 else 12)
        canvas.drawCentredString(x + box_w / 2, box_top + box_h - 1.0 * cm, val)
        canvas.setFillColor(PALETTE["muted"])
        canvas.setFont("Helvetica", 8.5)
        canvas.drawCentredString(x + box_w / 2, box_top + 0.55 * cm, lbl)

    canvas.setFillColor(PALETTE["deep"])
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(2 * cm, 5.4 * cm, "LIVE STACK")
    canvas.setFillColor(PALETTE["ink"])
    canvas.setFont("Helvetica", 10.5)
    canvas.drawString(2 * cm, 4.7 * cm, "Backend     ·  https://aarogyanet-api-production.up.railway.app")
    canvas.drawString(2 * cm, 4.15 * cm, "Frontend    ·  https://app-wine-pi.vercel.app")
    canvas.drawString(2 * cm, 3.6 * cm, "Workspace ·  Databricks  dbc-17e9d40d-5056")
    canvas.drawString(2 * cm, 3.05 * cm, "Sponsor    ·  Vector Search · FM APIs · Genie · MLflow Agent Bricks")

    canvas.setFillColor(PALETTE["coral"])
    canvas.rect(0, 0, page_w, 0.6 * cm, stroke=0, fill=1)
    canvas.setFillColor(PALETTE["white"])
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(2 * cm, 0.2 * cm,
                      "PITCH BRIEF  ·  TECHNICAL VIDEO COMPANION  ·  ENGLISH EDITION")
    canvas.drawRightString(page_w - 2 * cm, 0.2 * cm, "v1.0  ·  2026-04-26")

    canvas.restoreState()


def architecture_block() -> Preformatted:
    diagram = (
        "Patient (Hindi / Urdu voice or text)\n"
        "      |\n"
        "      v\n"
        "  /triage    --> Vector Search BGE-large + Llama 3.3 fallback\n"
        "      |          (specialty, urgency, fast_path, red_flag_match)\n"
        "      v\n"
        "  /recommend --> Router: P(bed) x travel x specialty x trust\n"
        "      |          Trust = Llama 3.3 + Llama 4 Maverick consensus\n"
        "      |          Badge: rule / single / verified / disagreement\n"
        "      |          SSE: triage -> extractor -> validator -> router\n"
        "      v\n"
        "  /book      --> Atomic saga: bed + ambulance + doctor + drug\n"
        "      |          txn_atomic; ANY leg fails  ->  rollback all 4\n"
        "      |          hash_patient_id before warehouse insert\n"
        "      v\n"
        "  /outcome   --> Patient ping after care\n"
        "      |          v_trust_calibrated view recomputes trust\n"
        "      v\n"
        "  Demo arc   :   Aradhna 0.831 -> 0.350 after 6 negatives\n"
        "\n"
        "  /sponsor/genie/query  --> Databricks Genie  ·  NL -> SQL\n"
        "                             live: WorkspaceClient().genie\n"
        "                             canned: deterministic demo fallback\n"
    )
    return Preformatted(diagram, S_CODE)


def build():
    out = Path(__file__).resolve().parent.parent / "AarogyaNet_Pitch_EN.pdf"

    doc = BaseDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="AarogyaNet — HackNation 2026 Pitch Brief",
        author="AarogyaNet Team",
        subject="Agentic Healthcare Maps · Databricks Challenge 3",
    )

    cover_frame = Frame(0, 0, A4[0], A4[1], id="cover", showBoundary=0,
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    body_frame = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm,
                       id="body", showBoundary=0)

    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=cover_page),
        PageTemplate(id="body", frames=[body_frame], onPage=header_footer),
    ])

    flow: list = []

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    flow.append(Paragraph("EXECUTIVE SUMMARY", S_SUPER))
    flow.append(Paragraph("One paragraph, six numbers, one promise.", S_H1))
    flow.append(hr())
    flow.append(Spacer(1, 14))
    flow.append(Paragraph(
        "AarogyaNet is a multi-agent healthcare map that triages a patient in plain "
        "language (Hindi, Urdu, English voice or text), ranks nearby hospitals on a "
        "calibrated trust score derived from a two-model LLM consensus, and books bed, "
        "ambulance, doctor, and drug as a single atomic transaction. After care, "
        "patient outcomes feed back into the trust score in real time. Density does "
        "not equal access — and a single LLM is not a guardrail. AarogyaNet treats "
        "both as engineering problems, not slogans.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 6))
    flow.append(stat_row([
        ("10,000", "Facilities ingested\nand cleaned", PALETTE["deep"]),
        ("3,736", "Indian PINs mapped\non NGO Desert Map", PALETTE["coral"]),
        ("4", "Atomic resources\nper booking saga", PALETTE["teal"]),
        ("$0.30", "Total LLM cost\nfor 256 facilities", PALETTE["amber"]),
    ]))
    flow.append(Spacer(1, 10))
    flow.append(stat_row([
        ("0.831 → 0.350", "Trust drift\nafter 6 outcomes", PALETTE["coral"]),
        ("4-tier", "Trust badge\n(rule / single / verified / disagree)", PALETTE["deep"]),
        ("20", "Foundation Model\nendpoints live", PALETTE["teal"]),
        ("3", "Apps on one\ndata layer", PALETTE["amber"]),
    ]))
    flow.append(Spacer(1, 18))
    flow.append(callout(
        "WHAT MAKES THIS A PRODUCT, NOT A DEMO",
        "A closed feedback loop: triage → ranked recommendation → atomic booking → "
        "outcome ledger → recalibrated trust. Most hackathon demos stop after the "
        "recommendation step. AarogyaNet writes the loop end-to-end.",
        PALETTE["coral"],
    ))
    flow.append(PageBreak())

    flow += section_header("01  ·  THE PROBLEM",
                           "Maps are not enough. Lives are.")
    flow.append(Paragraph(
        "Every minute of delay in a cardiac event raises mortality by ~1%. "
        "Indian patients face four compounding failures the moment they search "
        "for care:",
        S_LEAD,
    ))
    flow.append(Spacer(1, 8))

    problem_rows = [
        ("Wrong destination",
         "Google Maps returns the nearest hospital — not the best one. "
         "Nearest can be full, lack the right specialist, or be unsafe. "
         "Distance is the only signal."),
        ("Hidden trust gap",
         "Public listings mark a clinic as Level-1 trauma; the equipment log "
         "has been silent since 2023. Single-source claims hide stale, "
         "unverifiable, or contradictory facts."),
        ("Booking is theatre",
         "A ‘booked’ bed without a confirmed ambulance, doctor, or drug is a "
         "promise the system cannot keep. Patients arrive to half-fulfilled "
         "reservations every day."),
        ("No learning loop",
         "The system never asks: did the patient survive, recover, get "
         "transferred? Trust is published once and never updated. Yesterday's "
         "rating decides tomorrow's referral."),
    ]
    for title, body in problem_rows:
        flow.append(callout(title.upper(), body, PALETTE["coral"]))
        flow.append(Spacer(1, 8))

    flow.append(Spacer(1, 8))
    flow.append(Paragraph(
        "These are not UX problems. They are data, distributed-systems, and "
        "feedback-loop problems. AarogyaNet treats them as such.",
        S_QUOTE,
    ))
    flow.append(PageBreak())

    flow += section_header("02  ·  TARGET AUDIENCE",
                           "Three users. Three apps. One data layer.")
    flow.append(Paragraph(
        "The same Databricks lakehouse powers three distinct surfaces, each "
        "tuned to a different decision-maker. Building three products from "
        "one pipeline is the platform-maturity story for the judges.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 14))

    personas = Table(
        [[
            persona_card(
                "PRIMARY  ·  PATIENT",
                "Aradhna · 34 · Mumbai",
                "Chest pain at midnight. Speaks Hindi. Needs the right "
                "cardiology bed, an ambulance, a doctor, and the right "
                "drug — guaranteed before she leaves home.",
            ),
            persona_card(
                "SECONDARY  ·  CLINICIAN",
                "Dr. Iyer · ER lead",
                "Triaging a referral inbound from a smaller clinic. "
                "Needs trust badges, ETA, capacity at receiving hospitals, "
                "and an audit trail for the handoff.",
            ),
            persona_card(
                "TERTIARY  ·  POLICY / NGO",
                "State Health NGO Analyst",
                "Wants to ask, in plain English, ‘which PINs in Bihar have "
                "zero oncology coverage?’ — and get a SQL-grounded answer "
                "to fund the right new clinic.",
            ),
        ]],
        colWidths=[5.7 * cm, 5.7 * cm, 5.7 * cm],
    )
    personas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    flow.append(personas)
    flow.append(Spacer(1, 22))

    flow.append(Paragraph("HOW WE SERVE EACH", S_KICKER))
    flow.append(Spacer(1, 4))
    audience_table = Table(
        [
            [P("Surface", S_TBL_HEAD), P("Who", S_TBL_HEAD),
             P("Job to be done", S_TBL_HEAD),
             P("Killer affordance", S_TBL_HEAD)],
            [P("PatientFlow", S_TBL_BOLD), P("Patient"),
             P("Get the right care now"),
             P("Voice triage + atomic 4-resource booking")],
            [P("DoctorCopilot", S_TBL_BOLD), P("Clinician"),
             P("Refer with confidence"),
             P("Trust badge + SSE reasoning stream")],
            [P("NGODashboard", S_TBL_BOLD), P("NGO / policy"),
             P("See the deserts"),
             P("Per-PIN heatmap + Genie NL&rarr;SQL queries")],
        ],
        colWidths=[3.0 * cm, 2.4 * cm, 4.8 * cm, 6.8 * cm],
    )
    audience_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["deep"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [PALETTE["paper"], PALETTE["sand"]]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, PALETTE["coral"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    flow.append(audience_table)
    flow.append(PageBreak())

    flow += section_header("03  ·  SOLUTION CORE FEATURES",
                           "Seven pillars. One closed loop.")
    flow.append(Paragraph(
        "Each feature ships as a standalone endpoint and a UI surface. "
        "Together they form the only loop that matters: triage, rank, "
        "book, learn.",
        style("lead_tight",
              fontName="Helvetica",
              fontSize=11,
              leading=15,
              textColor=PALETTE["ink"],
              alignment=TA_JUSTIFY,
              spaceAfter=6),
    ))
    flow.append(Spacer(1, 6))

    features = [
        ("01", "Two-model trust consensus",
         "Llama 3.3 70B (Extractor) and Llama 4 Maverick (Validator) score every "
         "facility on four sub-factors — bed availability, oxygen, drug stock, "
         "specialist on-call. Agreement-band logic produces a 4-tier badge: "
         "<b>rule / single-source / verified / disagreement</b>. Disagreements "
         "are surfaced, never silently downgraded. Total LLM cost for 256 "
         "facilities ≈ $0.30."),
        ("02", "Atomic 4-resource booking saga",
         "<b>txn_atomic</b> reserves bed + ambulance + doctor + drug across "
         "four resource tables in a single transaction. If any leg fails, "
         "compensating actions roll back all four. The demo includes a "
         "deliberate ‘ambulance unavailable’ failure — every tile rolls back "
         "live in the UI. No half-promised care."),
        ("03", "Outcome learning loop",
         "<b>/outcome</b> records a patient ping after care. A "
         "<b>v_trust_calibrated</b> view recomputes trust on the fly. The demo "
         "arc shows Aradhna's clinic at 0.831 → 0.350 after six negative "
         "outcomes. The AI does not just recommend — it learns."),
        ("04", "Vernacular voice triage (Hindi / Urdu)",
         "Web Speech API on the patient side captures Hindi or Urdu speech. "
         "After /book commits, Fish Audio TTS narrates the dispatch in the "
         "same language. Inclusivity is wired into the protocol, not bolted on."),
        ("05", "Genie — natural-language SQL for NGOs",
         "<b>POST /sponsor/genie/query</b> wraps Databricks Genie. An NGO "
         "analyst types ‘Bihar PINs with zero oncology’ and receives "
         "executable SQL plus rows from <b>gold_pin_capabilities</b>. Live "
         "mode calls <b>WorkspaceClient().genie</b>; canned mode returns a "
         "deterministic, brief-cited fallback so the demo never 5xx’s. Six "
         "pre-curated queries cover Bihar appendectomy access, oncology "
         "deserts, two-model disagreements, ICU availability, calibrated "
         "trust ≥ 0.80, and cardiology rankings."),
        ("06", "NGO Desert Map",
         "Per-PIN capability heatmap over 3,736 Indian PINs across four "
         "specialties (Trauma, Cardiac, Neuro, Pediatric). The headline: "
         "<b>Bihar — 149 PINs with zero oncology, 130 with zero emergency. "
         "Maharashtra — 1,492 facilities, 403 PINs with zero oncology.</b> "
         "Density is not access."),
        ("07", "SSE reasoning stream",
         "Every agent decision streams over <b>/sse</b> as a structured "
         "event: <i>triage → extractor → validator → router</i>. The frontend "
         "renders the chain in real time. <b>/sse_demo</b> serves a "
         "pre-recorded fallback if the live channel falters mid-pitch."),
    ]

    for num, title, body in features:
        flow.append(feature_card(num, title, body))
        flow.append(Spacer(1, 5))

    flow.append(PageBreak())

    flow += section_header("04  ·  UNIQUE SELLING PROPOSITION",
                           "What only AarogyaNet does.")
    flow.append(Paragraph(
        "Most hackathon healthcare demos stop at ‘LLM gives advice.’ "
        "AarogyaNet ships the discipline of a production system in three "
        "places where competitors cut corners.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 12))

    usp_rows = [
        ("LLM trust",
         "Single LLM call, taken at face value",
         "Two-model consensus, 4-tier confidence badge, "
         "disagreement surfaced not hidden"),
        ("Booking",
         "&lsquo;Reserve bed&rsquo; button writes one row",
         "Atomic saga across 4 resource tables with "
         "compensating-action rollback"),
        ("Feedback",
         "No outcome capture",
         "Patient outcome ledger that recalibrates trust on the fly"),
        ("Inclusivity",
         "English-only chat",
         "Hindi / Urdu voice input + TTS narration in same language"),
        ("NGO surface",
         "Often missing",
         "Second product on the same data &mdash; Desert Map + "
         "Genie NL&rarr;SQL"),
        ("Demo robustness",
         "Live API or bust",
         "<b>SAFE_DEMO=true</b> kill-switch, /sse_demo fallback, "
         "Genie canned mode, smoke test on every deploy"),
    ]
    usp_table = Table(
        [[P("Dimension", S_TBL_HEAD),
          P("Typical hackathon entry", S_TBL_HEAD),
          P("AarogyaNet", S_TBL_HEAD)]] +
        [[P(d, S_TBL_BOLD), P(t, S_TBL_MUTED), P(a, S_TBL)]
         for d, t, a in usp_rows],
        colWidths=[3.0 * cm, 6.0 * cm, 8.0 * cm],
    )
    usp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["deep"]),
        ("BACKGROUND", (2, 1), (2, -1), PALETTE["sand"]),
        ("ROWBACKGROUNDS", (0, 1), (1, -1),
         [PALETTE["paper"], PALETTE["white"]]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, PALETTE["coral"]),
        ("LINEABOVE", (0, 1), (-1, -1), 0.3, PALETTE["rule"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    flow.append(usp_table)
    flow.append(Spacer(1, 18))

    flow.append(Paragraph(
        "Trust is not a single LLM call. It is a two-model consensus, "
        "with a four-tier confidence badge, recalibrated from real patient "
        "outcomes — and the booking that follows is atomic, or it is rolled "
        "back. That is the AarogyaNet wedge.",
        S_QUOTE,
    ))
    flow.append(PageBreak())

    flow += section_header("05  ·  IMPLEMENTATION & TECHNOLOGY",
                           "Architecture, stack, deployment.")
    flow.append(Paragraph("DATA AND CONTROL FLOW", S_H2))
    flow.append(Spacer(1, 4))
    flow.append(architecture_block())
    flow.append(Spacer(1, 10))

    flow.append(Paragraph("STACK", S_H2))
    stack_rows = [
        ("Frontend",
         "React 18  ·  Vite  ·  TypeScript  ·  Tailwind  ·  Leaflet",
         "Map-first UX with live SSE reasoning panel"),
        ("Backend",
         "FastAPI  ·  slowapi  ·  SSE  ·  Pydantic",
         "Async + rate-limited; SSE without extra infra"),
        ("Data",
         "Databricks SQL Warehouse  ·  Vector Search (BGE-large)",
         "Symptom corpus + facility text indexes"),
        ("LLMs",
         "Llama 3.3 70B  ·  Llama 4 Maverick  ·  GPT-5.x fallback",
         "Two-model trust consensus, ~$0.30 / 256 facilities"),
        ("Agent",
         "MLflow ResponsesAgent (Mosaic AI Agent Bricks)",
         "Sponsor conformance, traceable agent runs"),
        ("NL&rarr;SQL",
         "Databricks Genie  ·  WorkspaceClient.genie SDK",
         "Plain-English queries on gold tables for NGOs"),
        ("Voice",
         "Web Speech API (in)  ·  Fish Audio TTS (out)",
         "Hindi / Urdu inclusivity, post-booking narration"),
        ("Logs",
         "Token-scrubbing LogRecordFactory  ·  MLflow tracing",
         "No <b>dapi*</b> / <b>sk-*</b> token ever reaches a handler"),
        ("Hosting",
         "Railway (backend) + Vercel (frontend)",
         "Autodeploy on main; smoke script on every deploy"),
    ]
    stack_table = Table(
        [[P("Layer", S_TBL_HEAD), P("Technology", S_TBL_HEAD),
          P("Why", S_TBL_HEAD)]] +
        [[P(layer, S_TBL_BOLD), P(tech), P(why)]
         for layer, tech, why in stack_rows],
        colWidths=[2.6 * cm, 7.0 * cm, 7.4 * cm],
    )
    stack_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["teal"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [PALETTE["paper"], PALETTE["sand"]]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, PALETTE["coral"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    flow.append(stack_table)
    flow.append(Spacer(1, 10))

    safety_security = Table(
        [[
            Table(
                [
                    [Paragraph("DEMO-SAFETY ENGINEERING",
                               style("safety_h",
                                     fontName="Helvetica-Bold",
                                     fontSize=10.5,
                                     leading=13,
                                     textColor=PALETTE["teal"]))],
                    [Paragraph(
                        "Every sponsor route is flag-gated and default-off. "
                        "<b>SAFE_DEMO=true</b> is a master kill-switch &mdash; "
                        "every sponsor endpoint then returns a pre-baked "
                        "artifact from <b>app/sponsor/_demo/</b>. Genie has "
                        "its own canned mode with deterministic, brief-cited "
                        "responses. <b>/sse_demo</b> replays a recorded "
                        "reasoning stream when live SSE falters. "
                        "<b>scripts/smoke_railway.sh</b> validates "
                        "<b>/health</b>, <b>/triage</b>, <b>/sse</b>, "
                        "<b>/book</b> after every Railway deploy.",
                        style("sec_body",
                              fontName="Helvetica",
                              fontSize=9,
                              leading=12.5,
                              textColor=PALETTE["ink"],
                              alignment=TA_JUSTIFY))],
                ],
                colWidths=[8.0 * cm],
            ),
            Table(
                [
                    [Paragraph("SECURITY POSTURE",
                               style("sec_h",
                                     fontName="Helvetica-Bold",
                                     fontSize=10.5,
                                     leading=13,
                                     textColor=PALETTE["teal"]))],
                    [Paragraph(
                        "<b>X-Demo-Key</b> auth on /book and /outcome. "
                        "<b>PII_SALT</b> hashes patient_id before any "
                        "warehouse insert (deterministic but non-reversible). "
                        "A global <b>LogRecordFactory</b> redacts "
                        "<b>dapi*</b>, <b>sk-*</b>, and Fish-key shapes from "
                        "every log line and traceback before they hit any "
                        "handler. Failing-test-first discipline: every known "
                        "bug has a matching test in "
                        "<b>tests/test_known_bugs_*.py</b> that flips RED "
                        "&rarr; GREEN as the fix lands.",
                        style("sec_body2",
                              fontName="Helvetica",
                              fontSize=9,
                              leading=12.5,
                              textColor=PALETTE["ink"],
                              alignment=TA_JUSTIFY))],
                ],
                colWidths=[8.0 * cm],
            ),
        ]],
        colWidths=[8.4 * cm, 8.4 * cm],
    )
    safety_security.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 14),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    flow.append(safety_security)
    flow.append(PageBreak())

    flow += section_header("06  ·  RESULTS & IMPACT",
                           "What is on the table, what it changes.")
    flow.append(Paragraph(
        "Concrete artefacts, concrete metrics. Everything below is live and "
        "verifiable today.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 10))

    flow.append(Paragraph("LIVE METRICS", S_H2))
    flow.append(stat_row([
        ("20", "Foundation Model\nendpoints exposed", PALETTE["deep"]),
        ("4", "Specialties on\nDesert Map", PALETTE["coral"]),
        ("256", "Facilities\ntwo-model verified", PALETTE["teal"]),
        ("6", "Genie queries\nbrief-cited", PALETTE["amber"]),
    ]))
    flow.append(Spacer(1, 12))
    flow.append(stat_row([
        ("3,736", "PINs mapped\nwith severity tags", PALETTE["coral"]),
        ("4-tier", "Trust badge\nresolution", PALETTE["deep"]),
        ("100%", "/health uptime\non Railway", PALETTE["teal"]),
        ("$0.30", "LLM consensus\ncost / 256 facilities", PALETTE["amber"]),
    ]))
    flow.append(Spacer(1, 18))

    flow.append(Paragraph("DEMO ARC THAT SELLS THE LOOP", S_H2))
    flow.append(callout(
        "PATIENT JOURNEY  ·  60 SECONDS",
        "Hindi voice → triage classifies cardiology, urgency 4, fast_path → "
        "map shows 3 ranked hospitals with <b>verified</b> and "
        "<b>disagreement</b> badges → reserve clicked → 4 tiles light up → "
        "ambulance fails → all four tiles roll back live. No half-promise.",
        PALETTE["coral"],
    ))
    flow.append(Spacer(1, 8))
    flow.append(callout(
        "OUTCOME LOOP  ·  THE LEARNING MOMENT",
        "Switch to Doctor Copilot. Aradhna's clinic, trust 0.831 last week. "
        "Six negative patient outcomes recorded. Trust now 0.350. The next "
        "patient will not be routed there. The system learns in real time.",
        PALETTE["amber"],
    ))
    flow.append(Spacer(1, 8))
    flow.append(callout(
        "NGO MOMENT  ·  GENIE NL → SQL",
        "Type ‘Bihar PINs with zero oncology’ into the Genie panel. Output: "
        "executable SQL, 5 rows from <b>gold_pin_capabilities</b>, headline "
        "<b>97.4% of Bihar PINs uncovered</b>, ~104M people affected. "
        "Density is not access.",
        PALETTE["teal"],
    ))
    flow.append(Spacer(1, 16))

    flow.append(PageBreak())

    flow += section_header("07  ·  TECHNICAL VIDEO PRESENTATION",
                           "Full narration script — 90 seconds.")
    flow.append(Paragraph(
        "Read straight to camera. Times are cumulative. Every claim has a "
        "live endpoint or warehouse table behind it.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 12))

    script_rows = [
        ("0:00 — 0:08", "HOOK  ·  hold on the patient screen",
         "“When someone has a heart attack in Mumbai, Google Maps shows the "
         "nearest hospital. Nearest is not best. AarogyaNet guides patients "
         "to the right care at the right time.”"),
        ("0:08 — 0:22", "PATIENT DEMO  ·  voice triage",
         "Speak Hindi into the patient screen. Voice transcribes, /triage "
         "returns specialty=cardiology, urgency=4, fast_path=true, "
         "red_flag_match=[chest pain]. The map renders three ranked "
         "hospitals with trust badges — verified, single-source, "
         "disagreement. Cost and ETA visible on each card."),
        ("0:22 — 0:38", "ATOMIC SAGA  ·  the drama",
         "Click reserve. Four tiles light up in sequence: bed ✓, doctor ✓, "
         "drug ✓, ambulance ✗. All four tiles roll back live. “If even one "
         "resource fails — we do not promise the patient anything we cannot "
         "deliver.”"),
        ("0:38 — 0:52", "OUTCOME LOOP  ·  trust learns",
         "Swipe to Doctor Copilot. “This clinic was trust 0.831 last week. "
         "Six negative patient outcomes later — 0.350. Trust learns in real "
         "time. Most demos cut off here. Ours does not.”"),
        ("0:52 — 1:08", "NGO + GENIE  ·  the second product",
         "Switch to NGO Dashboard. “Maharashtra has 1,492 facilities — and "
         "403 PINs with zero oncology. Density is not access.” Open the "
         "Genie panel. Type ‘Bihar PINs with zero oncology.’ Genie returns "
         "the SQL, the rows, the headline: 97.4% uncovered, 104M people."),
        ("1:08 — 1:22", "TRUST CONSENSUS  ·  the moat",
         "Hold on a disagreement badge. “Llama 3.3 said 0.80 on bed "
         "availability. Llama 4 Maverick said 0.00. We do not silently "
         "average. We surface the disagreement and route it for human "
         "review. Two-model consensus, four-tier badge, ~$0.30 of LLM cost "
         "for 256 facilities.”"),
        ("1:22 — 1:30", "CLOSE  ·  one line",
         "“Three apps, one Databricks lakehouse, one closed loop: triage, "
         "rank, book, learn. <b>AarogyaNet — guide care, don't just map "
         "it.</b>”"),
    ]

    S_TBL_TIME = style(
        "tbl_time",
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=11,
        textColor=PALETTE["coral"],
    )
    script_table = Table(
        [[P("Time", S_TBL_HEAD), P("Beat", S_TBL_HEAD),
          P("Narration", S_TBL_HEAD)]] +
        [[P(t, S_TBL_TIME), P(b, S_TBL_BOLD), P(n)]
         for t, b, n in script_rows],
        colWidths=[2.4 * cm, 4.2 * cm, 10.4 * cm],
    )
    script_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["deep"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [PALETTE["paper"], PALETTE["sand"]]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, PALETTE["coral"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    flow.append(script_table)
    flow.append(Spacer(1, 16))

    flow.append(Paragraph("DELIVERY NOTES FOR THE TECHNICAL VIDEO", S_H2))
    flow.append(Paragraph(
        "Speak slow on the rollback (0:30 — 0:38). The four-tile sequence "
        "is the visual centerpiece — let it breathe. On the Genie segment, "
        "type the question into the live UI rather than narrating over a "
        "still: judges remember the moment SQL appears under a Hindi "
        "place-name. Keep the closing line on the screen for two beats "
        "before fade.",
        S_BODY,
    ))
    flow.append(PageBreak())

    flow += section_header("08  ·  CLOSING",
                           "One tagline. One promise. One repo.")
    flow.append(Spacer(1, 30))
    flow.append(Paragraph(
        '“Guide care, don\'t just map it.”',
        style("close",
              fontName="Helvetica-Bold",
              fontSize=30,
              leading=36,
              textColor=PALETTE["deep"],
              alignment=TA_CENTER,
              spaceAfter=24),
    ))
    flow.append(Spacer(1, 10))
    flow.append(Paragraph(
        "AarogyaNet is the loop the brief asks for: triage, rank, book, learn. "
        "Three apps, one Databricks lakehouse, every recommendation grounded "
        "in calibrated trust, every booking atomic, every outcome fed back "
        "into the next decision.",
        style("close_body",
              fontName="Helvetica",
              fontSize=12,
              leading=18,
              textColor=PALETTE["ink"],
              alignment=TA_CENTER),
    ))
    flow.append(Spacer(1, 28))

    closing_links = Table(
        [
            [Paragraph("LIVE API", S_KICKER),
             Paragraph(
                 'https://aarogyanet-api-production.up.railway.app',
                 style("link",
                       fontName="Helvetica",
                       fontSize=10,
                       leading=13,
                       textColor=PALETTE["deep"]))],
            [Paragraph("WEB APP", S_KICKER),
             Paragraph(
                 'https://app-wine-pi.vercel.app',
                 style("link2",
                       fontName="Helvetica",
                       fontSize=10,
                       leading=13,
                       textColor=PALETTE["deep"]))],
            [Paragraph("WORKSPACE", S_KICKER),
             Paragraph(
                 'Databricks  ·  dbc-17e9d40d-5056  ·  warehouse 10fff96dd6d936b5',
                 style("link3",
                       fontName="Helvetica",
                       fontSize=10,
                       leading=13,
                       textColor=PALETTE["ink"]))],
            [Paragraph("STACK", S_KICKER),
             Paragraph(
                 'Databricks Vector Search  ·  Foundation Model APIs  ·  '
                 'Genie  ·  SQL Warehouse  ·  MLflow Agent Bricks',
                 style("link4",
                       fontName="Helvetica",
                       fontSize=10,
                       leading=13,
                       textColor=PALETTE["ink"]))],
            [Paragraph("TEAM", S_KICKER),
             Paragraph(
                 'AarogyaNet  ·  4 contributors  ·  HackNation 2026',
                 style("link5",
                       fontName="Helvetica",
                       fontSize=10,
                       leading=13,
                       textColor=PALETTE["ink"]))],
        ],
        colWidths=[3.6 * cm, 13.1 * cm],
    )
    closing_links.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["sand"]),
        ("BOX", (0, 0), (-1, -1), 0.5, PALETTE["rule"]),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, PALETTE["rule"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    flow.append(closing_links)
    flow.append(Spacer(1, 28))
    flow.append(Paragraph(
        "Built for HackNation 2026  ·  Challenge 3  ·  Databricks Agentic "
        "Healthcare Maps.",
        style("footer_close",
              fontName="Helvetica",
              fontSize=9,
              leading=12,
              textColor=PALETTE["muted"],
              alignment=TA_CENTER),
    ))

    doc.build(flow)
    print(f"Wrote {out}")


if __name__ == "__main__":
    build()
