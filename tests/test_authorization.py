def test_anonymous_user_is_redirected_from_admin(client):
    response = client.get("/users")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_employee_cannot_open_admin_users(client, login_as):
    login_as(client, "employee", "employee")
    response = client.get("/users")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_employee_can_open_own_ticket(client, login_as, create_ticket):
    ticket_id = create_ticket("employee")
    login_as(client, "employee", "employee")
    response = client.get(f"/my_tickets/{ticket_id}")
    assert response.status_code == 200


def test_employee_cannot_open_another_users_ticket(client, login_as, create_ticket):
    ticket_id = create_ticket("other")
    login_as(client, "employee", "employee")
    response = client.get(f"/my_tickets/{ticket_id}")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/my_tickets")
