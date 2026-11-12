"""Recruiter final polish: preview permission tests and no-write structural assertions."""
from pathlib import Path

import pytest
from flask import Flask

from routes.recruiter_demo import recruiter_demo_bp
from services.recruiter_demo_guard import register_recruiter_demo_guard

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def demo_client(monkeypatch):
    monkeypatch.setenv('RECRUITER_DEMO_MODE', 'true')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://recruiter_demo_app:fake@localhost/nexusdesk_recruiter_demo')
    app = Flask(__name__, template_folder=str(ROOT / 'templates'), static_folder=str(ROOT / 'static'))
    app.config.update(TESTING=True, SECRET_KEY='testing-only', RECRUITER_STRICT_ENDPOINTS=True)
    app.register_blueprint(recruiter_demo_bp)
    register_recruiter_demo_guard(app)
    return app.test_client()


def sign_in(client, username, role):
    with client.session_transaction() as sess:
        sess.clear()
        sess.update({'username': username, 'role': role, 'recruiter_demo': True})


def test_guest_cannot_access_feature_previews(demo_client):
    assert demo_client.get('/recruiter-demo/preview/profile').status_code == 403


def test_admin_can_view_admin_previews(demo_client):
    sign_in(demo_client, 'Demo_Admin', 'admin')
    for name in ('create-user', 'submit-support-request', 'edit-ticket', 'profile'):
        response = demo_client.get('/recruiter-demo/preview/' + name)
        assert response.status_code == 200, name
        assert b'Nothing saved' in response.data
        assert b'Save disabled' in response.data
        assert b'<form' not in response.data


def test_employee_can_view_employee_previews(demo_client):
    sign_in(demo_client, 'Demo_Employee', 'employee')
    for name in ('change-password', 'profile'):
        response = demo_client.get('/recruiter-demo/preview/' + name)
        assert response.status_code == 200, name
        assert b'Save disabled' in response.data
    assert b'demo-employee@example.com' in demo_client.get('/recruiter-demo/preview/profile').data


def test_employee_cannot_view_admin_previews(demo_client):
    sign_in(demo_client, 'Demo_Employee', 'employee')
    for name in ('create-user', 'submit-support-request'):
        assert demo_client.get('/recruiter-demo/preview/' + name).status_code == 403


def test_admin_cannot_view_employee_password_preview(demo_client):
    sign_in(demo_client, 'Demo_Admin', 'admin')
    assert demo_client.get('/recruiter-demo/preview/change-password').status_code == 403
    assert demo_client.get('/recruiter-demo/preview/not-real').status_code == 404


def test_preview_post_methods_are_rejected(demo_client):
    sign_in(demo_client, 'Demo_Admin', 'admin')
    assert demo_client.post('/recruiter-demo/preview/create-user').status_code in (403, 405)
    assert demo_client.post('/submit').status_code == 403


def test_production_template_remains_present_and_demo_is_no_submit():
    html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
    assert 'action="/submit"' in html
    assert 'nd-local-ticket-editor' in html
    assert 'nd-save-disabled' in html
    assert 'disabled aria-disabled="true"' in html
    assert 'current_user.full_name' in html
    assert 'current_user.department' in html


def test_isolated_mode_only_and_original_db_guard_present():
    guard = (ROOT / 'services' / 'recruiter_demo_guard.py').read_text(encoding='utf-8')
    assert 'DEMO_DATABASE_NAME' in guard
    assert 'DEMO_DATABASE_USER' in guard
    assert 'RECRUITER_STRICT_ENDPOINTS' in guard
    assert '"recruiter_demo.preview"' in guard
    assert 'abort(403)' in guard
