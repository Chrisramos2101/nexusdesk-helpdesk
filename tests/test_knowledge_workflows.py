
from unittest.mock import patch

import pytest

from routes.knowledge import (
    get_article_summary,
    get_related_articles,
    knowledge_articles,
)


def test_knowledge_base_lists_all_articles(
    client, login_as
):
    login_as(client)

    with patch(
        "routes.knowledge.render_template",
        return_value="Knowledge base rendered",
    ) as mock_render:
        response = client.get("/knowledge_base")

    assert response.status_code == 200

    articles = mock_render.call_args.kwargs["articles"]

    assert len(articles) == len(knowledge_articles)

    slugs = {article["slug"] for article in articles}

    assert "password-reset" in slugs
    assert "wifi-network" in slugs


def test_article_summary_contains_required_information():
    article = knowledge_articles["password-reset"]

    summary = get_article_summary(
        "password-reset",
        article,
    )

    assert summary["slug"] == "password-reset"
    assert summary["title"] == "Password Reset Help"
    assert summary["category"] == "Account Access"
    assert summary["estimated_time"]
    assert summary["difficulty"]


def test_related_articles_exclude_current_article():
    related = get_related_articles("password-reset")

    assert len(related) == 3
    assert all(
        article["slug"] != "password-reset"
        for article in related
    )


def test_unknown_article_redirects_to_knowledge_base(
    client, login_as
):
    login_as(client)

    response = client.get(
        "/knowledge_base/not-a-real-article"
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/knowledge_base"
    )


def test_article_view_is_recorded(
    client, login_as, db
):
    login_as(client, "employee", "employee")

    response = client.get(
        "/knowledge_base/password-reset"
    )

    assert response.status_code == 200

    view = db.execute(
        """
        SELECT article_slug, username
        FROM article_views
        WHERE article_slug = ?
        """,
        ("password-reset",),
    ).fetchone()

    assert view is not None
    assert view["username"] == "employee"


@pytest.mark.parametrize(
    "choice",
    ["yes", "partial", "no"],
)
def test_valid_feedback_is_saved(
    client, login_as, db, choice
):
    login_as(client, "employee", "employee")

    response = client.post(
        "/knowledge_base/password-reset/feedback",
        data={
            "was_helpful": choice,
            "feedback_reason": "Clear instructions",
            "feedback": "Useful troubleshooting steps",
        },
    )

    assert response.status_code == 302

    saved = db.execute(
        """
        SELECT username, was_helpful, feedback
        FROM article_feedback
        WHERE article_slug = ?
        """,
        ("password-reset",),
    ).fetchone()

    assert saved is not None
    assert saved["username"] == "employee"
    assert saved["was_helpful"] == choice
    assert "Clear instructions" in saved["feedback"]
    assert "Useful troubleshooting steps" in saved["feedback"]


def test_unknown_article_feedback_is_rejected(
    client, login_as, db
):
    login_as(client)

    response = client.post(
        "/knowledge_base/unknown-article/feedback",
        data={
            "was_helpful": "yes",
            "feedback": "Test",
        },
    )

    assert response.status_code == 302

    count = db.execute(
        "SELECT COUNT(*) FROM article_feedback"
    ).fetchone()[0]

    assert count == 0


def test_feedback_length_limits_are_enforced(
    client, login_as, db
):
    login_as(client)

    response = client.post(
        "/knowledge_base/password-reset/feedback",
        data={
            "was_helpful": "yes",
            "feedback_reason": "R" * 500,
            "feedback": "F" * 3000,
        },
    )

    assert response.status_code == 302

    saved = db.execute(
        """
        SELECT feedback
        FROM article_feedback
        LIMIT 1
        """
    ).fetchone()

    assert saved is not None

    # The route limits reason to 120 characters
    # and feedback details to 2000 characters.
    assert "R" * 120 in saved["feedback"]
    assert "R" * 121 not in saved["feedback"]
    assert "F" * 2000 in saved["feedback"]
    assert "F" * 2001 not in saved["feedback"]


def test_employee_cannot_view_admin_feedback(
    client, login_as
):
    login_as(client, "employee", "employee")

    response = client.get("/admin/article-feedback")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_admin_feedback_report_calculates_totals(
    client, login_as, db
):
    rows = [
        ("employee", "yes"),
        ("other", "partial"),
        ("employee", "no"),
    ]

    for username, choice in rows:
        db.execute(
            """
            INSERT INTO article_feedback
            (article_slug, username, was_helpful,
             feedback, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "password-reset",
                username,
                choice,
                "Test feedback",
                "11/09/2026 10:00 AM",
            ),
        )

    db.commit()
    login_as(client, "admin", "admin")

    with patch(
        "routes.knowledge.render_template",
        return_value="Feedback report rendered",
    ) as mock_render:
        response = client.get(
            "/admin/article-feedback"
        )

    assert response.status_code == 200

    context = mock_render.call_args.kwargs

    assert context["total_feedback"] == 3
    assert context["solved_count"] == 1
    assert context["partial_count"] == 1
    assert context["no_count"] == 1


def test_article_helpfulness_percentage(
    client, login_as, db
):
    login_as(client)

    for choice in ["yes", "yes", "no", "partial"]:
        db.execute(
            """
            INSERT INTO article_feedback
            (article_slug, username, was_helpful,
             feedback, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "wifi-network",
                "employee",
                choice,
                "Test",
                "11/09/2026 10:00 AM",
            ),
        )

    db.commit()

    with patch(
        "routes.knowledge.render_template",
        return_value="Article rendered",
    ) as mock_render:
        response = client.get(
            "/knowledge_base/wifi-network"
        )

    assert response.status_code == 200

    stats = mock_render.call_args.kwargs[
        "article_stats"
    ]

    assert stats["feedback_count"] == 4
    assert stats["helpful_percent"] == 50
    assert stats["views"] == 1
