"""
Generates screenshot images for the blog.
Run from the project root: python blog/gen_screenshots.py
"""
import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.dsl.schema import Aggregation, Axis, Chart, VisualizationSpec
from core.renderer.image.image import ImageRenderer
from tools.query_tool import QueryTools

OUT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

# ── fetch real data ──────────────────────────────────────────────────────────
qt = QueryTools()
tools = {t.name: t for t in qt.get_tools()}
all_hotels = tools["list_all_hotels_with_offers"].invoke({})
renderer = ImageRenderer()


def save_png(spec: VisualizationSpec, data: list, filename: str) -> None:
    result = renderer.render(spec, data)
    b64 = result[len("data:image/png;base64,"):]
    path = os.path.join(OUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    print(f"  saved: {path}")


# ── chart images ─────────────────────────────────────────────────────────────
print("Generating chart images...")

save_png(VisualizationSpec(
    charts=[Chart(
        type="bar",
        x=Axis(field="town", type="dimension"),
        y=Axis(field="rating", type="measure"),
        aggregation=Aggregation(field="rating", op="avg"),
        title="Average Hotel Rating by Town",
    )],
    output="image",
), all_hotels, "bar_chart_ratings.png")

save_png(VisualizationSpec(
    charts=[Chart(
        type="horizontal_bar",
        x=Axis(field="hotel_name", type="dimension"),
        y=Axis(field="available_rooms", type="measure"),
        title="Available Rooms by Hotel",
    )],
    output="image",
), all_hotels, "horizontal_bar_rooms.png")

save_png(VisualizationSpec(
    charts=[Chart(
        type="grouped_bar",
        x=Axis(field="town", type="dimension"),
        y=Axis(field="price_single", type="measure"),
        y2=Axis(field="price_double", type="measure"),
        title="Single vs Double Room Prices by Town",
    )],
    output="image",
), all_hotels, "grouped_bar_prices.png")

save_png(VisualizationSpec(
    charts=[Chart(
        type="pie",
        x=Axis(field="hotel_name", type="dimension"),
        y=Axis(field="available_rooms", type="measure"),
        aggregation=Aggregation(field="available_rooms", op="sum"),
        title="Room Availability Distribution",
    )],
    output="image",
), all_hotels, "pie_rooms.png")

save_png(VisualizationSpec(
    charts=[Chart(
        type="bubble",
        x=Axis(field="price_single", type="measure"),
        y=Axis(field="rating", type="measure"),
        y2=Axis(field="available_rooms", type="measure"),
        title="Price vs Rating  (bubble size = available rooms)",
    )],
    output="image",
), all_hotels, "bubble_chart.png")

save_png(VisualizationSpec(
    charts=[Chart(
        type="gauge",
        x=Axis(field="hotel_name", type="dimension"),
        y=Axis(field="rating", type="measure"),
        aggregation=Aggregation(field="rating", op="avg"),
        title="Average Hotel Rating",
    )],
    output="image",
), all_hotels, "gauge_rating.png")

save_png(VisualizationSpec(
    charts=[Chart(
        type="heatmap",
        x=Axis(field="hotel_name", type="dimension"),
        y=Axis(field="rating", type="measure"),
        y2=Axis(field="price_single", type="measure"),
        title="Rating vs Single Room Price Heatmap",
    )],
    output="image",
), all_hotels, "heatmap.png")

save_png(VisualizationSpec(
    charts=[Chart(
        type="line",
        x=Axis(field="hotel_name", type="dimension"),
        y=Axis(field="rating", type="measure"),
        title="Hotel Ratings Trend",
    )],
    output="image",
), all_hotels, "line_chart.png")

# ── data table SVG ───────────────────────────────────────────────────────────
print("Generating data table SVG...")

DISPLAY_COLS = ["hotel_name", "town", "rating", "available_rooms", "price_single", "price_double"]
COL_LABELS   = ["Hotel Name", "Town", "Rating", "Rooms", "Single £", "Double £"]
COL_WIDTHS   = [190, 90, 58, 58, 68, 68]

rows = all_hotels[:6]
PAD      = 20
ROW_H    = 30
HEADER_H = 36
FOOTER_H = 40
LABEL_H  = 24
TABLE_W  = sum(COL_WIDTHS)
TOTAL_W  = TABLE_W + PAD * 2
TOTAL_H  = LABEL_H + HEADER_H + ROW_H * len(rows) + FOOTER_H + PAD * 2 + 10

lines = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TOTAL_W} {TOTAL_H}" '
    f'font-family="Inter, ui-sans-serif, system-ui" font-size="12">',
    # outer card
    f'<rect width="{TOTAL_W}" height="{TOTAL_H}" fill="#f1f5f9" rx="14"/>',
    f'<rect x="8" y="8" width="{TOTAL_W-16}" height="{TOTAL_H-16}" fill="white" rx="10" '
    f'stroke="#e2e8f0" stroke-width="1.5"/>',
    # agent label
    f'<text x="20" y="28" fill="#94a3b8" font-size="11" font-weight="500">Viz Agent</text>',
]

TX = PAD
TY = LABEL_H + PAD

# header
lines.append(f'<rect x="{TX}" y="{TY}" width="{TABLE_W}" height="{HEADER_H}" fill="#4f6ef7" rx="6"/>')
x = TX
for label, w in zip(COL_LABELS, COL_WIDTHS):
    lines.append(f'<text x="{x+10}" y="{TY+23}" fill="white" font-weight="600" font-size="11">{label}</text>')
    x += w

# rows
for ri, row in enumerate(rows):
    y = TY + HEADER_H + ri * ROW_H
    bg = "white" if ri % 2 == 0 else "#f8fafc"
    lines.append(f'<rect x="{TX}" y="{y}" width="{TABLE_W}" height="{ROW_H}" fill="{bg}"/>')
    lines.append(f'<line x1="{TX}" y1="{y}" x2="{TX+TABLE_W}" y2="{y}" stroke="#f1f5f9" stroke-width="1"/>')
    x = TX
    for col, w in zip(DISPLAY_COLS, COL_WIDTHS):
        val = str(row.get(col, ""))
        if col == "rating":
            color = "#16a34a" if float(val) >= 4.5 else "#0369a1"
            weight = "font-weight=\"600\""
        else:
            color = "#1e293b"
            weight = ""
        lines.append(f'<text x="{x+10}" y="{y+20}" fill="{color}" font-size="11" {weight}>{val}</text>')
        x += w

# bottom border
last_y = TY + HEADER_H + len(rows) * ROW_H
lines.append(f'<line x1="{TX}" y1="{last_y}" x2="{TX+TABLE_W}" y2="{last_y}" stroke="#e2e8f0" stroke-width="1"/>')

# footer
FY = last_y + 8
lines.append(f'<text x="{TX+4}" y="{FY+16}" fill="#94a3b8" font-size="10">10 records found</text>')

# CSV button
BX = TX + TABLE_W - 118
lines.append(f'<rect x="{BX}" y="{FY}" width="114" height="26" rx="6" fill="white" stroke="#e2e8f0" stroke-width="1.5"/>')
# download icon
lines.append(f'<line x1="{BX+12}" y1="{FY+6}" x2="{BX+12}" y2="{FY+14}" stroke="#64748b" stroke-width="1.5" stroke-linecap="round"/>')
lines.append(f'<polyline points="{BX+9},{FY+13} {BX+12},{FY+17} {BX+15},{FY+13}" fill="none" stroke="#64748b" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')
lines.append(f'<line x1="{BX+8}" y1="{FY+19}" x2="{BX+16}" y2="{FY+19}" stroke="#64748b" stroke-width="1.5" stroke-linecap="round"/>')
lines.append(f'<text x="{BX+24}" y="{FY+17}" fill="#475569" font-size="10" font-weight="500">Download CSV</text>')

lines.append("</svg>")

svg_path = os.path.join(OUT_DIR, "data_table.svg")
with open(svg_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"  saved: {svg_path}")

print("\nAll screenshots generated successfully.")
