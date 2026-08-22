def test_knowledge_base_requires_login(client):
    response = client.get("/knowledge_base")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_authenticated_user_can_view_knowledge_article(client, login_as):
    login_as(client)
    response = client.get("/knowledge_base/password-reset")
    assert response.status_code == 200


def test_invalid_feedback_value_is_not_stored(client, login_as, db):
    login_as(client)
    response = client.post(
        "/knowledge_base/password-reset/feedback",
        data={"was_helpful": "malicious", "feedback": "bad"},
    )
    assert response.status_code == 302
    count = db.execute("SELECT COUNT(*) AS count FROM article_feedback").fetchone()["count"]
    assert count == 0
