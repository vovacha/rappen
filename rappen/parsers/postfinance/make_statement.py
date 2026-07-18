"""Regenerate statement.pdf: a synthetic statement with invented names, at the
column positions of a real PostFinance export (the parser reads word coordinates, not text).

    uv run --with reportlab python rappen/parsers/postfinance/make_statement.py
"""

from pathlib import Path

from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent / "statement.pdf"
WIDTH, HEIGHT = 595.276, 841.89
X_DATE, X_TEXT, X1_CREDIT, X1_DEBIT, X_VALUE, X1_BALANCE = 65.2, 127.6, 354.3, 433.7, 447.1, 564.1
FONT, SIZE, LEAD = "Helvetica", 9, 12

# (booking date or "", text, credit, debit, value date, balance or "", detail lines)
ROWS = [
    ("01.06.26", "DEBIT", "", "356.45", "01.06.26", "",
     ["CH0000000000000000001", "SANITAS", "GRUNDVERSICHERUNGEN AG", "MUSTERGASSE 1", "8000 ZÜRICH"]),
    ("", "DEBIT", "", "2 100.00", "01.06.26", "764.55",
     ["STANDING ORDER: 90-00000000", "MUSTERBANK", "POSTFACH", "8000 ZÜRICH", "CH0000000000000000002",
      "ANNA BEISPIEL", "BEISPIELWEG 1", "8000 ZÜRICH"]),
    ("06.06.26", "TRANSFER FROM ACCOUNT", "1 000.00", "", "06.06.26", "1 764.55", ["CH0000000000000000003"]),
    ("07.06.26", "APPLE PAY SALES/SERVICES OF", "", "227.57", "06.06.26", "1 536.98",
     ["06.06.2026", "CARD NO. XXXX0000", "HERTZ MUSTERSTADT", "GLATTBRUGG (CH)"]),
    ("08.06.26", "TWINT SEND MONEY FROM", "", "1 000.00", "07.06.26", "536.98",
     ["07.06.2026", "TO MOBILE NO. +41790000000", ", ANNA"]),
    ("10.06.26", "TWINT PURCHASE/SERVICE FROM", "", "350.00", "10.06.26", "186.98",
     ["10.06.2026", "SBB CFF FFS", "BERN (CH)"]),
    ("25.06.26", "CREDIT", "7 439.10", "", "25.06.26", "",
     ["MAILER:", "ACME TECHNOLOGIES AG", "MUSTERSTRASSE 1", "8000 ZÜRICH", "COMMENTS:", "SALAERZAHLUNG",
      "REFERENCES:", "0000000000000000000000000"]),
    ("", "APPLE PAY SALES/SERVICES OF", "", "355.00", "25.06.26", "",
     ["25.06.2026", "CARD NO. XXXX0000", "SBB ZÜRICH", "ZÜRICH (CH)"]),
    ("", "APPLE PAY SALES/SERVICES OF", "", "1 500.00", "25.06.26", "",
     ["25.06.2026", "CARD NO. XXXX0000", "SBB ZÜRICH", "ZÜRICH (CH)"]),
    ("", "APPLE PAY CREDIT POSTFINANCE", "355.00", "", "25.06.26", "6 126.08",
     ["CARD OF 25.06.2026", "CARD NO. XXXX0000", "SBB ZÜRICH", "ZÜRICH (CH)"]),
    ("29.06.26", "DEBIT", "", "69.00", "29.06.26", "",
     ["MUSTERBANK", "POSTFACH", "8000 ZÜRICH", "CH0000000000000000004", "INIT7 (SCHWEIZ) AG",
      "MUSTERSTRASSE 5", "8000 ZÜRICH"]),
    ("", "DEBIT", "", "500.00", "29.06.26", "5 557.08",
     ["CH0000000000000000005", "REVOLUT BANK UAB", "KONSTITUCIJOS AVE. 21B", "08130 LT-VILNIUS",
      "SENDER'S REFERENCE:", "00000000000000000000000"]),
    ("30.06.26", "PRICE FOR", "", "5.00", "30.06.26", "", ["BANKING PACKAGE SMART", "05.2026"]),
    ("", "TWINT PURCHASE/SERVICE FROM", "", "295.00", "30.06.26", "5 257.08",
     ["30.06.2026", "ZURICHJS", "TANNAY (CH)"]),
]
OPENING, CLOSING, TOTAL_CREDIT, TOTAL_DEBIT = "3 221.00", "5 257.08", "8 794.10", "6 758.02"


class Page:
    def __init__(self, pdf: canvas.Canvas, total_pages: int):
        self.pdf, self.total, self.n, self.y = pdf, total_pages, 0, 0.0

    def header(self, first: bool) -> None:
        self.n += 1
        c, self.y = self.pdf, HEIGHT - 60
        c.setFont(FONT, SIZE)
        if first:
            for i, line in enumerate(["Mr", "Max Muster", "Musterstrasse 1", "8000 Zürich"]):
                c.drawString(283.5, HEIGHT - 190 - 11 * i, line)
            c.drawString(62.5, HEIGHT - 92, "PostFinance Ltd")
            c.drawString(X_TEXT, HEIGHT - 320, "Private account")
            c.drawString(X_TEXT, HEIGHT - 338, "Account statement 01.06.2026 - 30.06.2026")
            self.y = HEIGHT - 370
        c.drawString(X_TEXT, self.y, "IBAN CH00 0900 0000 0000 0000 0 CHF" if first else "IBAN CH00 0900 0000 0000 0000 0")
        c.drawString(X_TEXT, self.y - LEAD, "Account number 00-000000-0")
        c.drawString(X_TEXT, self.y - 2 * LEAD, "Date 01.07.2026")
        self.y -= 4 * LEAD
        self.line("Date", "Text", "Credit", "Debit", "Value", "Balance")
        c.drawRightString(561.2, 23, f"Page {self.n} / {self.total}")

    def line(self, date="", text="", credit="", debit="", value="", balance="") -> None:
        if self.y < 60:
            self.pdf.showPage()
            self.header(first=False)
        c = self.pdf
        c.drawString(X_DATE, self.y, date)
        c.drawString(X_TEXT, self.y, text)
        c.drawRightString(X1_CREDIT, self.y, credit)
        c.drawRightString(X1_DEBIT, self.y, debit)
        c.drawString(X_VALUE, self.y, value)
        c.drawRightString(X1_BALANCE, self.y, balance)
        self.y -= LEAD


def main() -> None:
    lines = 4 + sum(1 + len(r[6]) for r in ROWS)
    per_page = int((HEIGHT - 60 - 60) / LEAD)
    pdf = canvas.Canvas(str(OUT), pagesize=(WIDTH, HEIGHT))
    page = Page(pdf, total_pages=2 if lines + 26 > per_page else 1)
    page.header(first=True)
    page.line("31.05.26", "Account balance", balance=OPENING)
    for date, text, credit, debit, value, balance, details in ROWS:
        page.line(date, text, credit, debit, value, balance)
        for detail in details:
            page.line(text=detail)
    page.line("", "Total", TOTAL_CREDIT, TOTAL_DEBIT)
    page.line("30.06.26", "Account balance", balance=CLOSING)
    pdf.save()


if __name__ == "__main__":
    main()
