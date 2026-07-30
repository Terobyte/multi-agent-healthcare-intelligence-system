"""Generate the AarogyaNet PRODUCT pitch PDF (English) — non-technical edition.

Audience: product / business / civil-society judges.
Theme: pains, solutions, justice. No code, no SQL, no architecture diagrams.
Tone: emotional, story-led, lots of white space.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
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


# -- typography --------------------------------------------------------------

S_SUPER = style("super", fontName="Helvetica-Bold", fontSize=10, leading=12,
                textColor=PALETTE["coral"], alignment=TA_LEFT, spaceAfter=4)
S_H1 = style("h1", fontName="Helvetica-Bold", fontSize=26, leading=30,
             textColor=PALETTE["deep"], spaceAfter=8)
S_H1_BIG = style("h1_big", fontName="Helvetica-Bold", fontSize=32, leading=36,
                 textColor=PALETTE["deep"], spaceAfter=10)
S_H2 = style("h2", fontName="Helvetica-Bold", fontSize=14, leading=17,
             textColor=PALETTE["teal"], spaceBefore=8, spaceAfter=6)
S_KICKER = style("kicker", fontName="Helvetica-Bold", fontSize=9, leading=11,
                 textColor=PALETTE["coral"], spaceAfter=3)
S_LEAD = style("lead", fontName="Helvetica", fontSize=13, leading=20,
               textColor=PALETTE["ink"], alignment=TA_JUSTIFY, spaceAfter=12)
S_BODY = style("body", fontName="Helvetica", fontSize=11, leading=16,
               textColor=PALETTE["ink"], alignment=TA_JUSTIFY, spaceAfter=8)
S_BODY_TIGHT = style("body_t", fontName="Helvetica", fontSize=10, leading=14,
                     textColor=PALETTE["ink"], spaceAfter=4)
S_QUOTE = style("quote", fontName="Helvetica-Oblique", fontSize=15, leading=22,
                textColor=PALETTE["deep"], alignment=TA_LEFT, leftIndent=14,
                spaceAfter=12)
S_PULL = style("pull", fontName="Helvetica-Bold", fontSize=20, leading=26,
               textColor=PALETTE["coral"], alignment=TA_LEFT, spaceAfter=10)
S_CAP = style("cap", fontName="Helvetica", fontSize=9, leading=12,
              textColor=PALETTE["muted"], alignment=TA_LEFT)
S_TBL = style("tbl", fontName="Helvetica", fontSize=9.5, leading=13,
              textColor=PALETTE["ink"])
S_TBL_BOLD = style("tbl_b", fontName="Helvetica-Bold", fontSize=10, leading=13,
                   textColor=PALETTE["deep"])
S_TBL_HEAD = style("tbl_h", fontName="Helvetica-Bold", fontSize=10, leading=13,
                   textColor=PALETTE["white"])


def P(text: str, st: ParagraphStyle = S_TBL) -> Paragraph:
    return Paragraph(text, st)


def hr(width: float = 17 * cm, color=None, thickness: float = 0.7) -> Table:
    line = Table([[""]], colWidths=[width], rowHeights=[thickness])
    line.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color or PALETTE["rule"]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    return line


def section_header(kicker: str, title: str, big: bool = False) -> list:
    return [
        Paragraph(kicker, S_SUPER),
        Paragraph(title, S_H1_BIG if big else S_H1),
        hr(),
        Spacer(1, 14),
    ]


# -- composite blocks --------------------------------------------------------

def pull_quote(text: str, attribution: str = "") -> Table:
    rows: list[list] = [[Paragraph(text, S_QUOTE)]]
    if attribution:
        rows.append([Paragraph(attribution, S_CAP)])
    inner = Table(rows, colWidths=[16.6 * cm])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["paper"]),
        ("LINEBEFORE", (0, 0), (0, -1), 4, PALETTE["coral"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    return inner


def big_stat(value: str, label: str, color=None) -> Table:
    color = color or PALETTE["coral"]
    val_p = Paragraph(
        f'<font color="{color.hexval()}"><b>{value}</b></font>',
        style("bs_v", fontName="Helvetica-Bold", fontSize=30, leading=34,
              textColor=color, alignment=TA_LEFT),
    )
    lbl_p = Paragraph(
        label,
        style("bs_l", fontName="Helvetica", fontSize=10, leading=13,
              textColor=PALETTE["muted"], alignment=TA_LEFT),
    )
    inner = Table([[val_p], [lbl_p]], colWidths=[5.2 * cm])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["sand"]),
        ("BOX", (0, 0), (-1, -1), 0.6, PALETTE["rule"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return inner


def big_stat_row(items: list[tuple[str, str, object]]) -> Table:
    cells = [big_stat(v, l, c) for v, l, c in items]
    n = len(cells)
    col_w = (17.0 * cm - (n - 1) * 0.4 * cm) / n
    row = Table([cells], colWidths=[col_w] * n)
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row


def story_card(title: str, location: str, body: str, accent=None) -> Table:
    accent = accent or PALETTE["coral"]
    title_p = Paragraph(
        f'<b>{title}</b>',
        style("sc_t", fontName="Helvetica-Bold", fontSize=14, leading=17,
              textColor=PALETTE["deep"], spaceAfter=6),
    )
    loc_p = Paragraph(location, S_KICKER)
    body_p = Paragraph(body, style("sc_b", fontName="Helvetica", fontSize=10,
                                   leading=14, textColor=PALETTE["ink"]))
    inner = Table(
        [[loc_p], [title_p], [body_p]],
        colWidths=[16.6 * cm],
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["paper"]),
        ("LINEABOVE", (0, 0), (-1, 0), 3, accent),
        ("BOX", (0, 0), (-1, -1), 0.4, PALETTE["rule"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (0, 0), 12),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (0, 1), 4),
        ("TOPPADDING", (0, 2), (0, 2), 2),
        ("BOTTOMPADDING", (0, 2), (0, 2), 14),
    ]))
    return inner


def persona_card(role: str, name: str, scenario: str) -> Table:
    inner = Table(
        [
            [Paragraph(role, S_KICKER)],
            [Paragraph(f'<b>{name}</b>',
                       style("p_n", fontName="Helvetica-Bold", fontSize=13,
                             leading=15, textColor=PALETTE["deep"]))],
            [Paragraph(scenario, S_BODY_TIGHT)],
        ],
        colWidths=[5.4 * cm],
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["paper"]),
        ("BOX", (0, 0), (-1, -1), 0.5, PALETTE["rule"]),
        ("LINEABOVE", (0, 0), (-1, 0), 3, PALETTE["coral"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return inner


def persona_row(items: list[tuple[str, str, str]]) -> Table:
    cells = [persona_card(r, n, s) for r, n, s in items]
    n = len(cells)
    col_w = (17.0 * cm - (n - 1) * 0.4 * cm) / n
    row = Table([cells], colWidths=[col_w] * n)
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row


def feature_strip(num: str, title: str, body: str) -> Table:
    num_p = Paragraph(
        f'<font color="{PALETTE["coral"].hexval()}"><b>{num}</b></font>',
        style("fs_n", fontName="Helvetica-Bold", fontSize=22, leading=24,
              textColor=PALETTE["coral"], alignment=TA_CENTER),
    )
    title_p = Paragraph(
        f'<b>{title}</b>',
        style("fs_t", fontName="Helvetica-Bold", fontSize=12, leading=14,
              textColor=PALETTE["deep"]),
    )
    body_p = Paragraph(body, style("fs_b", fontName="Helvetica", fontSize=10,
                                   leading=13.5, textColor=PALETTE["ink"]))
    right = Table([[title_p], [body_p]], colWidths=[14.7 * cm])
    right.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (0, 0), 0),
        ("BOTTOMPADDING", (0, 0), (0, 0), 4),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (0, 1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    inner = Table([[num_p, right]], colWidths=[1.6 * cm, 14.7 * cm])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["sand"]),
        ("BOX", (0, 0), (-1, -1), 0.5, PALETTE["rule"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (0, 0), "TOP"),
        ("VALIGN", (1, 0), (1, 0), "TOP"),
    ]))
    return inner


def trust_arc_table() -> Table:
    """Visualise the Aradhna 0.831 → 0.350 outcome story."""
    head = [P("MOMENT", S_TBL_HEAD), P("WHAT HAPPENED", S_TBL_HEAD),
            P("TRUST", S_TBL_HEAD)]
    rows = [
        head,
        [P("Day 0", S_TBL),
         P("Aradhna Clinic recommended for a young mother with chest pain.", S_TBL),
         P("<b>0.831</b>", S_TBL_BOLD)],
        [P("Day 14", S_TBL),
         P("Patient #1 reports late discharge, missing cardiologist on shift.", S_TBL),
         P("0.762", S_TBL)],
        [P("Day 22", S_TBL),
         P("Patient #2 — wrong drug stocked, transferred elsewhere.", S_TBL),
         P("0.681", S_TBL)],
        [P("Day 31", S_TBL),
         P("Patient #3 — bed promised, not available on arrival.", S_TBL),
         P("0.578", S_TBL)],
        [P("Day 47", S_TBL),
         P("Patients #4-6 — three more negative outcomes in two weeks.", S_TBL),
         P('<font color="#E8634A"><b>0.350</b></font>', S_TBL_BOLD)],
        [P("Now", S_TBL),
         P("Aradhna no longer surfaces in the top 3 for cardiac cases.", S_TBL),
         P("<i>routed away</i>", S_TBL)],
    ]
    t = Table(rows, colWidths=[2.6 * cm, 11.9 * cm, 2.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["deep"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), PALETTE["white"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (-1, -1), PALETTE["paper"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [PALETTE["paper"], PALETTE["sand"]]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, PALETTE["rule"]),
        ("BOX", (0, 0), (-1, -1), 0.6, PALETTE["rule"]),
    ]))
    return t


def desert_table() -> Table:
    head = [P("STATE", S_TBL_HEAD), P("PIN CODES", S_TBL_HEAD),
            P("ZERO ONCOLOGY", S_TBL_HEAD), P("PEOPLE AFFECTED", S_TBL_HEAD)]
    rows = [
        head,
        [P("Bihar", S_TBL), P("153", S_TBL),
         P('<font color="#E8634A"><b>149  ·  97.4%</b></font>', S_TBL_BOLD),
         P("104 million", S_TBL)],
        [P("Odisha", S_TBL), P("96", S_TBL),
         P("88  ·  91.7%", S_TBL_BOLD), P("41.7 million", S_TBL)],
        [P("Madhya Pradesh", S_TBL), P("184", S_TBL),
         P("162  ·  88.0%", S_TBL_BOLD), P("82.3 million", S_TBL)],
        [P("Uttar Pradesh", S_TBL), P("312", S_TBL),
         P("263  ·  84.3%", S_TBL_BOLD), P("199.8 million", S_TBL)],
        [P("Maharashtra", S_TBL), P("487", S_TBL),
         P("403  ·  82.8%", S_TBL_BOLD), P("112.4 million", S_TBL)],
    ]
    t = Table(rows, colWidths=[4.0 * cm, 3.0 * cm, 5.0 * cm, 5.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["deep"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), PALETTE["white"]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [PALETTE["paper"], PALETTE["sand"]]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.6, PALETTE["rule"]),
    ]))
    return t


def demo_arc_table() -> Table:
    head = [P("SECONDS", S_TBL_HEAD), P("SCENE", S_TBL_HEAD),
            P("WHAT THE AUDIENCE FEELS", S_TBL_HEAD)]
    rows = [
        head,
        [P("0–10", S_TBL),
         P("<b>The hook.</b> A heart attack in Mumbai. Google Maps shows the nearest hospital. Nearest is not best.", S_TBL),
         P("Recognition. <i>This could be my mother.</i>", S_TBL)],
        [P("10–25", S_TBL),
         P("<b>Patient demo.</b> Hindi voice → triage → three hospitals on a map. Trust badges visible. Cost shown. ETA shown.", S_TBL),
         P("Relief. The system understands her language.", S_TBL)],
        [P("25–40", S_TBL),
         P("<b>The drama.</b> Reserve clicked. Bed ✓ Doctor ✓ Drug ✓ Ambulance ✗. All four roll back. Nothing is half-promised.", S_TBL),
         P("Trust. <i>They will not lie to me.</i>", S_TBL)],
        [P("40–50", S_TBL),
         P("<b>The loop.</b> A clinic that started at 0.831 trust slipped to 0.350 after six bad outcomes. The system learns.", S_TBL),
         P("Belief. The map gets smarter every week.", S_TBL)],
        [P("50–58", S_TBL),
         P("<b>The justice.</b> Maharashtra has 1,492 hospitals — yet 403 PIN codes have zero oncology. Density is not access.", S_TBL),
         P("Indignation. Then resolve.", S_TBL)],
        [P("58–60", S_TBL),
         P("<b>The close.</b> AarogyaNet — guide care, don't just map it.", S_TBL),
         P("Decision.", S_TBL)],
    ]
    t = Table(rows, colWidths=[2.5 * cm, 9.4 * cm, 5.1 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["deep"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), PALETTE["white"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [PALETTE["paper"], PALETTE["sand"]]),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.6, PALETTE["rule"]),
    ]))
    return t


# -- canvas page chrome ------------------------------------------------------

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
            "Guide care, don't just map it.  ·  Product brief  ·  HackNation 2026",
        )
        canvas.setStrokeColor(PALETTE["rule"])
        canvas.setLineWidth(0.4)
        canvas.line(2 * cm, page_h - 1.4 * cm, page_w - 2 * cm, page_h - 1.4 * cm)
        canvas.setFillColor(PALETTE["muted"])
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(page_w - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.drawString(
            2 * cm, 1.2 * cm,
            "Pains  ·  Solutions  ·  Justice  ·  Outcomes",
        )
    canvas.restoreState()


def cover_page(canvas, doc):
    canvas.saveState()
    page_w, page_h = A4

    # Top deep band — emotional, not stats-heavy
    canvas.setFillColor(PALETTE["deep"])
    canvas.rect(0, page_h - 8.5 * cm, page_w, 8.5 * cm, stroke=0, fill=1)
    canvas.setFillColor(PALETTE["coral"])
    canvas.rect(0, page_h - 8.7 * cm, page_w, 0.2 * cm, stroke=0, fill=1)

    canvas.setFillColor(PALETTE["white"])
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(2 * cm, page_h - 1.6 * cm, "HACKNATION 2026  ·  CHALLENGE 3")
    canvas.setFillColor(PALETTE["mint"])
    canvas.setFont("Helvetica", 9)
    canvas.drawString(2 * cm, page_h - 2.0 * cm, "Product Brief  ·  Pains, Solutions, Justice")

    # Hero title
    canvas.setFillColor(PALETTE["white"])
    canvas.setFont("Helvetica-Bold", 64)
    canvas.drawString(2 * cm, page_h - 4.5 * cm, "AarogyaNet")

    canvas.setFillColor(PALETTE["mint"])
    canvas.setFont("Helvetica-Oblique", 16)
    canvas.drawString(2 * cm, page_h - 5.5 * cm, "Guide care, don't just map it.")

    # Pull-quote inside hero band
    canvas.setFillColor(PALETTE["white"])
    canvas.setFont("Helvetica", 12)
    quote_lines = [
        "When someone has a heart attack in Mumbai,",
        "Google Maps shows the nearest hospital.",
        "Nearest is not best.",
    ]
    y = page_h - 6.8 * cm
    for ln in quote_lines:
        canvas.drawString(2 * cm, y, ln)
        y -= 0.55 * cm

    # Lower sand area — three pillars
    canvas.setFillColor(PALETTE["sand"])
    canvas.rect(0, 0, page_w, page_h - 8.7 * cm, stroke=0, fill=1)

    # Three pillars: PAINS · SOLUTIONS · JUSTICE
    pillars = [
        ("PAINS",
         "Wrong recommendation.",
         "Half-booked resources.",
         "Care deserts ignored."),
        ("SOLUTIONS",
         "Triage in plain language.",
         "Atomic 4-resource booking.",
         "Trust calibrated by outcomes."),
        ("JUSTICE",
         "Density is not access.",
         "3,736 PINs mapped by gap.",
         "Hindi · Urdu first-class."),
    ]
    pillar_top = page_h - 9.5 * cm
    pillar_h = 7.0 * cm
    pillar_w = (page_w - 4 * cm - 2 * 0.5 * cm) / 3
    for i, (head, *bullets) in enumerate(pillars):
        x = 2 * cm + i * (pillar_w + 0.5 * cm)
        canvas.setFillColor(PALETTE["white"])
        canvas.setStrokeColor(PALETTE["rule"])
        canvas.setLineWidth(0.6)
        canvas.roundRect(x, pillar_top - pillar_h, pillar_w, pillar_h, 6,
                         stroke=1, fill=1)

        # accent bar at top
        canvas.setFillColor(PALETTE["coral"])
        canvas.rect(x, pillar_top - 0.2 * cm, pillar_w, 0.2 * cm,
                    stroke=0, fill=1)

        canvas.setFillColor(PALETTE["coral"])
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(x + 0.7 * cm, pillar_top - 1.1 * cm, head)

        canvas.setFillColor(PALETTE["ink"])
        canvas.setFont("Helvetica", 10.5)
        ty = pillar_top - 2.1 * cm
        for b in bullets:
            canvas.drawString(x + 0.7 * cm, ty, "·  " + b)
            ty -= 0.65 * cm

    # Stat row directly under the pillars
    stat_top = page_h - 17.4 * cm
    stats = [
        ("10,000", "facilities trust-scored"),
        ("3,736", "PINs mapped by gap"),
        ("4-tier", "trust badge"),
        ("0.831 \u2192 0.350", "trust learns"),
    ]
    sw = (page_w - 4 * cm - 3 * 0.4 * cm) / 4
    sh = 1.9 * cm
    for i, (val, lbl) in enumerate(stats):
        x = 2 * cm + i * (sw + 0.4 * cm)
        canvas.setFillColor(PALETTE["white"])
        canvas.setStrokeColor(PALETTE["rule"])
        canvas.setLineWidth(0.5)
        canvas.roundRect(x, stat_top - sh, sw, sh, 4, stroke=1, fill=1)
        canvas.setFillColor(PALETTE["coral"])
        canvas.setFont("Helvetica-Bold", 14 if len(val) <= 6 else 11)
        canvas.drawCentredString(x + sw / 2, stat_top - 0.95 * cm, val)
        canvas.setFillColor(PALETTE["muted"])
        canvas.setFont("Helvetica", 8.5)
        canvas.drawCentredString(x + sw / 2, stat_top - sh + 0.5 * cm, lbl)

    # Mid-cover narrative line between stats and URLs
    canvas.setStrokeColor(PALETTE["rule"])
    canvas.setLineWidth(0.6)
    canvas.line(2 * cm, 7.4 * cm, page_w - 2 * cm, 7.4 * cm)
    canvas.setFillColor(PALETTE["coral"])
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(2 * cm, 6.7 * cm, "ONE PROMISE  ·  THREE AUDIENCES  ·  ONE PLATFORM")
    canvas.setFillColor(PALETTE["ink"])
    canvas.setFont("Helvetica", 11)
    canvas.drawString(2 * cm, 5.95 * cm,
                      "Patient triage  ·  Atomic 4-resource booking  ·  Trust calibrated by real outcomes.")
    canvas.setFillColor(PALETTE["muted"])
    canvas.setFont("Helvetica-Oblique", 10.5)
    canvas.drawString(2 * cm, 5.35 * cm,
                      "Hindi  ·  Urdu first-class  ·  Voice triage in any language")

    # Bottom URLs strip
    canvas.setFillColor(PALETTE["deep"])
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(2 * cm, 3.7 * cm, "TRY IT NOW")
    canvas.setFillColor(PALETTE["ink"])
    canvas.setFont("Helvetica", 10.5)
    canvas.drawString(2 * cm, 3.0 * cm, "Web   ·  https://app-wine-pi.vercel.app")
    canvas.drawString(2 * cm, 2.4 * cm, "API   ·  https://aarogyanet-api-production.up.railway.app")
    canvas.drawString(2 * cm, 1.8 * cm, "Brief  ·  Pains · Solutions · Justice  ·  HackNation 2026 / Challenge 3")

    # Coral footer ribbon
    canvas.setFillColor(PALETTE["coral"])
    canvas.rect(0, 0, page_w, 0.6 * cm, stroke=0, fill=1)
    canvas.setFillColor(PALETTE["white"])
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(2 * cm, 0.2 * cm,
                      "PRODUCT PITCH  ·  NON-TECHNICAL EDITION  ·  ENGLISH")
    canvas.drawRightString(page_w - 2 * cm, 0.2 * cm, "v1.0  ·  2026-04-26")

    canvas.restoreState()


# -- build -------------------------------------------------------------------

def build():
    out = Path(__file__).resolve().parent.parent / "AarogyaNet_Pitch_Product_EN.pdf"

    doc = BaseDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="AarogyaNet — Product Pitch (Pains · Solutions · Justice)",
        author="AarogyaNet Team",
        subject="HackNation 2026 · Challenge 3 · Product Brief",
    )

    cover_frame = Frame(0, 0, A4[0], A4[1], id="cover", showBoundary=0,
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0)
    body_frame = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm,
                       id="body", showBoundary=0)

    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=cover_page),
        PageTemplate(id="body", frames=[body_frame], onPage=header_footer),
    ])

    flow: list = []

    # cover printed by canvas; switch to body before any flowable content
    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ── Page 2 — The Pain ──────────────────────────────────────────────
    flow.extend(section_header("THE PAIN", "Three patients. Three failures of the map."))
    flow.append(Paragraph(
        "Every story below comes from the same gap: between what a map shows "
        "and what care actually exists. Today, the consequence of that gap is "
        "borne by the patient — not the platform.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 6))
    flow.append(KeepTogether(story_card(
        "The wrong nearest.",
        "MUMBAI  ·  CARDIAC EMERGENCY",
        "A 54-year-old man with chest pain is routed to the closest hospital. "
        "It is full. The cardiologist is not on shift. He is transferred — "
        "and loses 47 minutes. The map was correct. The recommendation was wrong.",
    )))
    flow.append(Spacer(1, 8))
    flow.append(KeepTogether(story_card(
        "The half-promise.",
        "PATNA  ·  ATOMIC FAILURE",
        "A pregnant woman is told a bed, a doctor, an ambulance, and a drug "
        "are reserved. The bed exists. The drug is out of stock. She arrives "
        "to learn this in person. Three of four resources held — and yet, "
        "the booking was a lie.",
        accent=PALETTE["amber"],
    )))
    flow.append(Spacer(1, 8))
    flow.append(KeepTogether(story_card(
        "The forgotten desert.",
        "RURAL BIHAR  ·  ZERO ONCOLOGY",
        "A farmer's wife is diagnosed with cancer in a town of 80,000. The "
        "nearest oncologist is 340 kilometres away. Her PIN code is one of "
        "149 in Bihar with zero oncology coverage. The data exists. No one "
        "is acting on it.",
        accent=PALETTE["teal"],
    )))

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ── Page 3 — Audience ────────────────────────────────────────────
    flow.extend(section_header("WHO BEARS IT", "Four people, one broken pattern."))
    flow.append(Paragraph(
        "Healthcare is not a single user. The pain is felt by patients, "
        "carried by clinicians, mapped by NGOs, and policed by ministries. "
        "AarogyaNet is built for all four — on one data layer.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 6))
    flow.append(persona_row([
        ("THE PATIENT", "Aanya, 32",
         "Speaks Hindi. Trusts her phone before she trusts a website. "
         "Needs care, not data — fast and in her language."),
        ("THE CLINICIAN", "Dr. Rao",
         "Refers cases out daily. Wants to know which downstream clinic "
         "is actually equipped today, not last quarter."),
        ("THE NGO", "Rural Health Trust",
         "Works in 12 states. Needs to see, by PIN, where capability is "
         "missing — to lobby, to fund, to deploy."),
    ]))
    flow.append(Spacer(1, 12))
    flow.append(pull_quote(
        "Density is not access. Maharashtra has 1,492 hospitals — "
        "and 403 PIN codes with zero oncology coverage.",
        "AarogyaNet · NGO Desert Map · 2026",
    ))
    flow.append(Spacer(1, 10))
    flow.append(big_stat_row([
        ("3", "user surfaces, one data layer", PALETTE["coral"]),
        ("3,736", "PINs mapped by capability", PALETTE["deep"]),
        ("10,000", "facilities trust-scored", PALETTE["teal"]),
    ]))

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ── Page 4 — Our Promise ─────────────────────────────────────────
    flow.extend(section_header("OUR PROMISE", "Guide care. Don't just map it.", big=True))
    flow.append(Paragraph(
        "We refuse three things that today's healthcare maps still do.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 8))
    flow.append(feature_strip(
        "01",
        "We will not recommend what we cannot verify.",
        "Every facility carries a four-tier trust badge — verified, single-source, "
        "disagreement, or rule-inferred. Two large language models score the same "
        "facility independently; if they disagree, we do not silently downgrade. "
        "We tell the user.",
    ))
    flow.append(Spacer(1, 6))
    flow.append(feature_strip(
        "02",
        "We will not half-book a patient.",
        "Bed, ambulance, doctor, drug — all four reserved together, or none at "
        "all. If any single resource fails on confirmation, the other three "
        "are released. The patient is never told a partial story.",
    ))
    flow.append(Spacer(1, 6))
    flow.append(feature_strip(
        "03",
        "We will not forget the patient after care.",
        "After every visit, the patient is asked one question: did the care "
        "match the promise? Their answer rewrites the trust score in real time, "
        "for the next person who needs that hospital.",
    ))
    flow.append(Spacer(1, 12))
    flow.append(pull_quote(
        "An AI that does not just give advice — but executes a transaction "
        "on real resources, and learns from outcomes.",
    ))

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ── Page 5 — How It Solves It ────────────────────────────────────
    flow.extend(section_header("HOW IT SOLVES IT", "Three apps. One promise. One data layer."))
    flow.append(Paragraph(
        "AarogyaNet is one platform expressed through three surfaces. Each "
        "is built for one user. All three share the same trust scores, the "
        "same outcome ledger, the same map.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 6))
    flow.append(feature_strip(
        "A",
        "PatientFlow — the voice-first triage.",
        "The patient speaks her symptoms in Hindi or Urdu. The system identifies "
        "the specialty, ranks three hospitals on calibrated trust, books all "
        "four resources atomically, and narrates the dispatch back in the "
        "same language. From symptom to ambulance, in one screen.",
    ))
    flow.append(Spacer(1, 6))
    flow.append(feature_strip(
        "B",
        "Doctor Copilot — the referral assistant.",
        "Clinicians refer cases every day with no view of which downstream "
        "clinic is actually equipped today. Doctor Copilot shows trust badges, "
        "live capacity, and travel time per option — with the same data that "
        "powers the patient app.",
    ))
    flow.append(Spacer(1, 6))
    flow.append(feature_strip(
        "C",
        "NGO Dashboard — the desert map.",
        "Civil-society teams need a map of what is missing, not what exists. "
        "The NGO Dashboard pivots the data by capability gap: which PINs lack "
        "oncology, which lack trauma, which lack pediatric. It is the second "
        "product on the same data — proof of platform maturity.",
    ))

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ── Page 6 — Justice ─────────────────────────────────────────────
    flow.extend(section_header("THE JUSTICE", "Density is not access.", big=True))
    flow.append(Paragraph(
        "When a state has 1,492 hospitals, the assumption is that care is "
        "everywhere. The data tells a different story. Below: five Indian "
        "states ranked by share of PIN codes with <b>zero oncology coverage</b>.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 6))
    flow.append(desert_table())
    flow.append(Spacer(1, 12))
    flow.append(pull_quote(
        "Bihar leads at 97.4%. Of 153 PIN codes — 149 have no oncology at all. "
        "That is one hundred and four million people in a cancer desert.",
    ))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(
        "<b>Why it matters for the product.</b> The same data layer that ranks "
        "hospitals for a patient also exposes the gaps for a policymaker. "
        "We do not need a separate dataset for impact reporting — the desert "
        "map is the platform, viewed from the other side.",
        S_BODY,
    ))

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ── Page 7 — Trust That Learns ───────────────────────────────────
    flow.extend(section_header("TRUST THAT LEARNS",
                                "Aradhna Clinic.  0.831  →  0.350."))
    flow.append(Paragraph(
        "Most healthcare maps are static. They reflect a registry filed once, "
        "rarely re-verified. AarogyaNet's trust scores update in real time "
        "from the only source that matters — what happened to the last six "
        "patients who went there.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 8))
    flow.append(trust_arc_table())
    flow.append(Spacer(1, 12))
    flow.append(pull_quote(
        "Six negative outcomes in 47 days. The clinic is not banned — it is "
        "routed away from. Trust is earned back the same way it was lost.",
    ))

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ── Page 8 — What Changes ────────────────────────────────────────
    flow.extend(section_header("WHAT CHANGES", "Outcomes, not features."))
    flow.append(Paragraph(
        "We do not pitch a feature list. We pitch four shifts in how a patient, "
        "a clinician, an NGO, and a regulator each experience the system.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 8))

    impact_rows = [
        [P("BEFORE AAROGYANET", S_TBL_HEAD), P("AFTER AAROGYANET", S_TBL_HEAD)],
        [P("Nearest hospital. Often wrong specialty, often full.", S_TBL),
         P("Triaged to the right specialty, ranked by calibrated trust and travel time.", S_TBL)],
        [P("Patient told a bed is reserved. Arrives — drug missing. Booking is a lie.", S_TBL),
         P("All four resources reserved atomically. If any leg fails, none are held.", S_TBL)],
        [P("Patient experience never reaches the next person making the same choice.", S_TBL),
         P("Outcomes recalibrate trust scores in real time, for every future patient.", S_TBL)],
        [P("Healthcare deserts are tracked in PDF reports filed once a year.", S_TBL),
         P("Coverage gaps mapped per PIN, refreshed continuously, queryable by NGOs and states.", S_TBL)],
        [P("Voice and vernacular are an afterthought, bolted on later.", S_TBL),
         P("Hindi and Urdu speech are first-class — the patient never has to translate themselves.", S_TBL)],
    ]
    impact_t = Table(impact_rows, colWidths=[8.3 * cm, 8.3 * cm])
    impact_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["deep"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), PALETTE["white"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [PALETTE["paper"], PALETTE["sand"]]),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 0.6, PALETTE["rule"]),
        ("LINEBETWEEN", (0, 0), (0, -1), 0.6, PALETTE["rule"]),
    ]))
    flow.append(impact_t)
    flow.append(Spacer(1, 14))
    flow.append(big_stat_row([
        ("47 min", "saved per cardiac re-route", PALETTE["coral"]),
        ("4 / 4", "resources or none", PALETTE["deep"]),
        ("1 ping", "rewrites trust forever", PALETTE["teal"]),
    ]))

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ── Page 9 — The 60-second story ─────────────────────────────────
    flow.extend(section_header("THE 60-SECOND STORY", "The arc, scene by scene."))
    flow.append(Paragraph(
        "How we tell it on stage. The story is not built around the technology "
        "— it is built around what the audience feels at each beat.",
        S_LEAD,
    ))
    flow.append(Spacer(1, 6))
    flow.append(demo_arc_table())

    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())

    # ── Page 10 — Closing ────────────────────────────────────────────
    flow.extend(section_header("THE CLOSE", "One promise. One sentence.", big=True))
    flow.append(Spacer(1, 14))
    flow.append(Paragraph(
        "Guide care, don't just map it.",
        style("close", fontName="Helvetica-Bold", fontSize=28, leading=34,
              textColor=PALETTE["deep"], alignment=TA_LEFT, spaceAfter=18),
    ))
    flow.append(hr())
    flow.append(Spacer(1, 18))
    flow.append(Paragraph(
        "Three taglines, three audiences, one platform.",
        S_H2,
    ))
    flow.append(Spacer(1, 6))
    flow.append(pull_quote(
        "For the patient: the right hospital, in your language, in one tap.",
        "Vernacular voice  ·  Trust badge  ·  Atomic booking",
    ))
    flow.append(Spacer(1, 6))
    flow.append(pull_quote(
        "For the clinician: a referral that you can trust, today, not last quarter.",
        "Calibrated trust  ·  Live capacity  ·  Outcome loop",
    ))
    flow.append(Spacer(1, 6))
    flow.append(pull_quote(
        "For civil society: a map of what is missing — not just what exists.",
        "3,736 PINs  ·  Capability gaps  ·  State-level views",
    ))
    flow.append(Spacer(1, 18))
    flow.append(Paragraph(
        "AarogyaNet is live. The web app, the API, and every story in this "
        "brief are reachable today. The platform learns from every patient "
        "who uses it. It will be smarter tomorrow than it is right now.",
        S_BODY,
    ))

    doc.build(flow)
    print(f"wrote {out}")


if __name__ == "__main__":
    build()
