def test_admin_users_page_loads(client, login_as):
    login_as(client, "admin", "admin")
    assert client.get("/users").status_code == 200


def test_admin_cannot_delete_own_account(client, login_as, db):
    admin_id = db.execute(
        "SELECT id FROM users WHERE username = ?",
        ("admin",),
    ).fetchone()["id"]
    login_as(client, "admin", "admin")
    response = client.post(f"/delete_user/{admin_id}")
    assert response.status_code == 302
    count = db.execute(
        "SELECT COUNT(*) AS count FROM users WHERE username = ?",
        ("admin",),
    ).fetchone()["count"]
    assert count == 1
