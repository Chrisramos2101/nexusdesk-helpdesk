from datetime import datetime

from scripts.seed_demo_portfolio import build_demo_plan, plan_summary


def test_demo_seed_has_portfolio_scale_and_valid_mix():
    plan = build_demo_plan(datetime(2026, 8, 22, 14, 45))
    summary = plan_summary(plan)

    assert summary["demo_users"] == 14
    assert summary["tickets"] == 72
    assert summary["ticket_notes"] >= 140
    assert summary["login_events"] == 224
    assert summary["audit_events"] >= 150
    assert summary["article_views"] == 120
    assert summary["article_feedback"] == 28

    statuses = {ticket["status"] for ticket in plan["tickets"]}
    priorities = {ticket["priority"] for ticket in plan["tickets"]}
    categories = {ticket["category"] for ticket in plan["tickets"]}

    assert statuses == {"Open", "In Progress", "Closed"}
    assert priorities == {"High", "Medium", "Low"}
    assert categories == {
        "Hardware",
        "Software",
        "Network",
        "Account Access",
        "Security",
        "Other",
    }


def test_demo_tickets_are_synthetic_and_use_demo_accounts_only():
    plan = build_demo_plan(datetime(2026, 8, 22, 14, 45))

    assert all(
        ticket["submitted_by"].startswith("demo_")
        for ticket in plan["tickets"]
    )
    assert all(
        "Synthetic portfolio" in ticket["notes"]
        for ticket in plan["tickets"]
    )
