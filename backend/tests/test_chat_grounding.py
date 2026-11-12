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
    assert cs.get_reply({"transactions": many, "currency": "PKR"}, "how many ATM withdrawals?") == ("ok", [])
    assert "899 rows" in captured["contents"] and "\n899," in captured["contents"]  # last row present
    assert "'debits_total_money_out': 179800.0" in captured["contents"]
    assert captured["config"].tools  # query tool attached


def test_export_rows_returns_every_match_with_export_columns_only():
    rows = cs.export_rows([dict(TX[0], extra="x", amount=1000.0)] + TX[1:], category_contains="wajid ali")
    assert rows == [
        {"date": "02 Jul 2025", "description": "Money Received from WAJID ALI", "amount": "1000.0", "type": "credit", "category": "From: WAJID ALI"},
        {"date": "03 Jul 2025", "description": "Money Transferred to WAJID ALI", "amount": "400.50", "type": "debit", "category": "To: WAJID ALI"},
    ]
    many = [dict(TX[2], date=f"{i} Sep 2025") for i in range(cs.QUERY_MAX_ROWS + 50)]
    assert len(cs.export_rows(many, description_contains="atm")) == cs.QUERY_MAX_ROWS + 50  # no 200-row cap


def test_reply_returns_rows_from_last_attach_call(monkeypatch):
    class FakeModels:
        def generate_content(self, model, contents, config):
            attach = next(f for f in config.tools if f.__name__ == "attach_transactions")
            attach(description_contains="atm")
            assert attach(category_contains="wajid ali")["attached_count"] == 2
            return type("R", (), {"text": "Here they are"})()

    monkeypatch.setattr(cs, "_get_client", lambda: type("C", (), {"models": FakeModels()})())
    reply, rows = cs.get_reply({"transactions": TX, "currency": "PKR"}, "give me transactions from wajid ali")
    assert reply == "Here they are"
    assert [r["category"] for r in rows] == ["From: WAJID ALI", "To: WAJID ALI"]
