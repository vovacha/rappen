import pytest

from rappen import config, importer, parsers, repository


@pytest.mark.parametrize("bank", sorted(parsers.load()))
def test_every_bank_is_detected_and_reimports_nothing(conn, bank, statements):
    first = importer.import_file(conn, statements[bank])
    assert first.account == bank
    assert (first.inserted, first.duplicates) == (first.parsed, 0) and first.parsed > 0
    assert first.date_from <= first.date_to and all(t.id for t in first.transactions)
    again = importer.import_file(conn, statements[bank])
    assert (again.inserted, again.duplicates, again.transactions) == (0, again.parsed, [])
    assert len(repository.list_transactions(conn, account=bank, limit=1000)) == first.parsed


def test_rules_fill_what_they_match(conn, statements):
    result = importer.import_file(conn, statements["revolut"])
    assert {t.category for t in result.transactions} > {None, "Groceries"}   # what the rules did, and did not


def test_one_file_many_currencies(conn, statements):
    importer.import_file(conn, statements["yuh"])
    by_currency = {c: len(repository.list_transactions(conn, account="yuh", currency=c, limit=1000))
                   for c in ("CHF", "EUR", "USD")}
    assert by_currency == {"CHF": 11, "EUR": 2, "USD": 3}


def _pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode()
    return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R"
            b"/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>endobj\n"
            b"4 0 obj<</Length " + str(len(stream)).encode() + b">>stream\n" + stream + b"\nendstream endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF\n")


@pytest.mark.parametrize("name, content", [
    ("x.csv", b"a,b\n1,2\n"),
    ("x.pdf", _pdf("Account statement")),
    ("monobank.pdf", _pdf("Date and time")),        # a CSV bank's signature in a PDF is not that bank
    ("x.csv", b"PostFinance Ltd,Text\n"),           # nor a PDF bank's in a CSV
])
def test_unknown_file_is_rejected(conn, tmp_path, name, content):
    path = tmp_path / name
    path.write_bytes(content)
    with pytest.raises(ValueError, match="known bank"):
        importer.import_file(conn, path)


def test_unknown_currency_is_rejected(conn, statements, tmp_path):
    path = tmp_path / "gbp.csv"
    path.write_text(statements["revolut"].read_text().replace(",EUR,", ",GBP,", 1))
    with pytest.raises(ValueError, match="GBP"):
        importer.import_file(conn, path)
    assert repository.list_transactions(conn) == []


def test_same_day_rows_are_distinct(conn, statements):
    importer.import_file(conn, statements["postfinance"])
    june25 = repository.list_transactions(conn, date_from="2026-06-25", date_to="2026-06-26", limit=100)
    assert len(june25) == 4  # salary, two Apple Pay charges, one refund — none deduped away


def test_transfers_classified_and_excluded(conn, statements):
    importer.import_file(conn, statements["postfinance"])
    importer.import_file(conn, statements["revolut"])
    rows = repository.list_transactions(conn, categories=["Transfers"], limit=100)
    assert {t.description[:21] for t in rows} >= {"TRANSFER FROM ACCOUNT", "Payment from MUSTER, ", "Exchanged to EUR"}
    assert "Transfers" in config.load().names(transfer=True)


def test_settled_rows_are_added_on_overlap(conn, statements, tmp_path):
    importer.import_file(conn, statements["revolut"])
    settled = tmp_path / "later.csv"
    settled.write_text(statements["revolut"].read_text().replace(",PENDING,", ",COMPLETED,", 1))
    result = importer.import_file(conn, settled)
    assert (result.inserted, result.duplicates) == (1, 17)
