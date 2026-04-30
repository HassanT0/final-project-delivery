"""Reports screen — generate and export inventory and sales reports.

Exports use the `reportlab` library to produce a branded LogicTrack PDF
with a header logo, summary block, and a styled data table. CSV export
is preserved for raw spreadsheet workflows.
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from typing import List, Sequence, Tuple

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle

from models import Item, SalesSummary


log = logging.getLogger("logictrack.reports")


REPORT_TYPES: Tuple[str, ...] = (
    "Low Stock", "Highest Selling", "Lowest Selling", "Expiration",
)


class _StatusPill(BoxLayout):
    def __init__(self, label: str, **kw) -> None:
        super().__init__(size_hint=(None, None), size=(96, 26),
                         padding=(10, 4), **kw)
        app = App.get_running_app()
        if label == "Critical":
            bg, fg = app.danger_bg, app.danger
        elif label == "Warning":
            bg, fg = app.warning_bg, app.warning
        else:
            bg, fg = app.success_bg, app.success
        with self.canvas.before:
            Color(*bg)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self.bind(pos=self._sync, size=self._sync)
        self.add_widget(Label(text=label, color=fg, font_size=12, bold=True))

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class ReportsScreen(Screen):
    last_results: List[Tuple[str, ...]] = []
    last_headers: Tuple[str, ...] = ()
    last_report_type: str = ""

    def on_pre_enter(self, *_) -> None:
        if not self.ids.report_type_input.text:
            self.ids.report_type_input.text = "Low Stock"
        if not self.ids.start_date.text:
            self.ids.start_date.text = "04/01/26"
        if not self.ids.end_date.text:
            self.ids.end_date.text = datetime.now().strftime("%m/%d/%y")

    # ----------------------------------------------------------- generate
    def generate_report(self) -> None:
        rtype = self.ids.report_type_input.text.strip() or "Low Stock"
        app = App.get_running_app()
        rows: List[Tuple[str, ...]] = []
        headers: Tuple[str, ...] = ()

        if rtype == "Low Stock":
            headers = ("Item", "Stock", "Threshold", "Status")
            t = int(app.low_stock_threshold)
            for item in app.db.low_stock(t):
                status = "Critical" if item.is_critical(t) else "Warning"
                rows.append((item.name, str(item.quantity), str(t), status))
        elif rtype in ("Highest Selling", "Lowest Selling"):
            headers = ("Item", "Units Sold")
            ascending = rtype == "Lowest Selling"
            for sale in app.db.top_items_by_sales(limit=10, ascending=ascending):
                rows.append((sale.item_name, str(sale.units_sold)))
        elif rtype == "Expiration":
            headers = ("Item", "Expires On", "SKU")
            for item in app.db.expiring_items(within_days=60):
                rows.append((item.name, item.expires_on or "—", item.sku))
            if not rows:
                rows = [("(No items expiring within 60 days)", "—", "—")]
        else:
            headers = ("Info",)
            rows = [(f"Unknown report type: {rtype}",)]

        self.last_headers = headers
        self.last_results = rows
        self.last_report_type = rtype
        self._render(headers, rows)

    def _render(self, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        app = App.get_running_app()
        table = self.ids.results_table
        table.clear_widgets()

        header_row = BoxLayout(size_hint_y=None, height=42, padding=(16, 0), spacing=12)
        with header_row.canvas.before:
            Color(*app.input_bg)
            hr = Rectangle(pos=header_row.pos, size=header_row.size)
        header_row.bind(pos=lambda *_: setattr(hr, "pos", header_row.pos),
                        size=lambda *_: setattr(hr, "size", header_row.size))
        for h in headers:
            header_row.add_widget(Label(
                text=h.upper(), color=app.muted_text_color, font_size=11,
                bold=True, halign="left", valign="middle",
                text_size=(180, None),
            ))
        table.add_widget(header_row)

        if not rows:
            empty = Label(text="No results.", color=app.muted_text_color,
                          size_hint_y=None, height=120,
                          halign="center", valign="middle")
            empty.bind(size=lambda i, *_: setattr(i, "text_size", i.size))
            table.add_widget(empty)
            table.add_widget(Widget())
            return

        for i, r in enumerate(rows):
            row = BoxLayout(size_hint_y=None, height=52, padding=(16, 0), spacing=12)
            bg = app.row_alt_bg if i % 2 == 1 else app.card_bg
            with row.canvas.before:
                Color(*bg)
                rect = Rectangle(pos=row.pos, size=row.size)
                Color(*app.divider)
                divider = Rectangle(pos=(row.x, row.y), size=(row.width, 1))
            row.bind(
                pos=lambda inst, _v, _r=rect, _d=divider:
                    (setattr(_r, "pos", inst.pos), setattr(_d, "pos", (inst.x, inst.y))),
                size=lambda inst, _v, _r=rect, _d=divider:
                    (setattr(_r, "size", inst.size), setattr(_d, "size", (inst.width, 1))),
            )

            for cell in r:
                if cell in ("Critical", "Warning"):
                    col = BoxLayout(padding=(0, 13))
                    col.add_widget(_StatusPill(cell))
                    row.add_widget(col)
                else:
                    lbl = Label(text=cell, color=app.text_color, font_size=13,
                                halign="left", valign="middle")
                    lbl.bind(size=lambda i, *_: setattr(i, "text_size", i.size))
                    row.add_widget(lbl)
            table.add_widget(row)

        table.add_widget(Widget())

    # ----------------------------------------------------------------- export
    def _toast(self, msg: str) -> None:
        Popup(title="Report", content=Label(text=msg),
              size_hint=(None, None), size=(460, 180)).open()

    def export_csv(self) -> None:
        if not self.last_results:
            self._toast("Generate a report first.")
            return
        try:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            path = os.path.abspath(filename)
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(self.last_headers)
                w.writerows(self.last_results)
            self._toast(f"Saved CSV to:\n{path}")
        except OSError as exc:
            log.exception("CSV export failed")
            self._toast(f"Could not save CSV: {exc}")

    # ----------------------------------------------------------------- pdf
    def export_pdf(self) -> None:
        if not self.last_results:
            self._toast("Generate a report first.")
            return
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
            )
        except ImportError:
            log.warning("reportlab not installed; falling back to plain text")
            self._export_plain_text_fallback()
            return

        try:
            filename = (
                f"LogicTrack_{self.last_report_type.replace(' ', '_')}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            path = os.path.abspath(filename)

            # Brand colours — keep in sync with style_manager / theme.
            brand_navy   = colors.HexColor("#1B2332")
            brand_indigo = colors.HexColor("#5863E8")
            brand_muted  = colors.HexColor("#6F7885")
            brand_border = colors.HexColor("#E8EAEF")
            brand_alt    = colors.HexColor("#F8FAFC")

            doc = SimpleDocTemplate(
                path,
                pagesize=LETTER,
                rightMargin=0.6 * inch, leftMargin=0.6 * inch,
                topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                title=f"LogicTrack {self.last_report_type} Report",
                author="LogicTrack",
            )
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "BrandTitle", parent=styles["Title"],
                textColor=brand_navy, fontSize=22, leading=26,
                alignment=0, spaceAfter=4,
            )
            subtitle_style = ParagraphStyle(
                "BrandSubtitle", parent=styles["Normal"],
                textColor=brand_muted, fontSize=11, leading=14,
                spaceAfter=12,
            )
            section_style = ParagraphStyle(
                "BrandSection", parent=styles["Heading2"],
                textColor=brand_indigo, fontSize=13, leading=16,
                spaceBefore=10, spaceAfter=6,
            )
            body_style = ParagraphStyle(
                "BrandBody", parent=styles["Normal"],
                textColor=brand_navy, fontSize=10, leading=14,
            )

            story = []

            # ---- header row: logo + brand wordmark
            header_cells = [[
                self._brand_logo_flowable(Image, inch),
                Paragraph(
                    "<b>LogicTrack</b><br/>"
                    "<font size=9 color='#6F7885'>Inventory Management</font>",
                    body_style,
                ),
                Paragraph(
                    f"<para align='right'><font size=9 color='#6F7885'>"
                    f"Generated {datetime.now().strftime('%b %d, %Y · %I:%M %p')}"
                    f"</font></para>",
                    body_style,
                ),
            ]]
            header_table = Table(header_cells, colWidths=[0.8 * inch, 3.4 * inch, 2.7 * inch])
            header_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.6, brand_border),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 14))

            # ---- title block
            story.append(Paragraph(
                f"{self.last_report_type} Report", title_style,
            ))
            story.append(Paragraph(
                f"A snapshot of {self.last_report_type.lower()} activity, "
                f"prepared by LogicTrack.",
                subtitle_style,
            ))

            # ---- summary metrics
            summary_rows = self._build_summary_rows()
            if summary_rows:
                story.append(Paragraph("Summary", section_style))
                summary_table = Table(summary_rows, colWidths=[2.6 * inch, 3.5 * inch])
                summary_table.setStyle(TableStyle([
                    ("FONT",        (0, 0), (-1, -1), "Helvetica", 10),
                    ("FONT",        (0, 0), (0, -1),  "Helvetica-Bold", 10),
                    ("TEXTCOLOR",   (0, 0), (0, -1),  brand_muted),
                    ("TEXTCOLOR",   (1, 0), (-1, -1), brand_navy),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING",(0, 0), (-1, -1), 8),
                    ("TOPPADDING",  (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING",(0, 0),(-1, -1), 6),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [brand_alt, colors.white]),
                    ("BOX",         (0, 0), (-1, -1), 0.5, brand_border),
                    ("INNERGRID",   (0, 0), (-1, -1), 0.25, brand_border),
                ]))
                story.append(summary_table)
                story.append(Spacer(1, 14))

            # ---- main data table
            story.append(Paragraph("Detail", section_style))
            table_data = [list(self.last_headers)] + [
                list(r) for r in self.last_results
            ]
            data_table = Table(
                table_data,
                colWidths=self._equal_col_widths(len(self.last_headers), 6.6 * inch),
                repeatRows=1,
            )
            data_style = TableStyle([
                # header row
                ("BACKGROUND",  (0, 0), (-1, 0), brand_indigo),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONT",        (0, 0), (-1, 0), "Helvetica-Bold", 10),
                ("ALIGN",       (0, 0), (-1, 0), "LEFT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING",(0, 0), (-1, -1), 8),
                ("TOPPADDING",  (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING",(0, 0),(-1, -1), 7),
                # body rows
                ("FONT",        (0, 1), (-1, -1), "Helvetica", 9.5),
                ("TEXTCOLOR",   (0, 1), (-1, -1), brand_navy),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, brand_alt]),
                ("LINEBELOW",   (0, 0), (-1, -1), 0.25, brand_border),
                ("BOX",         (0, 0), (-1, -1), 0.5, brand_border),
                ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ])
            # Highlight Critical / Warning status cells
            for r_idx, row in enumerate(self.last_results, start=1):
                for c_idx, cell in enumerate(row):
                    if cell == "Critical":
                        data_style.add("TEXTCOLOR", (c_idx, r_idx), (c_idx, r_idx),
                                       colors.HexColor("#D43B3B"))
                        data_style.add("FONT", (c_idx, r_idx), (c_idx, r_idx),
                                       "Helvetica-Bold", 9.5)
                    elif cell == "Warning":
                        data_style.add("TEXTCOLOR", (c_idx, r_idx), (c_idx, r_idx),
                                       colors.HexColor("#E38E0B"))
                        data_style.add("FONT", (c_idx, r_idx), (c_idx, r_idx),
                                       "Helvetica-Bold", 9.5)
            data_table.setStyle(data_style)
            story.append(data_table)

            # ---- footer
            story.append(Spacer(1, 24))
            story.append(Paragraph(
                "<para align='center'><font size=8 color='#6F7885'>"
                "© LogicTrack · Confidential — for internal distribution only."
                "</font></para>",
                body_style,
            ))

            doc.build(story)
            self._toast(f"Saved branded PDF to:\n{path}")
        except Exception as exc:
            log.exception("PDF export failed")
            self._toast(f"PDF export failed: {exc}")

    # --- helpers --------------------------------------------------------
    def _build_summary_rows(self) -> List[Tuple[str, str]]:
        app = App.get_running_app()
        rows: List[Tuple[str, str]] = [
            ("Report type",   self.last_report_type),
            ("Generated",     datetime.now().strftime("%B %d, %Y · %I:%M %p")),
            ("Row count",     str(len(self.last_results))),
        ]
        if self.last_report_type == "Low Stock":
            rows.append(("Threshold",
                         f"{int(app.low_stock_threshold)} units"))
        elif self.last_report_type in ("Highest Selling", "Lowest Selling"):
            rows.append(("Window", "Last 30 days · units sold"))
        elif self.last_report_type == "Expiration":
            rows.append(("Window", "Items expiring within 60 days"))
        return rows

    @staticmethod
    def _equal_col_widths(n: int, total_width: float) -> List[float]:
        if n <= 0:
            return []
        each = total_width / n
        return [each] * n

    def _brand_logo_flowable(self, Image, inch_unit: float):
        """Return a reportlab Image for the LogicTrack logo, falling back
        to a default icon if no brand logo is shipped with the project."""
        from reportlab.platypus import Image as _Image, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        candidates = [
            os.path.join(os.path.dirname(__file__), os.pardir,
                         "assets", "logo.png"),
            os.path.join(os.path.dirname(__file__), os.pardir,
                         "assets", "icons", "default.png"),
        ]
        for c in candidates:
            c = os.path.abspath(c)
            if os.path.isfile(c):
                try:
                    img = _Image(c, width=0.6 * inch_unit, height=0.6 * inch_unit)
                    return img
                except Exception:
                    continue
        # Text fallback if no image available
        styles = getSampleStyleSheet()
        return Paragraph(
            "<para align='left'><b><font size=14 color='#5863E8'>LT</font></b></para>",
            styles["Normal"],
        )

    def _export_plain_text_fallback(self) -> None:
        """Used only when reportlab is missing."""
        try:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            path = os.path.abspath(filename)
            with open(path, "w") as f:
                f.write("\t".join(self.last_headers) + "\n")
                for row in self.last_results:
                    f.write("\t".join(row) + "\n")
            self._toast(
                "reportlab is not installed — saved a plain-text export "
                f"instead:\n{path}\n\nRun `pip install reportlab` for the "
                "branded PDF layout."
            )
        except OSError as exc:
            log.exception("Fallback text export failed")
            self._toast(f"Could not export: {exc}")
