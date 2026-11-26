from services.currency_hint import correct_dollar_currency

CIBC = "CIBC Aeroplan Visa\nCALGARY AB T2X 1A1\nPrevious balance $5,672.99\nMar 05 MC DONALD S BUCARAMANGA 40,400.00 COP @ 0.000372277** 15.04"


def test_canadian_bank_dollar_statement_becomes_cad():
    assert correct_dollar_currency("USD", CIBC) == "CAD"
    assert correct_dollar_currency(None, CIBC) == "CAD"


def test_canadian_address_without_known_bank():
    text = "Credit Union statement\n123 Main St, Halifax NS B3H 1A1 CANADA\nBalance $1,200.00"
    assert correct_dollar_currency("USD", text) == "CAD"


def test_us_dollar_card_from_canadian_bank_stays_usd():
    assert correct_dollar_currency("USD", "CIBC US$ Visa\nBalance US$ 1,000.00") == "USD"
    assert correct_dollar_currency("USD", "RBC Royal Bank U.S. Dollar account\n$500.00") == "USD"


def test_fx_detail_in_usd_does_not_block_cad():
    text = CIBC + "\nMar 09 AMAZON SEATTLE 12.00 USD @ 1.371200** 16.45"
    assert correct_dollar_currency("USD", text) == "CAD"


def test_us_statements_untouched():
    assert correct_dollar_currency("USD", "Chase Bank\nChicago, IL 60601\nBalance $2,000.00") == "USD"
    assert correct_dollar_currency("USD", "BMO Bank N.A.\nBalance $2,000.00") == "USD"
    assert correct_dollar_currency("USD", "BMO Harris\n$10.00") == "USD"


def test_other_currencies_untouched():
    assert correct_dollar_currency("PKR", CIBC) == "PKR"
    assert correct_dollar_currency("CAD", CIBC) == "CAD"
