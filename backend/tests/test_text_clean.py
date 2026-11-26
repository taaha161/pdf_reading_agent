from services.text_clean import clean_description


def test_strips_statement_icons():
    assert clean_description("✈ TIM HORTONS #8366 CALGARY AB") == "TIM HORTONS #8366 CALGARY AB"
    assert clean_description("→ MCDONALD'S #9194 CALGARY AB") == "MCDONALD'S #9194 CALGARY AB"


def test_folds_accents_and_keeps_merchant_punctuation():
    assert clean_description("CAFÉ  DÉPANNEUR  A&W #4830") == "CAFE DEPANNEUR A&W #4830"
    assert clean_description("IC* COSTCO BY INSTACAR") == "IC* COSTCO BY INSTACAR"


def test_handles_empty_and_non_string():
    assert clean_description(None) == ""
    assert clean_description(12.5) == "12.5"
