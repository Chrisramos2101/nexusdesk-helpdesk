"""Structural safety tests for recruiter-only UI enhancements."""
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TEMPLATES = [
    'index.html', 'dashboard.html', 'my_tickets.html', 'ticket_detail.html',
    'stats.html', 'users.html', 'system_dashboard.html', 'knowledge_base.html',
    'knowledge_article.html', 'contact_it.html', 'admin_article_feedback.html',
]


def test_shared_navigation_is_conditional():
    for name in TEMPLATES:
        template = (BASE / 'templates' / name).read_text(encoding='utf-8')
        assert "{% if session.get('recruiter_demo') %}" in template, name
        assert "{% include '_recruiter_demo_nav.html' %}" in template, name
        assert "filename='recruiter_ui.css'" in template, name


def test_landing_keeps_csrf_and_role_selection():
    html = (BASE / 'templates' / 'recruiter_demo.html').read_text(encoding='utf-8')
    assert html.count('name="csrf_token"') == 2
    assert 'name="role" value="admin"' in html
    assert 'name="role" value="employee"' in html
    assert "url_for('recruiter_demo.enter')" in html


def test_readonly_controls_are_concealed_in_preview_only():
    css = (BASE / 'static' / 'recruiter_ui.css').read_text(encoding='utf-8')
    assert 'body.nexusdesk-recruiter-preview form[method="POST"]' in css
    assert 'body.nexusdesk-recruiter-preview form[method="post"]' in css
    navbar = (BASE / 'templates' / '_recruiter_demo_nav.html').read_text(encoding='utf-8')
    assert "session.get('role') == 'admin'" in navbar
    assert 'href="/recruiter-demo/"' in navbar


def test_ui_patch_does_not_modify_security_layer():
    guard = (BASE / 'services' / 'recruiter_demo_guard.py').read_text(encoding='utf-8')
    assert 'DEMO_DATABASE_NAME' in guard
    assert 'DEMO_DATABASE_USER' in guard
    assert 'abort(403)' in guard
