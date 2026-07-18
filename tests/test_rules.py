import pytest

from rappen import rules

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
    ("Payment from MUSTER, MAX", 500, "Transfers"),         # owner (`owner:` in the yaml)
    ("CREDIT MAILER: ACME TECHNOLOGIES AG SALAERZAHLUNG", 7439.1, "Salary"),  # must not mention the owner
    ("Transfer to Max Muster", -1000, "Transfers"),
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
    assert rules.load().classify(desc, amount) == expected


@pytest.mark.parametrize("desc, expected", [
    ("Київстар +380000000000", "Telecom"),        # Cyrillic upper-cases and has word boundaries too
    ("Cancellation Київстар +380000000000", "Telecom"),
    ("КИЇВСТАРТ", None),
])
def test_cyrillic_patterns(desc, expected):
    cyrillic = rules.Rules("categories:\n  - name: Telecom\n    match: [КИЇВСТАР]\n")
    assert cyrillic.classify(desc, -150) == expected


@pytest.mark.parametrize("bad", [
    "categories: nope",
    "categories:\n  - name: Food\n    match: MIGROS\n",              # a scalar would match letter by letter
    "categories:\n  - name: Transfers\n    transfer: 'false'\n",
    "categories:\n  - name: Rent\n    trip:\n",
    "categories:\n  - name: Food\n  - name: Food\n",
    "owner: MUSTER\ncategories: []\n",
    "categories:\n  - name: Rent\n    fixd: true\n",                        # a typo would silently drop the flag
    "categories:\n  - name: A\n    children:\n      - name: B\n        children: [{name: C}]\n",
    "categories:\n  - name: Software\n    match: [{pattern: APPLE, not_contains: APPLE PAY}]\n",  # the old key; `not` would be silently lost
    "categories:\n  - name: Food\n    match: ['*']\n",                                # matches everything
])
def test_malformed_files_are_rejected(bad):
    with pytest.raises(ValueError):
        rules.Rules(bad)
