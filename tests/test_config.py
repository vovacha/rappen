import pytest

from rappen import config, service

HEAD = "version: 1\ncurrency: CHF\n"

CASES = [
    ("Migros", -20, "Groceries"),
    ("NETFLIX.COM", -12, "Streaming"),
    ("Anthropic", -18, "AI"),
    ("Coop", -30, "Groceries"),                             # bare COOP
    ("Coop Vitality Apotheke", -30, "Pharmacy"),            # longer match wins
    ("Coop Restaurant", -30, "Restaurants"),
    ("Exchanged to EUR", 100, "Transfers"),                 # Revolut
    ("Autoexchange Swiss francs", -582.83, "Transfers"),    # Yuh
    ("Exchange United States dollars", 2734.31, "Transfers"),
    ("CREDIT MAILER: ACME TECHNOLOGIES AG SALAERZAHLUNG", 7439.1, "Salary"),  # must not mention the owner
    ("Transfer to Max Muster", -1000, "Transfers"),        # owner (`owner:` in the yaml)
    ("Transfer from PostFinance AG", 2500, "Transfers"),
    ("Transfer to finpension 3a Retirement Savings Fo", -3629, "Pillar 3a"),    # its own total for the tax return
    ("Zen.com", -1030, "Transfers"),
    ("SP ZENBIVY EUROPE", -586.25, None),                   # not the bank
    ("To Jonas Beispiel", -40, None),                       # person-to-person: by hand
    ("Hotel Sea Sand", -16, "Accommodation"),               # hotel always lodging; small ones reviewed by hand
    ("AG Hotel Restaurant", -60, "Restaurants"),            # longer match wins
    ("Stoos Lodge", -34, "Accommodation"),                  # explicit over the STOOS/LODGE tie
    ("Shell", -57, "Transport"),
    ("Twint to SBBCFFFFS", -170, "Transport"),
    ("McDonalds Zuerich 2016", -11.4, "Restaurants"),
    ("Zürich Duty Free", -32, "General"),
    ("Payment from ERIKA MUSTERMANN", 500, None),             # unknown third party
    ("Tierarztpraxis Muster", -286.1, None),                # a merchant with one of the owner's words: the owner is a phrase
    ("Amazon", -30, None),                                  # ambiguous: manual
    ("Apple", -9, "Software"),                              # small recurring: App Store/iCloud
    ("Apple", -150, None),                                  # large one-off (device): manual
    ("APPLE PAY SALES/SERVICES OF 01.01 CARD NO. X", -8, None),  # PostFinance rail, not the merchant
    ("DEBIT STANDING ORDER: 90-3 ANNA BEISPIEL", -2100, "Rent"),  # match the landlord, not the mechanism
    ("Some Random Kiosk XYZ", -5, "Groceries"),             # KIOSK is a grocery rail
    ("Interest on deposits", 0.7, "Other Income"),
    ("Transfer to Steueramt Zürich", -649, "Taxes"),
    ("Smilezone Zahnarztpraxis", -142.3, "Medical"),
    ("Transfer to Sanitas Grundversicherungen AG", -362.15, "Health Insurance"),
    ("AXA Versicherungen", -80, "Insurance"),
    ("TWINT ... RICARDO SALE ...", 644, "Other Income"),    # incoming Ricardo resale
    ("TWINT PURCHASE/SERVICE RICARDO AG ZUG", -190, None),  # outgoing Ricardo purchase stays manual
    ("Public Enterprise for State Roads of the Republic of Macedonia", -1, None),  # PUB is a word, not a substring
    ("Sparkasse", -10, None),                               # SPAR is a word
    ("Barbara Beispiel", -10, None),                        # BAR is a word ...
    ("Mühlibar", -10, "Restaurants"),                       # ... but *BAR accepts a suffix
    ("Jungfrau Gastronomie", -30, "Restaurants"),           # GASTR* accepts a prefix
    ("Avia Volg", -10, None),                               # equal-length hits in two categories: manual
]


@pytest.mark.parametrize("desc, amount, expected", CASES)
def test_classify(desc, amount, expected):
    assert config.load().classify(desc, amount) == expected


@pytest.mark.parametrize("desc, expected", [
    ("Київстар +380000000000", "Telecom"),        # Cyrillic upper-cases and has word boundaries too
    ("Cancellation Київстар +380000000000", "Telecom"),
    ("КИЇВСТАРТ", None),
])
def test_cyrillic_patterns(desc, expected):
    cyrillic = config.Config(HEAD + "categories:\n  - name: Telecom\n    match: [КИЇВСТАР]\n")
    assert cyrillic.classify(desc, -150) == expected


BAD_CATEGORIES = [
    "categories: nope",
    "categories:\n  - name: Food\n    match: MIGROS\n",              # a scalar would match letter by letter
    "categories:\n  - name: Transfers\n    transfer: 'false'\n",
    "categories:\n  - name: Rent\n    trip:\n",
    "categories:\n  - name: Food\n  - name: Food\n",
    "categories:\n  - name: Rent\n    fixd: true\n",                        # a typo would silently drop the flag
    "categories:\n  - name: A\n    children:\n      - name: B\n        children: [{name: C}]\n",
    "categories:\n  - name: Software\n    match: [{pattern: APPLE, not_contains: APPLE PAY}]\n",  # the old key; `not` would be silently lost
    "categories:\n  - name: Food\n    match: ['*']\n",                                # matches everything
]
BAD_HEADS = [
    "owner: [MUSTER]\ncurrency: CHF\ncategories: []\n",                  # no version: an unversioned file is not trusted
    "version: 0\nowner: [MUSTER]\ncurrency: CHF\ncategories: []\n",
    "version: 2\nowner: [MUSTER]\ncurrency: CHF\ncategories: []\n",     # from a newer rappen
    "version: 1\ncategories: []\n",                                      # no base currency
    "version: 1\nowner: MUSTER\ncurrency: CHF\ncategories: []\n",
    "version: 1\ncurrency: 5\ncategories: []\n",
    HEAD + "owners: [MAX]\ncategories: []\n",                            # a top-level typo would silently drop the key
    HEAD + "rates: [0.94]\ncategories: []\n",
    HEAD + "rates: {EUR: -0.94}\ncategories: []\n",
    HEAD + "rates: {EUR: true}\ncategories: []\n",
]


@pytest.mark.parametrize("bad", [HEAD + b for b in BAD_CATEGORIES] + BAD_HEADS)
def test_malformed_files_are_rejected(bad):
    with pytest.raises(ValueError):
        config.Config(bad)


def test_base_currency_has_rate_one():
    money = config.Config("version: 1\ncurrency: EUR\nrates: {USD: 0.9}\ncategories: []\n")
    assert (money.currency, money.rates) == ("EUR", {"USD": 0.9, "EUR": 1.0})


def test_an_older_format_is_rejected_with_what_to_edit(monkeypatch):
    """The real list is empty until the format changes; the example file is always current."""
    monkeypatch.setattr(config, "CHANGES", ["`rates` are inverted", "`owner` is a string"])
    with pytest.raises(ValueError, match=r"(?s)format 1; .*format 3.*2: `rates`.*3: `owner`"):
        config.load()
    with pytest.raises(ValueError, match=r"(?s)format 2; .*format 3.*3: `owner`") as e:
        config.Config(HEAD.replace("version: 1", "version: 2") + "categories: []\n")
    assert "rates" not in str(e.value)
    config.Config(HEAD.replace("version: 1", "version: 3") + "categories: []\n")


def test_first_set_config_needs_no_file_or_directory(home, monkeypatch):
    monkeypatch.setenv("RAPPEN_HOME", str(home / "fresh"))
    with pytest.raises(ValueError, match="set_config"):
        config.text()
    assert service.get_config().endswith(config.EXAMPLE.read_text(encoding="utf-8"))
    saved = config.save((home / "config.yaml").read_text(encoding="utf-8"))
    assert config.load().names() == saved.names()
