"""Correct "$" statements that the model labels USD but are really Canadian dollars."""
import re

# Canadian issuers whose statements print a bare "$" and never write "CAD".
_CANADIAN_BANKS = re.compile(
    r"\b(CIBC|RBC ROYAL BANK|ROYAL BANK OF CANADA|TD CANADA TRUST|BMO|BANK OF MONTREAL|SCOTIABANK|"
    r"BANK OF NOVA SCOTIA|DESJARDINS|NATIONAL BANK OF CANADA|BANQUE NATIONALE|TANGERINE|ATB FINANCIAL|"
    r"SIMPLII|EQ BANK|LAURENTIAN BANK|VANCITY|PC FINANCIAL|ROGERS BANK|CANADIAN TIRE BANK)\b",
    re.IGNORECASE,
)
# Canadian postal code, e.g. "T2X 1A1".
_POSTAL_CODE = re.compile(r"\b[ABCEGHJ-NPRSTVXY]\d[A-Z] ?\d[A-Z]\d\b")
# Foreign-exchange detail on a single purchase ("12.00 USD @ 1.3712") says nothing about the account.
_FX_DETAIL = re.compile(r"[\d.,]+\s*[A-Z]{3}\s*@\s*[\d.]+")
# US arms of Canadian groups (BMO Bank N.A., TD Bank N.A.) issue USD statements.
_US_BANK = re.compile(r"\bN\.\s?A\.|\bBMO HARRIS\b", re.IGNORECASE)
_SAYS_USD = re.compile(r"\bUSD\b|\bUS\s?\$|\bU\.\s?S\.\s?\$|\bU\.?\s?S\.?\s+DOLLARS?\b", re.IGNORECASE)


def correct_dollar_currency(currency: str | None, raw_text: str) -> str | None:
    """Return CAD when a USD (or unknown) statement is clearly Canadian and never names US dollars.

    US-dollar cards from Canadian banks write "US$"/"USD" on the statement, so they keep USD.
    """
    code = (currency or "").strip().upper()
    if code not in ("", "USD"):
        return currency
    text = _FX_DETAIL.sub(" ", raw_text or "")
    if "$" not in text or _SAYS_USD.search(text) or _US_BANK.search(text):
        return currency
    canadian_address = bool(_POSTAL_CODE.search(text)) and bool(re.search(r"\bCANADA\b", text, re.I))
    if _CANADIAN_BANKS.search(text) or canadian_address:
        return "CAD"
    return currency
