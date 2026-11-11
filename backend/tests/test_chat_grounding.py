"""Chat grounding: full data reaches the model, totals match the UI, queries compute exact sums."""
from services import chat_service as cs
from services.summary import _summary_by_category

TX = [
    {"date": "02 Jul 2025", "description": "Money Received from WAJID ALI", "amount": "1,000.00", "type": "credit", "category": "From: WAJID ALI"},
    {"date": "03 Jul 2025", "description": "Money Transferred to WAJID ALI", "amount": "400.50", "type": "debit", "category": "To: WAJID ALI"},
    {"date": "04 Aug 2025", "description": "ATM Cash Withdrawal", "amount": "200", "type": "debit", "category": "Cash Withdrawals"},
    {"date": "05 Aug 2025", "description": "Raast P2P Fund transfer to SHOP", "amount": "99.50", "type": "debit", "category": "Raast P2P - Sent"},
]


def test_official_totals_match_summary_table():
    t = cs.official_totals(TX)
    assert (t["credits_total_money_in"], t["debits_total_money_out"]) == (1000.0, 700.0)
    assert t["net_credits_minus_debits"] == 300.0
    assert [(r["category"], r["summary_total"]) for r in t["summary_by_category"]] == [
        (c, round(v, 2)) for c, v in _summary_by_category(TX)
    ]


def test_query_by_person_across_to_and_from_categories():
    r = cs.query_rows(TX, category_contains="wajid ali")
    assert (r["count"], r["credit_total"], r["debit_total"], r["net"]) == (2, 1000.0, 400.5, 599.5)
    assert [row["#"] for row in r["rows"]] == [1, 2]
    assert r["by_category"] == {
        "From: WAJID ALI": {"count": 1, "credit_total": 1000.0, "debit_total": 0.0},
        "To: WAJID ALI": {"count": 1, "credit_total": 0.0, "debit_total": 400.5},
    }


def test_query_filters_combine():
    r = cs.query_rows(TX, date_contains="aug 2025", type="debit")
    assert (r["count"], r["debit_total"], r["credit_total"]) == (2, 299.5, 0.0)
    assert cs.query_rows(TX, category="raast p2p - sent")["count"] == 1


def test_model_receives_every_row_and_totals(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured["contents"], captured["config"] = contents, config
            return type("R", (), {"text": "ok"})()

    monkeypatch.setattr(cs, "_get_client", lambda: type("C", (), {"models": FakeModels()})())
    many = [dict(TX[2], date=f"{i:02d} Sep 2025") for i in range(1, 900)]
    assert cs.get_reply({"transactions": many, "currency": "PKR"}, "how many ATM withdrawals?") == "ok"
    assert "899 rows" in captured["contents"] and "\n899," in captured["contents"]  # last row present
    assert "'debits_total_money_out': 179800.0" in captured["contents"]
    assert captured["config"].tools  # query tool attached
