
import pytest


@pytest.mark.parametrize(
    "choice",
    [
        "",
        "maybe",
        "YESPLEASE",
        "invalid",
    ],
)
def test_invalid_feedback_is_not_saved(
    client, login_as, db, choice
):
    login_as(client, "employee", "employee")

    response = client.post(
        "/knowledge_base/password-reset/feedback",
        data={
            "was_helpful": choice,
            "feedback": "Invalid feedback",
        },
    )

    assert response.status_code == 302

    count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM article_feedback
        """
    ).fetchone()["count"]

    assert count == 0


def test_demoted_admin_cannot_view_feedback_report(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    db.execute(
        """
        UPDATE users
        SET role = 'employee'
        WHERE username = 'admin'
        """
    )
    db.commit()

    response = client.get("/admin/article-feedback")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_deleted_admin_cannot_view_feedback_report(
    client, login_as, db
):
    login_as(client, "admin", "admin")

    db.execute(
        "DELETE FROM users WHERE username = 'admin'"
    )
    db.commit()

    response = client.get("/admin/article-feedback")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
