
import pytest


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/my_tickets",
        "/profile",
        "/knowledge_base",
        "/contact_it",
        "/api/users/search?q=admin",
    ],
)
def test_anonymous_user_redirected_to_login(client, path):
    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize(
    "path",
    [
        "/my_tickets",
        "/knowledge_base",
        "/profile",
    ],
)
def test_valid_employee_can_access_pages(
    client, login_as, path
):
    login_as(client, "employee", "employee")

    response = client.get(path)

    assert response.status_code == 200
